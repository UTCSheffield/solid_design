from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import subprocess
import tempfile

import cairosvg
import numpy as np
from PIL import Image
from solid2 import import_, linear_extrude, offset, projection, square, text
from solid2.extensions.bosl2 import BOTTOM, LEFT, cyl

from geometry import BoundingBox, measure_shape
from svg_tools import largest_rectangle

from .common import BaseDesign, ControlSpec, compose_font_with_style


def available_svg_paths() -> list[str]:
    svg_dir = Path(__file__).resolve().parent.parent / "svgs"
    if not svg_dir.exists():
        return ["svgs/utc hand logo.svg"]

    options = sorted(
        f"svgs/{path.name}"
        for path in svg_dir.iterdir()
        if path.is_file() and path.suffix.lower() == ".svg"
    )
    return options or ["svgs/utc hand logo.svg"]


@dataclass
class SvgKeyfobParams:
    name: str
    length: float
    height: float
    svg_path: str
    font: str = "Liberation Mono"
    font_style: str = "Regular"
    buffer: float = 2.0
    text_rotate_90: str = "Off"
    hole_radius: float = 1.5


class SvgKeyfobDesign(BaseDesign[SvgKeyfobParams]):
    name = "SVG Keyfob"
    params_type = SvgKeyfobParams

    def __init__(self) -> None:
        self._cached_text_fit_key: tuple[str, str, str, float, float, float, int] | None = None
        self._cached_text_fit_shape: object | None = None
        self._rectangle_box_cache: dict[str, tuple[float, float, float, float]] = {}
        self._text_fit_version = 23  # Bump this to invalidate cache on algorithm changes

    controls = [
        ControlSpec(
            field_name="name",
            label="Name Cutout",
            key="svg_name",
            control_type="text_input",
            default="UTC OLP",
            validation=lambda x: len(x.strip()) > 0 or "Name cannot be empty",
        ),
        ControlSpec(
            field_name="svg_path",
            label="SVG Path",
            key="svg_path",
            control_type="dropdown",
            default="svgs/utc hand logo.svg",
            options=available_svg_paths(),
        ),
        ControlSpec(
            field_name="font",
            label="Font",
            key="svg_font",
            control_type="dropdown",
            default="Liberation Mono",
        ),
        ControlSpec(
            field_name="font_style",
            label="Font Style",
            key="svg_font_style",
            control_type="dropdown",
            default="Regular",
        ),
        ControlSpec(
            field_name="length",
            label="SVG Length",
            key="svg_length",
            control_type="slider",
            min_value=20.0,
            max_value=120.0,
            step=0.5,
            default=50.0,
        ),
        ControlSpec(
            field_name="height",
            label="Thickness",
            key="svg_height",
            control_type="slider",
            min_value=1.0,
            max_value=10.0,
            step=0.1,
            default=3.0,
        ),
        ControlSpec(
            field_name="buffer",
            label="Buffer (mm)",
            key="svg_buffer",
            control_type="slider",
            min_value=0.0,
            max_value=20.0,
            step=0.1,
            default=2.0,
        ),
        ControlSpec(
            field_name="text_rotate_90",
            label="Text Rotate 90",
            key="svg_text_rotate_90",
            control_type="dropdown",
            default="Off",
            options=["Off", "On"],
        ),
        ControlSpec(
            field_name="hole_radius",
            label="Hole Radius",
            key="svg_hole_radius",
            control_type="slider",
            min_value=0.5,
            max_value=6.0,
            step=0.1,
            default=1.5,
        )
    ]

    @staticmethod
    def _resolve_svg_path(svg_path: str) -> Path:
        source = Path(svg_path)
        resolved = source if source.is_absolute() else Path(__file__).resolve().parent.parent / source
        if not resolved.exists():
            raise FileNotFoundError(f"SVG file not found: {resolved}")
        return resolved

    def _load_svg_shape(self, svg_path: str):
        return import_(file=str(self._resolve_svg_path(svg_path)))

    def _build_svg_shape(self, params: SvgKeyfobParams):
        svg_3d = self._load_svg_shape(params.svg_path).linear_extrude(params.height)
        svg_bounds_raw = measure_shape(svg_3d).bounds
        
        # Calculate uniform scale to fit length in X, preserving aspect ratio
        raw_x_size = svg_bounds_raw.size[0]
        raw_y_size = svg_bounds_raw.size[1]
        scale_factor = params.length / raw_x_size
        scaled_y_size = raw_y_size * scale_factor
        
        # Resize with both X and Y to preserve aspect ratio
        measured_svg = measure_shape(svg_3d).resize_to(x=params.length, y=scaled_y_size)
        positioned_svg = measured_svg.position(BOTTOM + LEFT)
        positioned_bounds = measure_shape(positioned_svg).bounds
        return positioned_svg, positioned_bounds


    def _base_fit_cache_key(self, params: SvgKeyfobParams) -> tuple[str, str, str, float, float, float, int]:
        return (
            params.name.strip(),
            params.svg_path,
            compose_font_with_style(params.font, params.font_style),
            params.text_rotate_90,
            params.buffer,
            params.hole_radius,
            params.length,
            self._text_fit_version,
        )

    def _rectangle_normalized_box(self, params: SvgKeyfobParams) -> tuple[float, float, float, float]:
        svg_file = str(self._resolve_svg_path(params.svg_path))
        cached = self._rectangle_box_cache.get(svg_file)
        if cached is not None:
            return cached

        # Build a mask from the imported geometry projection so rectangle extraction
        # uses the exact same coordinate frame as SolidPython geometry.
        proj_shape = projection(cut=True)(self._load_svg_shape(params.svg_path).linear_extrude(1))
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            scad_path = tmp / "shape.scad"
            svg_path = tmp / "shape.svg"

            proj_shape.save_as_scad(str(scad_path))
            subprocess.run(["openscad", "-o", str(svg_path), str(scad_path)], check=True)

            png_bytes = BytesIO()
            cairosvg.svg2png(
                url=str(svg_path),
                write_to=png_bytes,
                output_width=2048,
                output_height=2048,
            )
            png_bytes.seek(0)
            rgba = np.array(Image.open(png_bytes).convert("RGBA"))

        mask = rgba[:, :, 3] > 127
        rect, _ = largest_rectangle(mask)
        ys, xs = np.where(mask)
        if xs.size == 0 or ys.size == 0:
            norm_min_x, norm_max_x, norm_min_y, norm_max_y = 0.0, 1.0, 0.0, 1.0
        else:
            sil_min_x = int(xs.min())
            sil_max_x = int(xs.max()) + 1
            sil_min_y = int(ys.min())
            sil_max_y = int(ys.max()) + 1
            sil_w = max(1, sil_max_x - sil_min_x)
            sil_h = max(1, sil_max_y - sil_min_y)

            norm_min_x = (rect[0] - sil_min_x) / sil_w
            norm_max_x = (rect[2] - sil_min_x) / sil_w
            norm_min_y = (rect[1] - sil_min_y) / sil_h
            norm_max_y = (rect[3] - sil_min_y) / sil_h

            norm_min_x = min(1.0, max(0.0, norm_min_x))
            norm_max_x = min(1.0, max(norm_min_x, norm_max_x))
            norm_min_y = min(1.0, max(0.0, norm_min_y))
            norm_max_y = min(1.0, max(norm_min_y, norm_max_y))

        self._rectangle_box_cache[svg_file] = (norm_min_x, norm_max_x, norm_min_y, norm_max_y)
        return norm_min_x, norm_max_x, norm_min_y, norm_max_y

    def _text_fit_box(
        self,
        params: SvgKeyfobParams,
        svg_bounds: BoundingBox,
    ) -> tuple[float, float, float, float]:
        """Return text-fit box from detected rectangle position + buffer."""
        svg_min_x, svg_min_y, _ = svg_bounds.min_corner
        svg_width, svg_depth, _ = svg_bounds.size
        norm_min_x, norm_max_x, norm_min_y, norm_max_y = self._rectangle_normalized_box(params)
        buffer = max(0.0, params.buffer)

        # The extracted rectangle uses image-space Y (downward); model Y grows upward.
        model_norm_min_y = 1.0 - norm_max_y
        model_norm_max_y = 1.0 - norm_min_y

        raw_min_x = svg_min_x + (svg_width * norm_min_x)
        raw_max_x = svg_min_x + (svg_width * norm_max_x)
        raw_min_y = svg_min_y + (svg_depth * model_norm_min_y)
        raw_max_y = svg_min_y + (svg_depth * model_norm_max_y)

        min_x = max(svg_min_x, raw_min_x + buffer)
        max_x = min(svg_min_x + svg_width, raw_max_x - buffer)
        min_y = max(svg_min_y, raw_min_y + buffer)
        max_y = min(svg_min_y + svg_depth, raw_max_y - buffer)

        # Ensure the fit box always remains usable when buffer is large.
        if max_x - min_x < 1.0:
            center_x = (raw_min_x + raw_max_x) / 2.0
            min_x = max(svg_min_x, center_x - 0.5)
            max_x = min(svg_min_x + svg_width, center_x + 0.5)
        if max_y - min_y < 1.0:
            center_y = (raw_min_y + raw_max_y) / 2.0
            min_y = max(svg_min_y, center_y - 0.5)
            max_y = min(svg_min_y + svg_depth, center_y + 0.5)
        return min_x, max_x, min_y, max_y

    @staticmethod
    def _text_engrave_depth(params: SvgKeyfobParams) -> float:
        return min(max(0.35, params.height * 0.35), max(0.35, params.height - 0.2))

    def _build_text_cutout(self, params: SvgKeyfobParams, svg_bounds: BoundingBox):
        min_x, max_x, min_y, max_y = self._text_fit_box(params, svg_bounds)
        box_width = max(0.0, max_x - min_x)
        box_depth = max(0.0, max_y - min_y)
        engrave_depth = self._text_engrave_depth(params)

        effective_font = compose_font_with_style(params.font, params.font_style)
        
        # Create base text and measure it.
        base_text = text(text=params.name, font=effective_font)
        if params.text_rotate_90 == "On":
            base_text = base_text.rotate([0, 0, 90])
        bounds = measure_shape(base_text.linear_extrude(1)).bounds
        
        # Scale to fit box dimensions.
        base_width = bounds.size[0]
        base_depth = bounds.size[1]
        if base_width <= 0 or base_depth <= 0:
            return base_text.linear_extrude(engrave_depth)
        
        # Uniformly scale text to the full buffered fit box.
        fit_scale = min(box_width / base_width, box_depth / base_depth)
        fit_scale = max(0.01, min(10.0, fit_scale))
        
        # Create final text: translate to origin, scale uniformly, extrude to engrave depth.
        text_shape = base_text.translate(bounds.translation_to_zero())
        text_shape = text_shape.scale([fit_scale, fit_scale, 1.0]).linear_extrude(engrave_depth)
        
        # Center horizontally and vertically in the fit box, positioned at top surface for engraving.
        measured = measure_shape(text_shape).bounds
        offset_x = min_x + (box_width - measured.size[0]) / 2
        offset_y = min_y + (box_depth - measured.size[1]) / 2
        
        # Position text: centered horizontally/vertically, at top surface (z=height - engrave_depth).
        return text_shape.right(offset_x).forward(offset_y).up(params.height - engrave_depth)

    def _solve_base_text_cutout(
        self,
        params: SvgKeyfobParams,
        svg_shape: object,
        svg_bounds: BoundingBox,
        fit_shape: object,
    ):
        # Use rectangle-analysis-based fit; no validation checks to keep it fast.
        _ = svg_shape
        _ = fit_shape
        return self._build_text_cutout(params, svg_bounds)

    def _resolve_text_cutout(
        self,
        params: SvgKeyfobParams,
        svg_shape: object,
        svg_bounds: BoundingBox,
        fit_shape: object,
    ):
        cache_key = self._base_fit_cache_key(params)
        if self._cached_text_fit_key != cache_key or self._cached_text_fit_shape is None:
            self._cached_text_fit_shape = self._solve_base_text_cutout(
                params,
                svg_shape,
                svg_bounds,
                fit_shape,
            )
            self._cached_text_fit_key = cache_key

        return self._cached_text_fit_shape

    def _build_hole(self, params: SvgKeyfobParams, svg_shape: object, svg_bounds: BoundingBox):
        _ = svg_shape
        hole_radius = max(0.2, params.hole_radius)

        # Get silhouette bounds and fit box
        min_x, min_y, _ = svg_bounds.min_corner
        max_x, max_y, _ = svg_bounds.max_corner
        fit_min_x, fit_max_x, fit_min_y, fit_max_y = self._text_fit_box(params, svg_bounds)

        # Find available space: above vs below the fit box
        space_above_min = fit_max_y
        space_above_max = max_y
        space_above_size = space_above_max - space_above_min

        space_below_min = min_y
        space_below_max = fit_min_y
        space_below_size = space_below_max - space_below_min

        # Choose the region with more space
        if space_above_size >= space_below_size:
            # Place hole in upper space, as close to top edge as possible
            hole_y = max_y - params.buffer
        else:
            # Place hole in lower space, as close to bottom edge as possible
            hole_y = min_y + params.buffer

        # Center hole horizontally between left and right constraints (buffer from each edge)
        hole_x = (min_x + params.buffer + max_x - params.buffer) / 2

        # Cylinder extends from z=-2 to z=height+2 to ensure full through-cut.
        hole_height = params.height + 4
        return (
            cyl(h=hole_height, r=hole_radius, _fn=24)
            .right(hole_x)
            .forward(hole_y)
            .up(1.5)
        )

    def _build_fit_box_overlay(self, params: SvgKeyfobParams, svg_bounds: BoundingBox):
        min_x, max_x, min_y, max_y = self._text_fit_box(params, svg_bounds)
        box_w = max(0.0, max_x - min_x)
        box_h = max(0.0, max_y - min_y)
        if box_w <= 0.0 or box_h <= 0.0:
            return None

        ring_thickness = min(0.8, max(0.4, min(box_w, box_h) * 0.06))
        overlay_h = min(0.8, max(0.3, params.height * 0.25))

        outer = square([box_w, box_h]).translate([min_x, min_y, 0])
        inner_w = box_w - (2.0 * ring_thickness)
        inner_h = box_h - (2.0 * ring_thickness)
        if inner_w > 0.0 and inner_h > 0.0:
            inner = square([inner_w, inner_h]).translate(
                [min_x + ring_thickness, min_y + ring_thickness, 0]
            )
            ring_2d = outer - inner
        else:
            ring_2d = outer

        return linear_extrude(height=overlay_h)(ring_2d).up(params.height - overlay_h)

    def build_shape(self, params: SvgKeyfobParams):
        svg_shape, svg_bounds = self._build_svg_shape(params)
        text_cutout = self._resolve_text_cutout(params, svg_shape, svg_bounds, None)
        hole = self._build_hole(params, svg_shape, svg_bounds)
        result = svg_shape - hole - text_cutout

        return result

