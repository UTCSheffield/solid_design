import streamlit as st
from streamlit_stl import stl_from_file, stl_from_text
from solid2 import *

st.set_page_config(layout="wide")

st.title("Streamlit STL Examples")

cols = st.columns(4)
with cols[0]:
    name = st.text_input("What is your Name?", "Streamlit")
with cols[1]:
    length = st.slider("Length", 10, 100,
                       value=int(round(len(name) * 7.5) + 7.5))
with cols[2]:
    depth = st.slider("Depth", 10, 100, value=12)

with cols[3]:
    height = st.slider("Height", 0.5, 10.0, value=1.0)

shape = cube(length, depth, height)
shape -= text(text=name).linear_extrude(height
                                        ,center=True).translate(5, 1, height)
shape -= cylinder(3,1,height,True).translate(2, depth-4, 0)
shape.save_as_stl()

file_path='squirrel.stl'

with open("app.stl", "r") as file:
    file_path='app.stl'
    
st.subheader("Look: a flexi squirrel!")
cols = st.columns(5)
with cols[0]:
    color = st.color_picker("Pick a color", "#FF9900", key='color_file')
with cols[1]:
    material = st.selectbox("Select a material", ["material", "flat", "wireframe"], key='material_file')
with cols[2]:
    st.write('\n'); st.write('\n')
    auto_rotate = st.toggle("Auto rotation", key='auto_rotate_file')
with cols[3]:
    opacity = st.slider("Opacity", min_value=0.0, max_value=1.0, value=1.0, key='opacity_file')
with cols[4]:
    height = st.slider("Height", min_value=50, max_value=1000, value=500, key='height_file')

# camera position
cols = st.columns(4)
with cols[0]:
    cam_v_angle = st.number_input("Camera Vertical Angle", value=60, key='cam_v_angle')
with cols[1]:
    cam_h_angle = st.number_input("Camera Horizontal Angle", value=-90, key='cam_h_angle')
with cols[2]:
    cam_distance = st.number_input("Camera Distance", value=0, key='cam_distance')
with cols[3]:
    max_view_distance = st.number_input("Max view distance", min_value=1, value=1000, key='max_view_distance')

stl_from_file(  file_path=file_path, 
                color=color,
                material=material,
                auto_rotate=auto_rotate,
                opacity=opacity,
                height=height,
                shininess=100,
                cam_v_angle=cam_v_angle,
                cam_h_angle=cam_h_angle,
                cam_distance=cam_distance,
                max_view_distance=max_view_distance,
                key='example1')

file_input = st.file_uploader("Or upload a STL file ", type=["stl"])
