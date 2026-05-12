from __future__ import annotations

from typing import Any

from .common import BaseDesign, ControlSpec, compose_font_with_style
from .keyfobs import (
    KeyFobParams,
    KeyFobParamsLogan,
    LoganKeyFobDesign,
    RoundedBSOL2Design,
    RoundedFobDesign,
)
from .svg_keyfob import (
    SvgKeyfobDesign,
    SvgKeyfobParams,
)

DESIGNS: dict[str, BaseDesign[Any]] = {
    LoganKeyFobDesign.name: LoganKeyFobDesign(),
    RoundedFobDesign.name: RoundedFobDesign(),
    RoundedBSOL2Design.name: RoundedBSOL2Design(),
    SvgKeyfobDesign.name: SvgKeyfobDesign(),
}

__all__ = [
    "BaseDesign",
    "ControlSpec",
    "DESIGNS",
    "compose_font_with_style",
    "KeyFobParams",
    "KeyFobParamsLogan",
    "SvgKeyfobDesign",
    "SvgKeyfobParams",
]
