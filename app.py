import uuid
import json
from urllib.request import urlopen
from urllib.error import URLError

import streamlit as st
from streamlit_stl import stl_from_file, stl_from_text
from solid2 import *
import tempfile
from pathlib import Path
from solid2.extensions.bosl2 import squircle

if 'stl_file' not in st.session_state:
    tmp_file_path = str(Path(tempfile.gettempdir()) / str(uuid.uuid4()))+".stl" 
    Path(tmp_file_path).touch()  # Create an empty file
    st.session_state.stl_file = tmp_file_path


st.set_page_config(layout="wide")

st.title("Make a Key Fob")

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
    st.error(f"Invalid JSON in {SCHOOL_FILAMENTS_FILE.name}: {e}")
    owned_by_school = []

color_lookup = {c["name"]: c["hex"] for c in all_filament_colors}
owned_color_options = [{"name": name, "hex": color_lookup[name]} for name in owned_by_school if name in color_lookup]

if not owned_color_options:
    st.warning("No matching school-owned colours found. Showing all Bambu colours for now.")
    owned_color_options = all_filament_colors


cols = st.columns(5)
with cols[0]:
    name = st.text_input("What is your Name?", "Streamlit", key='name')
with cols[1]:
    length = st.slider("Length", 10, 100,
                       value=int(round(len(name) * 7.5) + 7.5), key='length')
with cols[2]:
    depth = st.slider("Depth", 10, 100, value=12, key='depth')

with cols[3]:
    height = st.slider("Height", 0.5, 10.0, value=1.0, key='height')

with cols[4]:
    if not owned_color_options:
        st.error("No colours are available. Check network and school_filaments.json")
        color = st.color_picker("Colour", "#2317CC", key='color_file')

    else:
        selected_colour_name = st.selectbox(
            "Filament",
            options=[c["name"] for c in owned_color_options],
            key='filament_name',
        )
        color = color_lookup[selected_colour_name]


# svg is usually just donee by import("file.svg") 
# from solid2 import import_scad
# svgshape = import_scad("file.svg")  # Not sure this will work
# should different designs be done by different classes? 
# Then use pydantic / dataclasses to generate the UI? 
## https://github.com/lukasmasuch/streamlit-pydantic

distance_from_corner = 3


#shape = cube(length, depth, height)
shape = squircle([length, depth], 0.9).linear_extrude(height, center=True).translate(length/2, depth/2, height/2)

#shape = cube(length, depth, height, center=True).translate(0, 0, height/2)
#shape = squircle([length, depth], 2).linear_extrude(height, center=True).translate(0, 0, height/2)

shape -= text(text=name).linear_extrude(height
                                        ,center=True).translate(5, 1, height)
shape -= cylinder(h=height*3, r=1).translate(distance_from_corner, depth-distance_from_corner, 0-height)

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

    st.download_button("Download STL", data=open(st.session_state.stl_file, "rb").read(), file_name=f"key_fob_{name}    .stl", mime="application/octet-stream")

except Exception as e:
    st.error(f"Error: {e}")
    scad_filename = st.session_state.stl_file.replace(".stl", ".scad")
    shape.save_as_scad(scad_filename)
    with open(scad_filename, "r") as file:
        st.code(file.read(), language='scad')