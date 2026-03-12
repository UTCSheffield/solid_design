import uuid

import streamlit as st
from streamlit_stl import stl_from_file, stl_from_text
from solid2 import *
import tempfile
from pathlib import Path


if 'stl_file' not in st.session_state:
    tmp_file_path = str(Path(tempfile.gettempdir()) / str(uuid.uuid4()))+".stl" 
    st.session_state.stl_file = tmp_file_path


st.set_page_config(layout="wide")

st.title("Make a Key Fob")


cols = st.columns(4)
with cols[0]:
    name = st.text_input("What is your Name?", "Streamlit", key='name')
with cols[1]:
    length = st.slider("Length", 10, 100,
                       value=int(round(len(name) * 7.5) + 7.5), key='length')
with cols[2]:
    depth = st.slider("Depth", 10, 100, value=12, key='depth')

with cols[3]:
    height = st.slider("Height", 0.5, 10.0, value=1.0, key='height')




# svg is usually just donee by import("file.svg") 
# from solid2 import import_scad
# svgshape = import_scad("file.svg")  # Not sure this will work
# should different designs be done by different classes? 
# Then use pydantic / dataclasses to generate the UI? 
## https://github.com/lukasmasuch/streamlit-pydantic
<<<<<<< HEAD

distance_from_corner = 3

=======
>>>>>>> c8a14d2 (Refactor controls and improve UI elements for key fob application)

shape = cube(length, depth, height)

#shape = cube(length, depth, height, center=True).translate(0, 0, height/2)
#shape = squircle([length, depth], 2).linear_extrude(height, center=True).translate(0, 0, height/2)

shape -= text(text=name).linear_extrude(height
                                        ,center=True).translate(5, 1, height)
shape -= cylinder(h=height*3, r=1).translate(distance_from_corner, depth-distance_from_corner, 0-height)

try:
    shape.save_as_stl(st.session_state.stl_file)

<<<<<<< HEAD
        
    st.subheader("View controls!")
    cols = st.columns(5)
    with cols[0]:
        color = st.color_picker("Pick a color", "#005EFF", key='color_file')
    with cols[1]:
        material = st.selectbox("Select a material", ["material", "flat", "wireframe"], key='material_file')
    with cols[2]:
        st.write('\n'); st.write('\n')
        auto_rotate = st.toggle("Auto rotation", key='auto_rotate_file',value=True)
    with cols[3]:
        opacity = st.slider("Opacity", min_value=0.0, max_value=1.0, value=1.0, key='opacity_file')
    with cols[4]:
        height = st.slider("Height", min_value=50, max_value=1000, value=500, key='height_file')

    stl_from_file(  file_path=st.session_state.stl_file, 
                    color=color,
                    material=material,
                    auto_rotate=auto_rotate,
                    opacity=opacity,
                    height=height,
                    shininess=100,
                    cam_v_angle=60,
                    cam_h_angle=-90,
                    cam_distance=50,
                    max_view_distance=1000,
                    key='example1')

    st.download_button("Download STL", data=open(st.session_state.stl_file, "rb").read(), file_name=f"key_fob_{name}.stl", mime="application/octet-stream")
=======
with open("app.stl", "r") as file:
    file_path='app.stl'
    
st.subheader("View controls!")
cols = st.columns(5)
with cols[0]:
    color = st.color_picker("Pick a color", "#005EFF", key='color_file')
with cols[1]:
    material = st.selectbox("Select a material", ["material", "flat", "wireframe"], key='material_file')
with cols[2]:
    st.write('\n'); st.write('\n')
    auto_rotate = st.toggle("Auto rotation", key='auto_rotate_file',value=True)
with cols[3]:
    opacity = st.slider("Opacity", min_value=0.0, max_value=1.0, value=1.0, key='opacity_file')
with cols[4]:
    height = st.slider("Height", min_value=50, max_value=1000, value=500, key='height_file')

stl_from_file(  file_path=file_path, 
                color=color,
                material=material,
                auto_rotate=auto_rotate,
                opacity=opacity,
                height=height,
                shininess=100,
                cam_v_angle=60,
                cam_h_angle=-90,
                cam_distance=50,
                max_view_distance=1000,
                key='example1')
>>>>>>> c8a14d2 (Refactor controls and improve UI elements for key fob application)

except Exception as e:
    st.error(f"Error: {e}")
    scad_filename = st.session_state.stl_file.replace(".stl", ".scad")
    shape.save_as_scad(scad_filename)
    with open(scad_filename, "r") as file:
        st.code(file.read(), language='scad')