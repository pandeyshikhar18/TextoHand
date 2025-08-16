# TextoHand

Need to convert typed text into realistic, customizable handwriting? Whether it's for notes, letters, or creative projects, TextoHand has got you covered.

TextoHand uses Machine Learning to generate authentic handwriting by introducing controlled randomness and variations, making each output look naturally written. It supports multiple handwriting styles and a variety of customization options to make your documents truly unique.

## Features

- Realistic Handwriting Generation with a Recurrent Neural Network (RNN)
- Choose from multiple predefined handwriting styles
- Adjust line spacing, page size, margins, ink color, pen thickness, and more
- Dark Mode support for comfortable night-time usage
- User-friendly interface with live preview
- Automatically splits large texts into multiple lines, paragraphs, and pages
- Scalable SVG output that preserves quality on resizing

## Screenshots

![TextoHand Screenshot](https://github.com/pandeyshikhar18/TextoHand/raw/main/screenshots/gui_screenshot.png)

## Getting Started

There are two ways to get started:

### Download the Executable

1. Head to the Releases page and download the `TextoHand-v1.0.zip` package.
2. Unzip the file and double-click `TextoHand.exe` to launch the application.

### Clone the Repository

1. Clone this repo using:
    ```bash
    git clone https://github.com/pandeyshikhar18/TextoHand.git
    ```
2. Navigate to the cloned directory:
    ```bash
    cd TextoHand
    ```
3. With Anaconda installed, create the environment:
    ```bash
    conda env create -f environment.yml
    conda activate textohand_env
    ```
4. Run the program:
    ```bash
    python gui.py
    ```

## Usage

1. Launch the application (either `python gui.py` or double-click the executable).
2. Enter your text and customize the settings (style, pen thickness, margins, etc.).
3. Preview the layout and handwriting style.
4. Enable Dark Mode if desired.
5. Click **Generate** and select the destination folder.
6. Wait for the handwriting files to be created.

## Known Issues

- Some antivirus programs may flag the executable; this is due to the way Python programs are packaged and is safe to ignore.
- The application may briefly freeze while generating large documents; it does not crash.

## Future Plans

- More handwriting styles and increased character support
- Enhanced dark mode and UI responsiveness
- Additional text formatting options (alignment, ink colors per line)
- Build an installer for easier installation

## Acknowledgements

This project is inspired by the handwriting-synthesis repository by sjvasquez and based on the paper *Generating Sequences with Recurrent Neural Networks* by Alex Graves.
