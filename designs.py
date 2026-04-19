from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Generic, Literal, TypeVar

import streamlit as st
from solid2 import cube, cylinder, text
from solid2.extensions.bosl2 import squircle

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
        values = render_controls(self.controls)
        return self.params_type(**values)

    def build_shape(self, params: TParams):
        raise NotImplementedError


@dataclass
class KeyFobParams:
    name: str
    length: int
    depth: int
    height: float


class KeyFobDesign(BaseDesign[KeyFobParams]):
    name = "Key Fob"
    params_type = KeyFobParams

    controls = [
        ControlSpec(
            field_name="name",
            label="What is your Name?",
            key="name",
            control_type="text_input",
            default="Streamlit",
        ),
        ControlSpec(
            field_name="length",
            label="Length",
            key="length",
            control_type="slider",
            min_value=10,
            max_value=100,
            default=30,
            default_factory=lambda values: int(round(len(values.get("name", "")) * 7.5) + 7.5),
        ),
        ControlSpec(
            field_name="depth",
            label="Depth",
            key="depth",
            control_type="slider",
            min_value=10,
            max_value=100,
            default=12,
        ),
        ControlSpec(
            field_name="height",
            label="Height",
            key="height",
            control_type="slider",
            min_value=0.5,
            max_value=10.0,
            step=0.1,
            default=1.0,
        ),
    ]

    def build_shape(self, params: KeyFobParams):
        shape = (
            squircle([params.length, params.depth], 0.8)
            .linear_extrude(params.height, center=True)
            .translate(params.length / 2, params.depth / 2, params.height / 2)
        )

        distance_from_corner = 3

        shape -= text(text=params.name).linear_extrude(params.height, center=True).translate(5, 1, params.height)
        shape -= cylinder(h=params.height * 3, r=1).translate(
            distance_from_corner,
            params.depth - distance_from_corner,
            0 - params.height,
        )

        return shape


class SquareFobDesign(KeyFobDesign):
    name = "Square Fob"

    def build_shape(self, params: KeyFobParams):
        shape = cube([params.length, params.depth, params.height])

        distance_from_corner = 3

        shape -= text(text=params.name).linear_extrude(params.height, center=True).translate(5, 1, params.height)
        shape -= cylinder(h=params.height * 3, r=1).translate(
            distance_from_corner,
            params.depth - distance_from_corner,
            0 - params.height,
        )

        return shape

DESIGNS: dict[str, BaseDesign[Any]] = {
    KeyFobDesign.name: KeyFobDesign(),
    SquareFobDesign.name: SquareFobDesign(),
}
