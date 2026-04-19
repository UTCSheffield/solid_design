import uuid
import json
from urllib.request import urlopen
from urllib.error import URLError

import streamlit as st
from streamlit_stl import stl_from_file, stl_from_text
import tempfile
from pathlib import Path

from designs import DESIGNS

if 'stl_file' not in st.session_state:
    tmp_file_path = str(Path(tempfile.gettempdir()) / str(uuid.uuid4()))+".stl" 
    st.session_state.stl_file = tmp_file_path

if not Path(st.session_state.stl_file).exists():
    Path(st.session_state.stl_file).touch()  # Create an empty file
    
page_title = "UTC OLP - Custom 3D Stuff Designer"
st.set_page_config(layout="wide", page_title=page_title, page_icon="🔑")

st.title(page_title)

# https://3dfilamentprofiles.com/filaments/bambu-lab/pla
BAMBU_COLORS_URL = "https://raw.githubusercontent.com/dadequate/bambu-lab-filament-colors/refs/heads/main/colors.json"
SCHOOL_FILAMENTS_FILE = "school_filaments.json"


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

color_lookup = {c["name"]: c["hex"] for c in all_filament_colors}
owned_color_options = [{"name": name, "hex": color_lookup[name]} for name in owned_by_school if name in color_lookup]

if not owned_color_options:
    st.warning("No matching school-owned colours found. Showing all Bambu colours for now.")
    owned_color_options = all_filament_colors

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

shape = selected_design.build_shape(params)

name_for_file = getattr(params, "name", design)

save_as_filename = f"OLP_{file_safe_name(design)}_{file_safe_name(str(name_for_file))}_{file_safe_name(selected_colour_name)}.stl"

try:
    shape.save_as_stl(st.session_state.stl_file)
    
    stl_from_file(  file_path=st.session_state.stl_file, 
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
                    key='example1')

    st.download_button("Download STL",
                       data=open(st.session_state.stl_file, "rb").read(),
                       file_name=save_as_filename,
                       mime="application/octet-stream")

except Exception as e:
    st.error(f"Error: {e}")
    scad_filename = st.session_state.stl_file.replace(".stl", ".scad")
    shape.save_as_scad(scad_filename)
    with open(scad_filename, "r") as file:
        st.code(file.read(), language='scad')