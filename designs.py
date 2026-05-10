from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Any, Callable, Dict, Generic, Literal, TypeVar

import streamlit as st
from solid2 import cube, cylinder, text
from solid2.extensions.bosl2 import (
    BACK,
    BOTTOM,
    FRONT,
    LEFT,
    cyl,
    linear_sweep,
    squircle,
    text3d,
)

from geometry import BoundingBox, measure_shape

TParams = TypeVar("TParams")


@dataclass(frozen=True)
class ControlSpec:
    field_name: str
    label: str
    key: str
    control_type: Literal["text_input", "slider", "dropdown"]
    default: Any
    min_value: int | float | None = None
    max_value: int | float | None = None
    step: int | float | None = None
    default_factory: Callable[[Dict[str, Any]], Any] | None = None
    validation: Callable[[Any], bool | str] | None = None

@st.cache_data(show_spinner=False)
def available_font_options() -> list[str]:
    fallback_fonts = [
        "Liberation Mono",
        "Liberation Sans",
        "DejaVu Sans",
        "Noto Sans",
        "FreeSans",
    ]
    try:
        result = subprocess.run(
            ["fc-list", ":", "family"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return fallback_fonts

    font_names: set[str] = set()
    for line in result.stdout.splitlines():
        for name in line.split(","):
            candidate = name.strip()
            if candidate:
                font_names.add(candidate)

    if not font_names:
        return fallback_fonts

    preferred_order = [
        "Liberation Mono",
        "Liberation Sans",
        "Liberation Serif",
        "DejaVu Sans",
        "DejaVu Serif",
        "Noto Sans",
        "Nimbus Sans",
        "Nimbus Roman",
    ]
    ordered = [name for name in preferred_order if name in font_names]
    extras = sorted(name for name in font_names if name not in ordered)
    return ordered + extras


@st.cache_data(show_spinner=False)
def available_font_style_options(font_family: str) -> list[str]:
    fallback_styles = ["Regular", "Bold", "Italic", "Bold Italic"]
    if not font_family:
        return fallback_styles

    try:
        result = subprocess.run(
            ["fc-list", f":family={font_family}", "style"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return fallback_styles

    style_names: set[str] = set()
    for line in result.stdout.splitlines():
        if "style=" not in line:
            continue
        styles_part = line.split("style=", maxsplit=1)[1]
        for name in styles_part.split(","):
            candidate = name.strip()
            if candidate:
                style_names.add(candidate)

    if not style_names:
        return fallback_styles

    preferred_order = ["Regular", "Book", "Medium", "Bold", "Italic", "Bold Italic"]
    ordered = [name for name in preferred_order if name in style_names]
    extras = sorted(name for name in style_names if name not in ordered)
    return ordered + extras


def compose_font_with_style(font_family: str, font_style: str) -> str:
    family = font_family.strip()
    style = font_style.strip()
    if not style:
        return family
    if ":style=" in family:
        return family
    return f"{family}:style={style}"


def render_controls(control_specs: list[ControlSpec], columns: int = 4) -> dict[str, Any]:
    values: dict[str, Any] = {}
    cols = st.columns(columns)

    for idx, spec in enumerate(control_specs):
        with cols[idx % columns]:
            default_value = spec.default_factory(values) if spec.default_factory else spec.default

            if spec.control_type == "text_input":
                value = st.text_input(
                    spec.label,
                    value=st.session_state.get(spec.key, default_value),
                    key=spec.key,
                )
                if spec.validation:
                    validation_result = spec.validation(value)
                    if validation_result is not True:
                        st.error(validation_result)
                        
            elif spec.control_type == "dropdown":
                if spec.field_name == "font":
                    options = available_font_options()
                elif spec.field_name == "font_style":
                    selected_font = str(values.get("font", st.session_state.get("font", "")))
                    options = available_font_style_options(selected_font)
                else:
                    options = [str(spec.default)]

                current_value = st.session_state.get(spec.key, default_value)
                if current_value not in options:
                    if spec.field_name == "font_style" and "Regular" in options:
                        current_value = "Regular"
                    else:
                        current_value = options[0]
                value = st.selectbox(
                    spec.label,
                    options=options,
                    index=options.index(current_value),
                    key=spec.key,
                )
            elif spec.control_type == "slider":
                slider_kwargs: dict[str, Any] = {
                    "label": spec.label,
                    "min_value": spec.min_value,
                    "max_value": spec.max_value,
                    "value": st.session_state.get(spec.key, default_value),
                    "key": spec.key,
                }
                if spec.step is not None:
                    slider_kwargs["step"] = spec.step
                value = st.slider(**slider_kwargs)
            else:
                raise ValueError(f"Unsupported control type: {spec.control_type}")

            values[spec.field_name] = value

    return values


class BaseDesign(Generic[TParams]):
    name: str
    params_type: type[TParams]
    controls: list[ControlSpec]

    def collect_params(self) -> TParams:
        columns = len(self.controls)
        if columns > 5:
            if columns % 3 == 0:
                columns = 3
            elif columns % 4 == 0:
                columns = 4
            else:
                columns = 5
        values = render_controls(self.controls, columns=columns)
        return self.params_type(**values)

    def build_shape(self, params: TParams):
        raise NotImplementedError


@dataclass
class KeyFobParams:
    name: str
    length: int
    depth: int
    height: float
    

@dataclass
class KeyFobParamsLogan:
    name: str
    length: int
    height: float
    buffer: float
    font: str = "Liberation Mono"
    font_style: str = "Regular"


class LoganKeyFobDesign(BaseDesign[KeyFobParamsLogan]):
    name = "Key Fob Logan"
    params_type = KeyFobParamsLogan

    controls = [
        ControlSpec(
            field_name="name",
            label="What is your Name?",
            key="name",
            control_type="text_input",
            default="Streamlit",
            validation=lambda x: len(x) > 0 or "Name cannot be empty",
        ),
        ControlSpec(
            field_name="font",
            label="Font",
            key="font",
            control_type="dropdown",
            default="Liberation Mono",
        ),
        ControlSpec(
            field_name="font_style",
            label="Font Style",
            key="font_style",
            control_type="dropdown",
            default="Regular",
        ),
        ControlSpec(
            field_name="length",
            label="Length",
            key="length",
            control_type="slider",
            min_value=10,
            max_value=100,
            default=50,
        ),
        ControlSpec(
            field_name="buffer",
            label="Buffer",
            key="buffer",
            control_type="slider",
            min_value=1.0,
            max_value=10.0,
            step=0.1,
            default=2.5,
        ),
        ControlSpec(
            field_name="height",
            label="Height",
            key="height",
            control_type="slider",
            min_value=1.0,
            max_value=10.0,
            step=0.1,
            default=3.0,
        ),
    ]
    

    def calculate_text_bounding_box(_self, txt: str, font: str) -> BoundingBox:
        text_shape = text(text=txt, font=font).linear_extrude(1)
        bounds = measure_shape(text_shape).bounds
        
        return text_shape, bounds
    

    def build_text_shape(self, params: KeyFobParamsLogan):
        effective_font = compose_font_with_style(params.font, params.font_style)
        # Create the text shape, extrude it
        text_shape, bounds = self.calculate_text_bounding_box(txt=params.name, font=effective_font)

        # Calculate the new length of the text after accounting for the buffer, then scale the text shape to fit within the desired length
        new_text_length = params.length - (params.buffer * 3) # the end with the hole is a buffer wider
        
        # Calculate the scale factor based on the new text length and the original text length, then scale the text shape accordingly
        scale_factor = new_text_length / bounds.size[0]

        #Make the text again so we have the height ok
        text_shape = text(text=params.name, font=effective_font).translate(bounds.translation_to_zero())
        text_shape = text_shape.scale(scale_factor).linear_extrude(params.height)
        
        return text_shape, bounds, scale_factor
    
    def build_shape(self, params: KeyFobParamsLogan):
        text_shape, bounds, scale_factor = self.build_text_shape(params)

        depth = (bounds.size[1] * scale_factor) + params.buffer * 2

        # Create the base shape as a cube with the calculated dimensions
        shape = cube([params.length, depth, params.height])
        
        # move the text up by half the thickness and right by 2 buffers and forward by the buffer, then cut it out of the base shape
        shape -= text_shape.up(params.height/2).right(params.buffer*2).forward(params.buffer)

        #  then translating the hole into the top left corner
        shape -= (
            cylinder(h=params.height * 3, r=1.5, _fn=16)
            .right(params.buffer)
            .forward(depth - params.buffer)
            .down(params.height)
        )

        return shape

class RoundedFobDesign(LoganKeyFobDesign):
    name = "Rounded Fob"

    def build_shape(self, params: KeyFobParamsLogan):
        text_shape, bounds, scale_factor = self.build_text_shape(params)

        # Calculate the new depth of the shape based on the scaled text size and the buffer
        depth = (bounds.size[1] * scale_factor) + params.buffer * 2

        # Create the base shape as a cube with the calculated dimensions
        shape = squircle([params.length, depth], 0.8).forward(depth / 2).right(params.length / 2).linear_extrude(params.height)
        
        # move the text up by half the thickness and right by 2 buffers and forward by the buffer, then cut it out of the base shape
        shape -= text_shape.up(params.height/2).right(params.buffer*2).forward(params.buffer)

        #  then translating the hole into the top left corner
        shape -= (
            cylinder(h=params.height * 3, r=1.5, _fn=16)
            .right(params.buffer)
            .forward(depth - params.buffer)
            .down(params.height)
        )

        return shape


class RoundedBSOL2Design(LoganKeyFobDesign):
    name = "BSOL Fob"

    def calculate_text_bounding_box(self, txt: str, font: str):
        probe = text3d(text=txt, font=font, size=10, h=1, anchor=BOTTOM+LEFT+FRONT)
        return measure_shape(probe).bounds

    def build_text_shape(self, params: KeyFobParamsLogan):
        effective_font = compose_font_with_style(params.font, params.font_style)
        bounds = self.calculate_text_bounding_box(txt=params.name, font=effective_font)
        left_text_buffer = params.buffer * 2
        right_text_buffer = params.buffer
        new_text_length = params.length - left_text_buffer - right_text_buffer
        measured_text = measure_shape(
            text3d(
            text=params.name,
            font=effective_font,
            size=10,
            h=params.height,
            anchor=LEFT,
        )
        ).resize_to(x=new_text_length)
        text_shape = measured_text.position(BOTTOM + LEFT + FRONT)
        text_depth = measured_text.bounds.size[1]

        return text_shape, text_depth

    def build_shape(self, params: KeyFobParamsLogan):
        text_shape, text_depth = self.build_text_shape(params)
        left_text_buffer = params.buffer * 2
        right_text_buffer = params.buffer
        top_bottom_buffer = params.buffer
        depth = text_depth + top_bottom_buffer * 2

        base = linear_sweep(
            region=squircle([params.length, depth], 0.8, anchor=LEFT+FRONT),
            height=params.height,
            #anchor=BOTTOM + LEFT + FRONT,
        )

        hole = (
            cyl(h=params.height * 3, r=1.5, _fn=16)
            .position( LEFT + BACK)
            .right(params.buffer)
            .back(params.buffer)
            .tag("remove")
        )

        text_cutout = (
            text_shape
            .right(left_text_buffer)
            .fwd(top_bottom_buffer)
            .tag("remove")
        )

        return base(hole, text_cutout).diff()

DESIGNS: dict[str, BaseDesign[Any]] = {
    LoganKeyFobDesign.name: LoganKeyFobDesign(),  
    RoundedFobDesign.name: RoundedFobDesign(),
    RoundedBSOL2Design.name: RoundedBSOL2Design(),
}
