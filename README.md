TextoHand 

Need to convert typed text into realistic, customizable handwriting? Whether it's for notes, letters, or creative projects, TextoHand has got you covered.

TextoHand uses Machine Learning to generate authentic handwriting by introducing controlled randomness and variations, making each output look naturally written. It supports multiple handwriting styles and a variety of customization options to make your documents truly unique.


Realistic Handwriting Generation with a Recurrent Neural Network (RNN)

Choose from multiple predefined handwriting styles.

Adjust line spacing, page size, margins, ink color, pen thickness, and more.

Dark Mode support for comfortable night-time usage

User-friendly interface with live preview

Automatically splits large texts into multiple lines, paragraphs, and pages

Scalable SVG output that preserves quality on resizing

Getting Started

There are two ways to get started:

Download the Executable:

Head to the Releases page and download the TextoHand-v1.0.zip package.

Unzip the file and double-click TextoHand.exe to launch the application.

Clone the Repository:

Clone this repo using:

git clone https://github.com/yourusername/textohand.git


Navigate to the cloned directory.

With Anaconda installed, run:

conda env create -f environment.yml
conda activate textohand_env


Run the program with:

python gui.py

Usage

Launch the application (python gui.py or double-click the executable).

Enter your text and customize the settings (style, pen thickness, margins, etc.).

Preview the layout and handwriting style.

Enable Dark Mode if desired.

Click Generate and select the destination folder.

Wait for the handwriting files to be created.

Known Issues

Some antivirus programs may flag the executable; this is due to the way Python programs are packaged and is safe to ignore.

The application may briefly freeze while generating large documents; it does not crash.

Future Plans

More handwriting styles and increased character support

Enhanced dark mode and UI responsiveness

Additional text formatting options (alignment, ink colors per line)

Build an installer for easier installation

Acknowledgements

This project is inspired by the handwriting-synthesis repository by sjvasquez and based on the paper Generating Sequences with Recurrent Neural Networks by Alex Graves.