import os
import tempfile
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, colorchooser
from tkinter.font import Font
from handwriting_synthesis.hand.Hand import Hand
import threading
import queue
import time

# Optional imports for PDF and preview
try:
    from reportlab.graphics import renderPDF
    from svglib.svglib import svg2rlg
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

try:
    import cairosvg
    from PIL import Image, ImageTk
    PREVIEW_SUPPORT = True
except ImportError:
    PREVIEW_SUPPORT = False

class HandwritingGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("TextoHand - Text To Handwriting Generator by Shikhar\n")
        self.root.geometry("1200x800")
        # Default settings (must be set before building UI)
        self.defaults = {
            "max_line_length": 60,
            "total_lines": 24,
            "lines_per_page": 24,
            "consistency": 0.95,
            "pen_thickness": 1.0,
            "line_height": 32,
            "view_height": 896,
            "view_width": 633.472,
            "margin_left": 64,
            "margin_top": 96,
            "style": 1,
            "color": "Black",
            "page_color": "#FFFFFF",
            "margin_color": "#FF0000",
            "line_color": "#F0F0F0"
        }

        # State
        self.dark_mode = False
        self.dark_mode_var = tk.BooleanVar(value=self.dark_mode)
        self.preview_active = False
        self.preview_queue = queue.Queue()

        # Build UI
        self.setup_ui()

        # Start preview thread after UI exists
        self.setup_preview_thread()

        # Initialize widgets/vars with defaults
        self.reset_defaults()

    def setup_preview_thread(self):
        """Set up a background thread for preview generation"""
        self.preview_thread = threading.Thread(target=self.preview_worker, daemon=True)
        self.preview_thread.start()

    def preview_worker(self):
        """Background worker for generating previews"""
        while True:
            try:
                # wait for a trigger; use timeout so thread can exit gracefully if needed later
                self.preview_queue.get(timeout=1)
                # Delegate UI work to main thread
                self.root.after(0, self.generate_preview_svg)
            except queue.Empty:
                continue

    def setup_ui(self):
        """Initialize all UI components"""
        self.create_styles()
        self.setup_frames()
        self.setup_controls()
        self.setup_text_area()
        self.setup_preview()
        self.setup_menu()

    def create_styles(self):
        """Create consistent styles for widgets"""
        self.style = ttk.Style()
        self.style.configure('TFrame', background='white')
        self.style.configure('TLabel', background='white', foreground='black')
        self.style.configure('TButton', font=('Arial', 10))
        self.style.configure('TCombobox', font=('Arial', 10))

        # compact button style for tighter UI
        self.style.configure('Small.TButton', font=('Arial', 9), padding=(4, 2))
        self.style.map('Small.TButton',
                       foreground=[('active', 'black')],
                       background=[('active', '!disabled', '#e6e6e6')])

        self.bold_font = Font(family='Arial', size=10, weight='bold')
        self.title_font = Font(family='Arial', size=12, weight='bold')

    def setup_frames(self):
        """Create main application frames"""
        # Main container
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left panel - controls (make this scrollable)
        # We create a container with a Canvas + vertical Scrollbar and place the LabelFrame inside the canvas.
        self.control_container = ttk.Frame(self.main_frame)
        self.control_container.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        # Canvas and scrollbar for scrolling settings
        self._control_canvas = tk.Canvas(self.control_container, borderwidth=0, highlightthickness=0)
        self._control_vscroll = ttk.Scrollbar(self.control_container, orient=tk.VERTICAL, command=self._control_canvas.yview)
        self._control_canvas.configure(yscrollcommand=self._control_vscroll.set)

        # Place canvas and scrollbar
        self._control_vscroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._control_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Create the LabelFrame that will hold settings and add it to the canvas
        self.control_frame = ttk.LabelFrame(self._control_canvas, text="Settings", padding=10)
        # Create a window in the canvas to host the control_frame
        self._control_window = self._control_canvas.create_window((0, 0), window=self.control_frame, anchor='nw')

        # Ensure the scrollregion is updated when the inner frame changes size
        def _on_frame_configure(event):
            try:
                self._control_canvas.configure(scrollregion=self._control_canvas.bbox("all"))
            except Exception:
                pass

        self.control_frame.bind("<Configure>", _on_frame_configure)

        # Make the embedded labelframe width track the canvas width to avoid horizontal scrollbar
        def _on_canvas_configure(event):
            try:
                self._control_canvas.itemconfigure(self._control_window, width=event.width)
            except Exception:
                pass

        self._control_canvas.bind("<Configure>", _on_canvas_configure)

        # Mousewheel scrolling for Windows (and basic support for other platforms)
        def _on_mousewheel(event):
            # On Windows delta is multiples of 120
            delta = 0
            if hasattr(event, 'delta') and event.delta:
                delta = int(-1 * (event.delta / 120))
            elif event.num == 5:
                delta = 1
            elif event.num == 4:
                delta = -1
            if delta:
                self._control_canvas.yview_scroll(delta, "units")

        # Bind when pointer enters/leaves control area so wheel affects only this canvas
        def _bind_mousewheel(event):
            # Windows and Mac use <MouseWheel>, Linux may use Button-4/5
            self._control_canvas.bind_all("<MouseWheel>", _on_mousewheel)
            self._control_canvas.bind_all("<Button-4>", _on_mousewheel)
            self._control_canvas.bind_all("<Button-5>", _on_mousewheel)

        def _unbind_mousewheel(event):
            self._control_canvas.unbind_all("<MouseWheel>")
            self._control_canvas.unbind_all("<Button-4>")
            self._control_canvas.unbind_all("<Button-5>")

        self.control_frame.bind("<Enter>", _bind_mousewheel)
        self.control_frame.bind("<Leave>", _unbind_mousewheel)

        # Middle container: PanedWindow for equal/resizable text and preview areas
        self.content_pane = ttk.Panedwindow(self.main_frame, orient=tk.HORIZONTAL)
        self.content_pane.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5,0), pady=5)

        # Create labelframes as panes so they keep titles
        self.text_frame = ttk.LabelFrame(self.content_pane, text="Input Text", padding=10)
        self.preview_frame = ttk.LabelFrame(self.content_pane, text="Preview", padding=10)

        # Add both panes with equal weight so they share space (user can resize)
        self.content_pane.add(self.text_frame, weight=1)
        self.content_pane.add(self.preview_frame, weight=1)

    def setup_controls(self):
        """Set up control widgets"""
        # Layout settings
        self.create_slider("Line Length (chars)", "max_line_length", 20, 100, self.defaults["max_line_length"])
        self.create_slider("Total Lines", "total_lines", 1, 50, self.defaults["total_lines"])
        self.create_slider("Lines per Page", "lines_per_page", 1, 50, self.defaults["lines_per_page"])
        self.create_slider("Line Height", "line_height", 20, 50, self.defaults["line_height"])

        # Handwriting style
        ttk.Label(self.control_frame, text="Handwriting Style").pack(anchor=tk.W)
        self.style_var = tk.IntVar(value=self.defaults["style"])
        self.style_menu = ttk.Combobox(
            self.control_frame,
            textvariable=self.style_var,
            values=list(range(1, 13)),
            state="readonly"
        )
        self.style_menu.pack(fill=tk.X, pady=2)
        self.style_menu.bind("<<ComboboxSelected>>", self.update_preview)

        # Handwriting consistency
        self.create_slider("Consistency", "consistency", 0.7, 1.0, self.defaults["consistency"], 0.01)

        # Pen settings
        self.create_slider("Pen Thickness", "pen_thickness", 0.5, 3.0, self.defaults["pen_thickness"], 0.1)

        ttk.Label(self.control_frame, text="Ink Color").pack(anchor=tk.W)
        self.color_var = tk.StringVar(value=self.defaults["color"])
        self.color_menu = ttk.Combobox(
            self.control_frame,
            textvariable=self.color_var,
            values=["Black", "Blue", "Red", "Green", "Custom..."],
            state="readonly"
        )
        self.color_menu.pack(fill=tk.X, pady=2)
        self.color_menu.bind("<<ComboboxSelected>>", self.on_color_select)

        # Color variables and pickers
        self.page_color_var = tk.StringVar(value=self.defaults["page_color"])
        self.margin_color_var = tk.StringVar(value=self.defaults["margin_color"])
        self.line_color_var = tk.StringVar(value=self.defaults["line_color"])

        ttk.Label(self.control_frame, text="Page Color").pack(anchor=tk.W)
        self.page_color_btn = tk.Button(
            self.control_frame,
            text="Choose",
            command=lambda: self.choose_color("page_color"),
            bg=self.defaults["page_color"],
            width=8,
            padx=2,
            pady=2
        )
        self.page_color_btn.pack(fill=tk.X, pady=2)

        ttk.Label(self.control_frame, text="Margin Color").pack(anchor=tk.W)
        self.margin_color_btn = tk.Button(
            self.control_frame,
            text="Choose",
            command=lambda: self.choose_color("margin_color"),
            bg=self.defaults["margin_color"],
            width=8,
            padx=2,
            pady=2
        )
        self.margin_color_btn.pack(fill=tk.X, pady=2)

        ttk.Label(self.control_frame, text="Guide Line Color").pack(anchor=tk.W)
        self.line_color_btn = tk.Button(
            self.control_frame,
            text="Choose",
            command=lambda: self.choose_color("line_color"),
            bg=self.defaults["line_color"],
            width=8,
            padx=2,
            pady=2
        )
        self.line_color_btn.pack(fill=tk.X, pady=2)

        # View settings
        self.create_slider("View Width", "view_width", 300, 1000, self.defaults["view_width"], 1)
        self.create_slider("View Height", "view_height", 400, 1200, self.defaults["view_height"], 1)
        self.create_slider("Left Margin", "margin_left", 0, 200, self.defaults["margin_left"])
        self.create_slider("Top Margin", "margin_top", 0, 200, self.defaults["margin_top"])

        # Action buttons
        btn_frame = ttk.Frame(self.control_frame)
        btn_frame.pack(fill=tk.X, pady=10)

        ttk.Button(btn_frame, text="Generate", command=self.on_generate, style='Small.TButton', width=10).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(btn_frame, text="Export PDF", command=self.export_pdf, style='Small.TButton', width=10).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(btn_frame, text="Reset", command=self.reset_defaults, style='Small.TButton', width=10).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def create_slider(self, label, var_name, from_, to, default, resolution=1):
        """Helper to create labeled slider controls"""
        frame = ttk.Frame(self.control_frame)
        frame.pack(fill=tk.X, pady=2)

        ttk.Label(frame, text=label).pack(anchor=tk.W)

        value_var = tk.DoubleVar(value=default)
        setattr(self, f"{var_name}_var", value_var)

        slider = ttk.Scale(
            frame,
            from_=from_,
            to=to,
            variable=value_var,
            command=lambda v: self.on_slider_change(var_name, v),
            orient=tk.HORIZONTAL
        )
        slider.pack(fill=tk.X)

        value_label = ttk.Label(frame, text=str(default))
        value_label.pack(anchor=tk.E)
        setattr(self, f"{var_name}_label", value_label)

    def on_slider_change(self, var_name, value):
        """Handle slider value changes"""
        value = float(value)
        if var_name in ["consistency", "pen_thickness"]:
            value = round(value, 2)
        else:
            value = int(round(value))

        getattr(self, f"{var_name}_var").set(value)
        getattr(self, f"{var_name}_label").config(text=str(value))
        self.update_preview()

    def setup_text_area(self):
        """Set up the text input area"""
        # text_frame is already created inside the PanedWindow; place the Text inside it
        self.text_box = tk.Text(
            self.text_frame,
            wrap=tk.WORD,
            font=('Arial', 12),
            padx=10,
            pady=10,
            undo=True
        )
        self.text_box.pack(fill=tk.BOTH, expand=True)

        # Add placeholder text
        self.text_box.insert("1.0", "Enter your text here...")
        self.text_box.config(fg="grey")

        # Bind events for placeholder
        self.text_box.bind("<FocusIn>", self.on_text_focus_in)
        self.text_box.bind("<FocusOut>", self.on_text_focus_out)
        self.text_box.bind("<KeyRelease>", self.update_preview)

    def on_text_focus_in(self, event):
        """Handle text box focus in"""
        if self.text_box.get("1.0", "end-1c") == "Enter your text here...":
            self.text_box.delete("1.0", "end")
            self.text_box.config(fg="black")

    def on_text_focus_out(self, event):
        """Handle text box focus out"""
        if not self.text_box.get("1.0", "end-1c").strip():
            self.text_box.insert("1.0", "Enter your text here...")
            self.text_box.config(fg="grey")

    def setup_preview(self):
        """Set up the preview area"""
        # Add a small header inside preview frame to show and control dark mode
        header = ttk.Frame(self.preview_frame)
        header.pack(fill=tk.X, pady=(0,6))

        # Mode label and checkbutton
        self.mode_label = ttk.Label(header, text="Mode: Light", width=12)
        self.mode_label.pack(side=tk.LEFT, padx=(0,6))

        self.dark_check = ttk.Checkbutton(
            header,
            text="Dark Mode",
            variable=self.dark_mode_var,
            command=self.toggle_dark_mode
        )
        self.dark_check.pack(side=tk.LEFT)

        # Preview canvas
        self.preview_canvas = tk.Canvas(
            self.preview_frame,
            bg="white",
            bd=2,
            relief=tk.SUNKEN
        )
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)

        # Preview mode toggle (below header)
        self.preview_mode = tk.StringVar(value="layout")
        preview_mode_frame = ttk.Frame(self.preview_frame)
        preview_mode_frame.pack(fill=tk.X, pady=5)

        ttk.Radiobutton(
            preview_mode_frame,
            text="Layout Preview",
            variable=self.preview_mode,
            value="layout",
            command=self.update_preview
        ).pack(side=tk.LEFT, padx=5)

        ttk.Radiobutton(
            preview_mode_frame,
            text="Handwriting Preview",
            variable=self.preview_mode,
            value="handwriting",
            command=self.update_preview
        ).pack(side=tk.LEFT, padx=5)

    def setup_menu(self):
        """Set up the menu bar"""
        menubar = tk.Menu(self.root)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New", command=self.reset_defaults)
        file_menu.add_command(label="Generate", command=self.on_generate)
        file_menu.add_command(label="Export PDF", command=self.export_pdf)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        # call toggle_dark_mode with flip=True so menu toggles the checkbutton state
        view_menu.add_command(label="Toggle Dark Mode", command=lambda: self.toggle_dark_mode(flip=True))
        menubar.add_cascade(label="View", menu=view_menu)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)

    def choose_color(self, color_type):
        """Open color chooser dialog and update the specified color"""
        var = getattr(self, f"{color_type}_var")
        btn = getattr(self, f"{color_type}_btn")
        current_color = var.get()
        color = colorchooser.askcolor(title=f"Choose {color_type.replace('_', ' ').title()}", initialcolor=current_color)
        if color and color[1]:
            var.set(color[1])
            btn.config(bg=color[1])
            self.update_preview()

    def on_color_select(self, event):
        """Handle ink color selection"""
        if self.color_var.get() == "Custom...":
            color = colorchooser.askcolor(title="Choose Custom Ink Color")
            if color and color[1]:
                self.color_var.set(color[1])
        self.update_preview()

    def update_preview(self, event=None):
        """Update the preview display"""
        if self.preview_mode.get() == "layout":
            self.draw_layout_preview()
        else:
            # clear pending preview triggers (thread-safe)
            while not self.preview_queue.empty():
                try:
                    self.preview_queue.get_nowait()
                except queue.Empty:
                    break
            self.preview_queue.put(True)

    def draw_layout_preview(self):
        """Draw the page layout preview"""
        self.preview_canvas.delete("all")

        # Get current dimensions
        canvas_width = self.preview_canvas.winfo_width()
        canvas_height = self.preview_canvas.winfo_height()

        if canvas_width <= 10 or canvas_height <= 10:
            return

        # Calculate page dimensions maintaining aspect ratio
        view_width = self.view_width_var.get()
        view_height = self.view_height_var.get()
        aspect_ratio = view_width / view_height

        if view_height > view_width:
            page_height = canvas_height * 0.9
            page_width = page_height * aspect_ratio
        else:
            page_width = canvas_width * 0.9
            page_height = page_width / aspect_ratio

        # Center the page
        x_offset = (canvas_width - page_width) / 2
        y_offset = (canvas_height - page_height) / 2

        # Draw page background
        page_color = self.page_color_var.get()
        self.preview_canvas.create_rectangle(
            x_offset, y_offset,
            x_offset + page_width, y_offset + page_height,
            fill=page_color, outline="black"
        )

        # Draw margins
        margin_left = self.margin_left_var.get()
        margin_top = self.margin_top_var.get()

        margin_left_pos = x_offset + (margin_left / view_width) * page_width
        margin_top_pos = y_offset + (margin_top / view_height) * page_height

        margin_color = self.margin_color_var.get()
        self.preview_canvas.create_line(
            margin_left_pos, y_offset,
            margin_left_pos, y_offset + page_height,
            fill=margin_color, width=2
        )
        self.preview_canvas.create_line(
            x_offset, margin_top_pos,
            x_offset + page_width, margin_top_pos,
            fill=margin_color, width=2
        )

        # Draw guide lines
        line_height = self.line_height_var.get()
        line_color = self.line_color_var.get()
        total_lines = self.total_lines_var.get()

        current_y = margin_top_pos + (line_height / view_height) * page_height
        for _ in range(total_lines):
            if current_y > y_offset + page_height:
                break

            self.preview_canvas.create_line(
                x_offset + 10, current_y,
                x_offset + page_width - 10, current_y,
                fill=line_color, dash=(2, 2)
            )
            current_y += (line_height / view_height) * page_height

        # Check for text overflow
        text = self.text_box.get("1.0", "end-1c").strip()
        if not text:
            return

        # Calculate how many lines the text would take
        max_line_length = self.max_line_length_var.get()
        wrapped_lines = []
        for line in text.split("\n"):
            if not line:
                wrapped_lines.append("")
                continue
            for i in range(0, len(line), max_line_length):
                wrapped_lines.append(line[i:i+max_line_length])

        if len(wrapped_lines) > total_lines:
            self.preview_canvas.create_text(
                canvas_width / 2, canvas_height / 2,
                text="⚠ Text Overflow - Too Many Lines",
                fill="red",
                font=("Arial", 14, "bold")
            )

    def generate_preview_svg(self):
        """Generate a preview SVG in a temporary file and display it"""
        if not PREVIEW_SUPPORT:
            messagebox.showinfo(
                "Preview Unavailable",
                "Handwriting preview requires cairosvg and Pillow packages.\n"
                "Install with: pip install cairosvg pillow"
            )
            return

        text = self.text_box.get("1.0", "end-1c").strip()
        if not text or text == "Enter your text here...":
            return

        # Create temp directory if needed
        temp_dir = os.path.join(tempfile.gettempdir(), "inkscribe_preview")
        os.makedirs(temp_dir, exist_ok=True)
        temp_file = os.path.join(temp_dir, "preview.svg")

        # Generate the SVG
        try:
            self.generate_handwriting(text, temp_file, preview_mode=True)
            # Convert to PNG and display
            self.display_svg_preview(temp_file)
        except Exception as e:
            print(f"Preview generation error: {e}")

    def display_svg_preview(self, svg_path):
        """Display the SVG preview on canvas"""
        if not os.path.exists(svg_path):
            return

        try:
            # Convert SVG to PNG
            png_path = os.path.join(tempfile.gettempdir(), "inkscribe_preview", "preview.png")
            cairosvg.svg2png(url=svg_path, write_to=png_path)

            # Open and resize the image
            img = Image.open(png_path)
            canvas_width = self.preview_canvas.winfo_width()
            canvas_height = self.preview_canvas.winfo_height()

            if canvas_width <= 10 or canvas_height <= 10:
                return

            # Maintain aspect ratio
            img_ratio = img.width / img.height
            canvas_ratio = canvas_width / canvas_height

            if img_ratio > canvas_ratio:
                new_width = canvas_width - 20
                new_height = int(new_width / img_ratio)
            else:
                new_height = canvas_height - 20
                new_width = int(new_height * img_ratio)

            img = img.resize((new_width, new_height), Image.LANCZOS)

            # Display on canvas
            self.preview_canvas.delete("all")
            photo = ImageTk.PhotoImage(img)
            self.preview_canvas.image = photo  # Keep reference
            self.preview_canvas.create_image(
                canvas_width / 2, canvas_height / 2,
                image=photo, anchor=tk.CENTER
            )
        except Exception as e:
            print(f"Preview display error: {e}")

    def on_generate(self):
        """Generate the final handwriting output"""
        text = self.text_box.get("1.0", "end-1c").strip()
        if not text or text == "Enter your text here...":
            messagebox.showwarning("Input Error", "Please enter some text to generate.")
            return

        output_dir = filedialog.askdirectory(title="Select Output Directory")
        if not output_dir:
            return

        try:
            # Generate the handwriting
            self.generate_handwriting(text, output_dir)
            messagebox.showinfo("Success", "Handwriting generated successfully!")

            # Update preview to show first page
            first_page = os.path.join(output_dir, "result_page_1.svg")
            if os.path.exists(first_page) and PREVIEW_SUPPORT:
                self.display_svg_preview(first_page)
        except Exception as e:
            messagebox.showerror("Generation Error", f"Failed to generate handwriting:\n{e}")

    def generate_handwriting(self, text, output_dir, preview_mode=False):
        """Generate handwriting SVG files"""
        # Get all parameters
        params = {
            "max_line_length": int(self.max_line_length_var.get()),
            "total_lines": int(self.total_lines_var.get()),
            "lines_per_page": int(self.lines_per_page_var.get()),
            "consistency": float(self.consistency_var.get()),
            "style": int(self.style_var.get()),
            "color": self.color_var.get(),
            "pen_thickness": float(self.pen_thickness_var.get()),
            "line_height": int(self.line_height_var.get()),
            "view_width": float(self.view_width_var.get()),
            "view_height": float(self.view_height_var.get()),
            "margin_left": int(self.margin_left_var.get()),
            "margin_top": int(self.margin_top_var.get()),
            "page_color": self.page_color_var.get(),
            "margin_color": self.margin_color_var.get(),
            "line_color": self.line_color_var.get()
        }

        # Process color
        color_map = {
            "Black": "#000000",
            "Blue": "#0000FF",
            "Red": "#FF0000",
            "Green": "#008000"
        }
        stroke_color = color_map.get(params["color"], params["color"])

        # Wrap text into lines
        wrapped_lines = []
        for line in text.split("\n"):
            if not line:
                wrapped_lines.append("")
                continue
            for i in range(0, len(line), params["max_line_length"]):
                wrapped_lines.append(line[i:i+params["max_line_length"]])

        # Check for overflow
        if not preview_mode and len(wrapped_lines) > params["total_lines"]:
            answer = messagebox.askyesno(
                "Text Overflow",
                f"Your text requires {len(wrapped_lines)} lines but only {params['total_lines']} are available.\n"
                "Do you want to proceed with the first page only?"
            )
            if not answer:
                return
            wrapped_lines = wrapped_lines[:params["total_lines"]]

        # Paginate
        pages = [
            wrapped_lines[i:i+params["lines_per_page"]]
            for i in range(0, len(wrapped_lines), params["lines_per_page"])
        ]

        # Create output directory if needed
        if not preview_mode:
            os.makedirs(output_dir, exist_ok=True)

        # Generate each page
        hand = Hand()
        for page_num, page_lines in enumerate(pages):
            if not page_lines:
                continue

            if preview_mode:
                filename = output_dir
            else:
                filename = os.path.join(output_dir, f"result_page_{page_num+1}.svg")

            hand.write(
                filename=filename,
                lines=page_lines,
                biases=[params["consistency"]] * len(page_lines),
                styles=[params["style"]] * len(page_lines),
                stroke_colors=[stroke_color] * len(page_lines),
                stroke_widths=[params["pen_thickness"]] * len(page_lines),
                page=[
                    params["line_height"],
                    params["total_lines"],
                    params["view_height"],
                    params["view_width"],
                    -params["margin_left"],
                    -params["margin_top"],
                    params["page_color"],
                    params["margin_color"],
                    params["line_color"]
                ]
            )

    def export_pdf(self):
        """Export generated SVG files to PDF"""
        if not PDF_SUPPORT:
            messagebox.showinfo(
                "PDF Export Unavailable",
                "PDF export requires svglib and reportlab packages.\n"
                "Install with: pip install svglib reportlab"
            )
            return

        input_dir = filedialog.askdirectory(title="Select Directory with SVG Files")
        if not input_dir:
            return

        output_dir = filedialog.askdirectory(title="Select Output Directory for PDF")
        if not output_dir:
            return

        try:
            count = 0
            for file in os.listdir(input_dir):
                if file.endswith(".svg"):
                    svg_path = os.path.join(input_dir, file)
                    pdf_path = os.path.join(output_dir, file.replace(".svg", ".pdf"))

                    drawing = svg2rlg(svg_path)
                    renderPDF.drawToFile(drawing, pdf_path)
                    count += 1

            messagebox.showinfo("Success", f"Exported {count} PDF files successfully!")
        except Exception as e:
            messagebox.showerror("PDF Export Error", f"Failed to export PDFs:\n{e}")

    def reset_defaults(self):
        """Reset all settings to defaults"""
        # Reset sliders and color vars
        for name, value in self.defaults.items():
            if name in ["page_color", "margin_color", "line_color"]:
                var = getattr(self, f"{name}_var", None)
                btn = getattr(self, f"{name}_btn", None)
                if var is not None:
                    var.set(value)
                if btn is not None:
                    try:
                        btn.config(bg=value)
                    except Exception:
                        pass
            elif hasattr(self, f"{name}_var"):
                getattr(self, f"{name}_var").set(value)
                if hasattr(self, f"{name}_label"):
                    getattr(self, f"{name}_label").config(text=str(value))

        # Reset text box
        self.text_box.delete("1.0", tk.END)
        self.text_box.insert("1.0", "Enter your text here...")
        self.text_box.config(fg="grey")

        # Update preview
        self.update_preview()

    def toggle_dark_mode(self, flip=False):
        """Toggle between dark and light mode.
        If flip=True the function will invert the checkbutton var (used by menu).
        If flip=False it reads the checkbutton var (used by the widget).
        """
        if flip:
            # invert the boolean variable; checkbutton will reflect this
            self.dark_mode_var.set(not self.dark_mode_var.get())

        # set internal state from the BooleanVar
        self.dark_mode = bool(self.dark_mode_var.get())

        bg = "#2e2e2e" if self.dark_mode else "white"
        fg = "white" if self.dark_mode else "black"
        entry_bg = "#3e3e3e" if self.dark_mode else "white"
        entry_fg = "white" if self.dark_mode else "black"

        # Update mode label text
        try:
            self.mode_label.config(text="Mode: Dark" if self.dark_mode else "Mode: Light")
        except Exception:
            pass

        # Update main window background
        try:
            self.root.config(bg=bg)
        except Exception:
            pass

        # Update direct children (best-effort)
        for widget in self.root.winfo_children():
            try:
                widget.config(bg=bg, fg=fg)
            except Exception:
                pass

        # Special handling for text box
        try:
            self.text_box.config(bg=entry_bg, fg=entry_fg, insertbackground=fg)
        except Exception:
            pass

        # Update preview canvas background appropriately
        try:
            self.preview_canvas.config(bg=bg if self.preview_mode.get() == "layout" else "white")
        except Exception:
            pass

        # Force update
        self.update_preview()

    def show_about(self):
        """Show about dialog"""
        about_text = (
    "TextoHand-Text to Handwriting Generator\n"
    "Version 1.0\n\n"
    "Created by Shikhar Pandey\n\n"
    "CodeHand converts typed text into realistic, customizable handwritten pages.\n"
    "Choose from multiple handwriting styles, adjust pen thickness, ink color, line spacing, and margins.\n"
    "Perfect for notes, letters, journals, or creative projects.\n\n"
    "© 2025 Shikhar Pandey"
)
        messagebox.showinfo("About InkScribe Pro", about_text)


if __name__ == "__main__":
    root = tk.Tk()
    app = HandwritingGenerator(root)
    root.mainloop()