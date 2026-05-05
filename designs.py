from __future__ import annotations

from dataclasses import dataclass
from tkinter import font
from typing import Any, Callable, Dict, Generic, Literal, TypeVar

import streamlit as st
from solid2 import cube, cylinder, text
from solid2.extensions.bosl2 import squircle

from geometry import BoundingBox, calculate_shape_bounding_box, center_shape_on_origin

TParams = TypeVar("TParams")


@dataclass(frozen=True)
class ControlSpec:
    field_name: str
    label: str
    key: str
    control_type: Literal["text_input", "slider"]
    default: Any
    min_value: int | float | None = None
    max_value: int | float | None = None
    step: int | float | None = None
    default_factory: Callable[[Dict[str, Any]], Any] | None = None


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
            elif spec.control_type == "dropdown":
                value = st.selectbox(
                    spec.label,
                    options=["Liberation Mono", "Arial", "Times New Roman"],
                    index=0,
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
        ),
        ControlSpec(
            field_name="font",
            label="Font",
            key="font",
            control_type="dropdown",
            default="Liberation Mono",
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
    
    @st.cache_data
    def calculate_text_bounding_box(_self, txt: str, font: str) -> BoundingBox:
        
        textshape = text(text=txt, font=font).linear_extrude(1)


        # Calculate the bounding box of the text shape
        bounds = calculate_shape_bounding_box(textshape)
        
        return textshape, bounds

    def build_text_shape(self, params: KeyFobParamsLogan):
        # Create the text shape, extrude it
        textshape, bounds = self.calculate_text_bounding_box(txt=params.name, font=params.font)

        # Calculate the new length of the text after accounting for the buffer, then scale the text shape to fit within the desired length
        new_text_length = params.length - (params.buffer * 3) # the end with the hole is a buffer wider
        
        # Calculate the scale factor based on the new text length and the original text length, then scale the text shape accordingly
        scale_factor = new_text_length / bounds.size[0]

        #Make the text again so we have the height ok
        textshape = text(text=params.name, font=params.font).translate(*bounds.translation_to_zero())
        textshape = textshape.scale(scale_factor).linear_extrude(params.height)
        
        return textshape, bounds, scale_factor
    
    def build_shape(self, params: KeyFobParamsLogan):
        textshape, bounds, scale_factor = self.build_text_shape(params)

        depth = (bounds.size[1] * scale_factor) + params.buffer * 2

        # Create the base shape as a cube with the calculated dimensions
        shape = cube([params.length, depth, params.height])
        
        # move the text up by half the thickness and right by 2 buffers and forward by the buffer, then cut it out of the base shape
        shape -= textshape.up(params.height/2).right(params.buffer*2).forward(params.buffer)

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
        textshape, bounds, scale_factor = self.build_text_shape(params)

        # Calculate the new depth of the shape based on the scaled text size and the buffer
        depth = (bounds.size[1] * scale_factor) + params.buffer * 2

        # Create the base shape as a cube with the calculated dimensions
        shape = squircle([params.length, depth], 0.8).forward(depth / 2).right(params.length / 2).linear_extrude(params.height)
        
        # move the text up by half the thickness and right by 2 buffers and forward by the buffer, then cut it out of the base shape
        shape -= textshape.up(params.height/2).right(params.buffer*2).forward(params.buffer)

        #  then translating the hole into the top left corner
        shape -= (
            cylinder(h=params.height * 3, r=1.5, _fn=16)
            .right(params.buffer)
            .forward(depth - params.buffer)
            .down(params.height)
        )

        return shape

DESIGNS: dict[str, BaseDesign[Any]] = {
    LoganKeyFobDesign.name: LoganKeyFobDesign(),  
    RoundedFobDesign.name: RoundedFobDesign(),
}
