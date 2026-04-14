# solid_design

Small Streamlit app for generating a simple 3D nameplate/tag and exporting it as an STL.

The app uses `solidpython2` to build the geometry, relies on OpenSCAD for STL generation, and displays the result in the browser with `streamlit_stl`.

## What It Does

- Takes a name as input
- Lets you adjust length, depth, and height
- Cuts the text into the base shape
- Adds a small mounting hole
- Generates an STL for preview and download

## Project Files

- `app.py` - Streamlit application and geometry generation logic
- `requirements.txt` - Python dependencies
- `packages.txt` - System dependency list for environments that install apt packages
- `app.scad` - Generated OpenSCAD output
- `app.stl.scad` - Generated SCAD source emitted by the model pipeline
- `squirrel.stl` - Example STL asset in the repository

## Requirements

- Python 3.10+
- OpenSCAD available on the system

On Debian/Ubuntu systems:

```bash
sudo apt-get update
sudo apt-get install -y openscad
```

## Installation

Create a virtual environment, install Python dependencies, and ensure OpenSCAD is installed:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

Start the Streamlit app from the repository root:

```bash
streamlit run app.py
```

Then open the local URL shown by Streamlit in your browser.

## Usage

1. Enter the text to engrave.
2. Adjust the dimensions with the sliders.
3. Inspect the rendered STL in the browser.
4. Download the generated `app.stl` file.

## Notes

- `packages.txt` lists `openscad`, which is required for STL generation.
- If STL generation fails, the app falls back to showing generated SCAD output.
- The default shape in `app.py` is currently a rectangular base. There is also a commented `squircle` variant available in the source.

## License

This project is licensed under the terms of the [LICENSE](LICENSE) file.