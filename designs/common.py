from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Any, Callable, Dict, Generic, Literal, TypeVar

import streamlit as st

TParams = TypeVar("TParams")

LEGACY_FONT_OPTIONS = ["Liberation Mono", "Arial", "Times New Roman"]


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
    options: list[Any] | None = None
    default_factory: Callable[[Dict[str, Any]], Any] | None = None
    validation: Callable[[Any], bool | str] | None = None


@st.cache_data(show_spinner=False)
def available_font_options() -> list[str]:
    fallback_fonts = LEGACY_FONT_OPTIONS + [
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

    # Keep compatibility aliases available even when host fonts are limited.
    font_names.update(LEGACY_FONT_OPTIONS)

    preferred_order = [
        "Arial",
        "Times New Roman",
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


@st.cache_data(show_spinner=False)
def resolve_font_match(font_family: str) -> str | None:
    if not font_family:
        return None

    try:
        result = subprocess.run(
            ["fc-match", "-f", "%{family}|%{style}", font_family],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None

    resolved = result.stdout.strip()
    if not resolved:
        return None

    family, _, style = resolved.partition("|")
    family = family.strip()
    style = style.strip()
    if not family:
        return None
    return f"{family} ({style})" if style else family


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
    field_to_key = {spec.field_name: spec.key for spec in control_specs}
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
                    font_key = field_to_key.get("font", "font")
                    selected_font = str(values.get("font", st.session_state.get(font_key, "")))
                    options = available_font_style_options(selected_font)
                elif spec.options is not None and len(spec.options) > 0:
                    options = spec.options
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
                if spec.field_name == "font":
                    resolved_font = resolve_font_match(str(value))
                    if resolved_font:
                        st.caption(f"Host font match: {resolved_font}")
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
