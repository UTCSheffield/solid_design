import uuid
import json
import hashlib
from urllib.request import urlopen
from urllib.error import URLError

import streamlit as st
from streamlit_stl import stl_from_file, stl_from_text
import tempfile
from pathlib import Path
import trimesh

from designs import DESIGNS

PLA_DENSITY_G_PER_MM3 = 0.00125
PRINT_SPEED_G_PER_HOUR = 15.0  # Lower-end estimate for Bambu Studio standard speed on 0.4mm nozzle

# Ensure we have a temporary STL file to work with in the session state
if 'stl_file' not in st.session_state:
    tmp_file_path = str(Path(tempfile.gettempdir()) / str(uuid.uuid4()))+".stl" 
    st.session_state.stl_file = tmp_file_path

# Create an empty STL file if it doesn't exist
if not Path(st.session_state.stl_file).exists():
    Path(st.session_state.stl_file).touch()  # Create an empty file

page_title = "UTC OLP - Custom 3D Stuff Designer"
st.set_page_config(layout="wide", page_title=page_title, page_icon="🔑")

st.title(page_title)

# https://3dfilamentprofiles.com/filaments/bambu-lab/pla
BAMBU_COLORS_URL = "https://raw.githubusercontent.com/dadequate/bambu-lab-filament-colors/refs/heads/main/colors.json"
SCHOOL_FILAMENTS_FILE = "school_filaments.json"

# Load filament color data with caching to avoid repeated network requests
@st.cache_data(ttl=60 * 60 * 24, show_spinner=False)
def load_bambu_filament_colors():
    with urlopen(BAMBU_COLORS_URL, timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))
    colors = payload.get("colors", [])
    return [
        {
            "name": c.get("name", "").strip(),
            "hex": c.get("hex", "").strip().upper(),
        }
        for c in colors
        if c.get("name") and c.get("hex")
    ]

# Load school-owned filament colors from a local JSON file
def load_school_owned_filaments(file_path: str):
    with open(file_path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    return payload.get("owned_filaments", [])

try:
    all_filament_colors = load_bambu_filament_colors()
except (URLError, TimeoutError, json.JSONDecodeError) as e:
    st.error(f"Could not load Bambu colour catalogue: {e}")
    all_filament_colors = []

try:
    owned_by_school = load_school_owned_filaments(str(SCHOOL_FILAMENTS_FILE))
except FileNotFoundError:
    st.error(f"Missing school filament list: {SCHOOL_FILAMENTS_FILE}")
    owned_by_school = []
except json.JSONDecodeError as e:
    st.error(f"Invalid JSON in {SCHOOL_FILAMENTS_FILE}: {e}")
    owned_by_school = []

# Create a lookup of color names to hex values for easy access when rendering the color selection dropdown
color_lookup = {c["name"]: c["hex"] for c in all_filament_colors}
owned_color_options = [{"name": name, "hex": color_lookup[name]} for name in owned_by_school if name in color_lookup]

if not owned_color_options:
    st.warning("No matching school-owned colours found. Showing all Bambu colours for now.")
    owned_color_options = all_filament_colors

# UI for selecting the design and filament color
cols = st.columns(2)
with cols[0]:
    design = st.selectbox("Design", options=list(DESIGNS.keys()), key='design')

with cols[1]:
    if not owned_color_options and all_filament_colors:
        selected_colour_name = all_filament_colors[0]["name"]
    elif not owned_color_options and not all_filament_colors:
        selected_colour_name = "Default"
    else:
        selected_colour_name = st.selectbox(
            "Filament",
            options=[c["name"] for c in owned_color_options],
            key='filament_name',
        )

color = color_lookup.get(selected_colour_name, "#B0B0B0")

selected_design = DESIGNS[design]
params = selected_design.collect_params()

def file_safe_name(name: str) -> str:
    return name.lower().replace(" — ", "-").replace(" ", "_")


def format_duration(hours: float) -> str:
    total_minutes = max(1, round(hours * 60))
    h, m = divmod(total_minutes, 60)
    return f"{h}h {m}m" if h else f"{m}m"

name_for_file = getattr(params, "name", design)

save_as_filename = f"OLP_{file_safe_name(design)}_{file_safe_name(str(name_for_file))}_{file_safe_name(selected_colour_name)}.stl"

# Build the shape, save it as an STL file, and render it in the Streamlit app with a download button
shape = None
try:
    shape = selected_design.build_shape(params)

    shape.save_as_stl(st.session_state.stl_file)

    with open(st.session_state.stl_file, "rb") as f:
        stl_data = f.read()
    stl_hash = hashlib.md5(stl_data).hexdigest()
    
    stl_from_text(  text=stl_data,
                    color=color,
                    material="material",
                    auto_rotate=True,
                    opacity=1.0,
                    height=500,
                    shininess=100,
                    cam_v_angle=60,
                    cam_h_angle=-90,
                    cam_distance=50,
                    max_view_distance=1000,
                          key=f"example1_{stl_hash}")

    # UI for estimating print time and filament usage
    cols = st.columns(3)

    infill_label_to_percent = {
        "0%": 0,
        "5%": 5,
        "10%": 10,
        "15%": 15,
        "20%": 20,
        "50%": 50,
    }

    with cols[0]:
        st.download_button("Download STL",
                       data=stl_data,
                       file_name=save_as_filename,
                       mime="application/octet-stream")
    
    with cols[1]:
        infill_label = st.selectbox(
            "Infill Density",
            options=list(infill_label_to_percent.keys()),
            index=2,
            key="infill",
        )

    with cols[2]:
        # Load the STL file
        mesh = trimesh.load(st.session_state.stl_file)

        # Calculate mesh volume (mm^3)
        volume_mm3 = max(0.0, float(mesh.volume))

        # Approximate material usage based on infill percentage.
        # 20% baseline approximates walls/top/bottom + sparse infill.
        infill_percent = infill_label_to_percent[infill_label]
        infill_multiplier = infill_percent / 20 if infill_percent > 0 else 0.25

        # Calculate filament weight (grams)
        # Assume PLA density ≈ 1.25 g/cm^3 = 0.00125 g/mm^3
        weight_g = volume_mm3 * PLA_DENSITY_G_PER_MM3 * infill_multiplier
        estimated_hours = weight_g / PRINT_SPEED_G_PER_HOUR if weight_g > 0 else 0.0

        st.markdown(f"**Estimated Print Time:** {format_duration(estimated_hours)}")
        st.markdown(f"**Estimated Filament Usage:** {weight_g:.2f}g")   
        st.caption("Estimate uses 15g/hour (lower-end standard speed for 0.4mm nozzle).")


except Exception as e:
    st.error(f"Error: {e}")
    if shape is not None:
        scad_filename = st.session_state.stl_file.replace(".stl", ".scad")
        shape.save_as_scad(scad_filename)
        with open(scad_filename, "r") as file:
            st.code(file.read(), language='scad')