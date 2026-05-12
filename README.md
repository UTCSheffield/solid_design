# solid_design


Small Streamlit app for generating customizable 3D nameplates, tags, and fobs, and exporting them as STL files.


The app uses `solidpython2` to build the geometry, relies on OpenSCAD for STL generation, and displays the result in the browser with `streamlit_stl`.

## Design System

The app supports multiple design types (e.g. squircle fob, square fob) using a dataclass-driven system in the `designs/` package. Each design defines its own geometry and UI controls, and gets registered in `designs/__init__.py`.

To experiment with new shapes or features, use `examples/prototype.py` as a scratchpad for geometry prototyping before integrating your design into the main app.

For layout work, `geometry.py` includes helpers to render a SolidPython shape to STL through OpenSCAD, measure its true bounding box back from the mesh, and compute the translate vector needed to center it.

## What It Does

- Takes a name as input
- Lets you adjust length, depth, and height
- Cuts the text into the base shape
- Adds a small mounting hole
- Generates an STL for preview and download


- `app.py` - Streamlit application and main UI logic
- `designs/` - Design package split by responsibility:
	- `designs/common.py` - shared controls, font helpers, and base class
	- `designs/keyfobs.py` - keyfob design classes
	- `designs/svg_keyfob.py` - SVG Keyfob design with name cutout and silhouette
	- `designs/__init__.py` - package exports and `DESIGNS` registry
- `geometry.py` - STL-based bounding-box and centering helpers for SolidPython shapes
- `examples/prototype.py` - Geometry prototyping and experimentation (not part of main app flow)
- `prototype.py` - compatibility shim that delegates to `examples/prototype.py`
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
- The default shape is now selectable via the UI. You can add new shapes by creating a design class under `designs/` and registering it in `designs/__init__.py`.
- Use `examples/prototype.py` to quickly try out new geometry ideas before formalizing them as a new design class.
- Call `calculate_shape_bounding_box(shape)` to get `min_corner`, `max_corner`, `size`, `center`, and `translation_to_center()`.

## Add A New Design

1. Create a new module under `designs/` (for example `designs/my_new_design.py`).
2. Add a params dataclass and a design class that extends `BaseDesign`.
3. Define `controls` with `ControlSpec` for Streamlit input fields.
4. Implement `build_shape(params)` to return a SolidPython shape.
5. Register an instance in `DESIGNS` inside `designs/__init__.py`.

## License

This project is licensed under the terms of the [LICENSE](LICENSE) file.