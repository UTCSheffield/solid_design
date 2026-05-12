from pathlib import Path
from dataclasses import dataclass
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from solid2 import import_, text
from solid2.extensions.bosl2 import (
    BOTTOM,
    FRONT,
    LEFT,
    cyl,
)

from designs import compose_font_with_style
from geometry import measure_shape


@dataclass
class SvgKeychainParams:
    name: str
    length: float
    height: float
    font: str = "Liberation Mono"
    font_style: str = "Regular"
    text_left_buffer: float = 5.0
    text_right_buffer: float = 2.5
    text_top_buffer: float = 2.5
    text_bottom_buffer: float = 2.5
    text_x_offset: float = 0.0
    text_y_offset: float = 0.0
    hole_radius: float = 1.5
    hole_margin: float = 2.5



class MockDesign:
    def __init__(self, svg_source: str | Path = "svgs/utc hand logo.svg") -> None:
        self.svg_source = svg_source

    def _resolve_svg_path(self, svg_source: str | Path | None = None) -> Path:
        source = Path(svg_source if svg_source is not None else self.svg_source)
        if source.is_absolute():
            resolved = source
        else:
            resolved = Path(__file__).resolve().parent.parent / source

        if not resolved.exists():
            raise FileNotFoundError(f"SVG file not found: {resolved}")
        return resolved

    def load_svg_shape(self, svg_source: str | Path | None = None):
        svg_path = self._resolve_svg_path(svg_source)
        return import_(file=str(svg_path))

    def calculate_svg_bounding_box(self, svg_source: str | Path | None = None):
        probe = self.load_svg_shape(svg_source).linear_extrude(1)
        return measure_shape(probe).bounds

    def build_svg_shape(self, params: SvgKeychainParams, svg_source: str | Path | None = None):
        measured_logo = measure_shape(
            self.load_svg_shape(svg_source).linear_extrude(params.height)
        ).resize_to(x=params.length)

        logo_shape = measured_logo.position(BOTTOM + LEFT + FRONT)
        logo_bounds = measured_logo.bounds

        return logo_shape, logo_bounds

    def build_text_cutout(self, params: SvgKeychainParams, logo_bounds):
        logo_width, logo_depth, _ = logo_bounds.size
        left_text_buffer = max(0.0, params.text_left_buffer)
        right_text_buffer = max(0.0, params.text_right_buffer)
        top_text_buffer = max(0.0, params.text_top_buffer)
        bottom_text_buffer = max(0.0, params.text_bottom_buffer)
        text_width = max(1.0, logo_width - left_text_buffer - right_text_buffer)
        text_height = max(1.0, logo_depth - top_text_buffer - bottom_text_buffer)

        effective_font = compose_font_with_style(params.font, params.font_style)
        measured_text = measure_shape(
            text(text=params.name, font=effective_font).linear_extrude(params.height)
        ).resize_to(x=text_width)

        if measured_text.bounds.size[1] > text_height:
            measured_text = measured_text.resize_to(y=text_height)

        remaining_x = text_width - measured_text.bounds.size[0]
        remaining_y = text_height - measured_text.bounds.size[1]
        offset_x = left_text_buffer + max(0.0, remaining_x / 2) + params.text_x_offset
        offset_y = bottom_text_buffer + max(0.0, remaining_y / 2) + params.text_y_offset

        max_offset_x = logo_width - right_text_buffer - measured_text.bounds.size[0]
        max_offset_y = logo_depth - top_text_buffer - measured_text.bounds.size[1]
        offset_x = min(max(left_text_buffer, offset_x), max(left_text_buffer, max_offset_x))
        offset_y = min(max(bottom_text_buffer, offset_y), max(bottom_text_buffer, max_offset_y))

        text_shape = measured_text.position(BOTTOM + LEFT + FRONT)
        return text_shape.right(offset_x).fwd(offset_y)

    def build_hole(self, params: SvgKeychainParams, logo_bounds):
        min_x, min_y, _ = logo_bounds.min_corner
        max_x, max_y, _ = logo_bounds.max_corner
        hole_radius = max(0.2, params.hole_radius)
        hole_margin = max(params.hole_margin, hole_radius)
        hole_x = (min_x + max_x) / 2
        hole_y = (min_y + max_y) / 2

        hole_x = min(max_x - hole_radius, max(min_x + hole_radius, hole_x))
        hole_y = min(max_y - hole_radius, max(min_y + hole_radius, hole_y))

        return (
            cyl(h=params.height * 3, r=hole_radius, _fn=24)
            .right(hole_x)
            .forward(hole_y)
            .down(params.height)
        )

    def build_shape(self, params: SvgKeychainParams, svg_source: str | Path | None = None):
        logo_shape, logo_bounds = self.build_svg_shape(params, svg_source=svg_source)
        text_cutout = self.build_text_cutout(params, logo_bounds)
        hole = self.build_hole(params, logo_bounds)

        return logo_shape - hole - text_cutout


def main() -> None:
    shape = MockDesign(svg_source="svgs/utc hand logo.svg").build_shape(
        SvgKeychainParams(length=50, height=3, name="Matthew", font="Liberation Mono")
        # SvgKeychainParams(length=50, height=3, name="Martyn", font="Times New Roman")
    )
    shape.save_as_stl()


if __name__ == "__main__":
    main()
