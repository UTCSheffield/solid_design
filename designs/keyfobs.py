from __future__ import annotations

from dataclasses import dataclass

from solid2 import cube, cylinder, text
from solid2.extensions.bosl2 import BACK, BOTTOM, FRONT, LEFT, cyl, linear_sweep, squircle, text3d

from geometry import BoundingBox, measure_shape

from .common import BaseDesign, ControlSpec, compose_font_with_style


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
        text_shape, bounds = self.calculate_text_bounding_box(txt=params.name, font=effective_font)

        # End with hole uses one extra buffer width.
        new_text_length = params.length - (params.buffer * 3)
        scale_factor = new_text_length / bounds.size[0]

        text_shape = text(text=params.name, font=effective_font).translate(bounds.translation_to_zero())
        text_shape = text_shape.scale(scale_factor).linear_extrude(params.height)

        return text_shape, bounds, scale_factor

    def build_shape(self, params: KeyFobParamsLogan):
        text_shape, bounds, scale_factor = self.build_text_shape(params)
        depth = (bounds.size[1] * scale_factor) + params.buffer * 2

        shape = cube([params.length, depth, params.height])
        shape -= text_shape.up(params.height / 2).right(params.buffer * 2).forward(params.buffer)
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
        depth = (bounds.size[1] * scale_factor) + params.buffer * 2

        shape = (
            squircle([params.length, depth], 0.8)
            .forward(depth / 2)
            .right(params.length / 2)
            .linear_extrude(params.height)
        )
        shape -= text_shape.up(params.height / 2).right(params.buffer * 2).forward(params.buffer)
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
        probe = text3d(text=txt, font=font, size=10, h=1, anchor=BOTTOM + LEFT + FRONT)
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
        top_bottom_buffer = params.buffer
        depth = text_depth + top_bottom_buffer * 2

        base = linear_sweep(
            region=squircle([params.length, depth], 0.8, anchor=LEFT + FRONT),
            height=params.height,
        )
        hole = (
            cyl(h=params.height * 3, r=1.5, _fn=16)
            .position(LEFT + BACK)
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
