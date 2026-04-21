# solid_design


Small Streamlit app for generating customizable 3D nameplates, tags, and fobs, and exporting them as STL files.


The app uses `solidpython2` to build the geometry, relies on OpenSCAD for STL generation, and displays the result in the browser with `streamlit_stl`.

## Design System

The app supports multiple design types (e.g. squircle fob, square fob) using a dataclass-driven system in `designs.py`. Each design defines its own geometry and UI controls. You can easily add new designs by subclassing an existing design or creating a new one, then registering it in the `DESIGNS` dictionary.

To experiment with new shapes or features, use `prototype.py` as a scratchpad for geometry prototyping before integrating your design into the main app.

For layout work, `geometry.py` includes helpers to render a SolidPython shape to STL through OpenSCAD, measure its true bounding box back from the mesh, and compute the translate vector needed to center it.

## What It Does

- Takes a name as input
- Lets you adjust length, depth, and height
- Cuts the text into the base shape
- Adds a small mounting hole
- Generates an STL for preview and download


- `app.py` - Streamlit application and main UI logic
- `designs.py` - Design classes and registry for different fob/tag types
- `geometry.py` - STL-based bounding-box and centering helpers for SolidPython shapes
- `prototype.py` - Geometry prototyping and experimentation (not part of main app flow)
- `school_filaments.json` - List of school-owned filament names used to filter selectable colours
- `requirements.txt` - Python dependencies
- `packages.txt` - System dependency list for streamlit.app


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

1. Select a design type from the dropdown (e.g. Key Fob, Square Fob).
2. Enter the text to engrave.
3. Adjust the dimensions with the sliders.
4. Inspect the rendered STL in the browser.
5. Download the generated STL file.


## Notes

- `packages.txt` lists `openscad`, which is required for STL generation.
- `school_filaments.json` must contain names that exactly match entries in the Bambu colour catalogue.
- If STL generation fails, the app falls back to showing generated SCAD output.
- The default shape is now selectable via the UI. You can add new shapes by editing `designs.py`.
- Use `prototype.py` to quickly try out new geometry ideas before formalizing them as a new design class.
- Call `calculate_shape_bounding_box(shape)` to get `min_corner`, `max_corner`, `size`, `center`, and `translation_to_center()`.

## License

This project is licensed under the terms of the [LICENSE](LICENSE) file.