"""Utilities for extracting an SVG silhouette and largest interior rectangle."""

from __future__ import annotations

import importlib
from io import BytesIO
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image, ImageDraw


def svg_to_binary_silhouette(svg_path: str, resolution: int = 2048) -> np.ndarray:
    """
    Convert SVG to binary mask of silhouette.
    
    Two approaches depending on what's installed:
    1. cairosvg (best): Renders SVG properly including fills/strokes
    2. svgpathtools (fallback): Extracts paths as polygons
    """
    try:
        # Approach 1: CairoSVG rendering + alpha extraction (best for exact silhouette).
        import cairosvg

        png_bytes = BytesIO()
        cairosvg.svg2png(
            url=str(svg_path),
            write_to=png_bytes,
            output_width=resolution,
            output_height=resolution,
        )
        png_bytes.seek(0)
        rgba = np.array(Image.open(png_bytes).convert("RGBA"))

        # Alpha marks rasterized geometry regardless of fill color.
        alpha_mask = rgba[:, :, 3] > 0
        if alpha_mask.any():
            return alpha_mask

        # Fallback for edge cases where alpha might be fully opaque.
        luminance = np.array(Image.fromarray(rgba).convert("L"))
        return luminance < 250
    
    except ImportError:
        # Approach 2: svgpathtools (lighter weight)
        svgpathtools = importlib.import_module("svgpathtools")
        svg2paths = getattr(svgpathtools, "svg2paths")

        paths, attrs = svg2paths(svg_path)
        bbox = _compute_bbox(paths)
        width, height = int(bbox[2] - bbox[0]), int(bbox[3] - bbox[1])
        
        img = Image.new('L', (width + 10, height + 10), 0)
        draw = ImageDraw.Draw(img)
        
        for path in paths:
            points = [
                (seg.start.real - bbox[0] + 5, seg.start.imag - bbox[1] + 5)
                for seg in path
            ]
            if points:
                draw.polygon(points, fill=255)

        return np.array(img) > 128


def _compute_bbox(paths):
    """Get bounding box of SVG paths."""
    bbox = [float('inf'), float('inf'), float('-inf'), float('-inf')]
    for path in paths:
        for seg in path:
            for pt in [seg.start, seg.end]:
                bbox[0] = min(bbox[0], pt.real)
                bbox[1] = min(bbox[1], pt.imag)
                bbox[2] = max(bbox[2], pt.real)
                bbox[3] = max(bbox[3], pt.imag)
    return bbox


def _parse_svg_length(value: str | None) -> float | None:
    if not value:
        return None
    match = re.match(r"^\s*([+-]?\d+(?:\.\d+)?)", value)
    if not match:
        return None
    return float(match.group(1))


def _svg_bounds(svg_path: str) -> tuple[float, float, float, float] | None:
    """Return (min_x, min_y, width, height) from viewBox/size when available."""
    try:
        root = ET.parse(svg_path).getroot()
    except ET.ParseError:
        return None

    view_box = root.attrib.get("viewBox")
    if view_box:
        parts = view_box.replace(",", " ").split()
        if len(parts) == 4:
            try:
                min_x, min_y, width, height = (float(v) for v in parts)
                if width > 0 and height > 0:
                    return min_x, min_y, width, height
            except ValueError:
                pass

    width = _parse_svg_length(root.attrib.get("width"))
    height = _parse_svg_length(root.attrib.get("height"))
    if width and height and width > 0 and height > 0:
        return 0.0, 0.0, width, height

    return None


def _largest_rectangle_in_histogram(
    heights: np.ndarray, row_index: int
) -> tuple[tuple[int, int, int, int], int]:
    """Return best rectangle ending at row_index for a histogram row."""
    max_area = 0
    best_rect = (0, 0, 1, 1)
    stack: list[int] = []

    for i in range(len(heights) + 1):
        current = int(heights[i]) if i < len(heights) else 0
        while stack and int(heights[stack[-1]]) > current:
            top = stack.pop()
            h = int(heights[top])
            left = stack[-1] + 1 if stack else 0
            right = i - 1
            area = h * (right - left + 1)
            if area > max_area:
                y2 = row_index + 1
                y1 = y2 - h
                best_rect = (left, y1, right + 1, y2)
                max_area = area
        stack.append(i)

    return best_rect, max_area


def largest_rectangle(binary_mask: np.ndarray) -> tuple[tuple[int, int, int, int], int]:
    """
    Find largest axis-aligned rectangle in binary image.
    Uses maximal rectangle algorithm (DP with histogram).
    
    Returns:
        ((x1, y1, x2, y2), area) - pixel coordinates and square pixel count
    """
    if binary_mask.ndim != 2:
        raise ValueError("largest_rectangle expects a 2D boolean mask")

    _, width = binary_mask.shape
    histogram = np.zeros(width, dtype=np.int32)
    max_area = 0
    best_rect = (0, 0, 1, 1)

    for y in range(binary_mask.shape[0]):
        histogram = np.where(binary_mask[y], histogram + 1, 0)
        row_rect, row_area = _largest_rectangle_in_histogram(histogram, y)
        if row_area > max_area:
            best_rect = row_rect
            max_area = row_area

    return best_rect, max_area


def analyze_svg(svg_path: str, resolution: int = 2048, visualize: bool = True) -> dict:
    """
    Complete analysis pipeline: SVG → silhouette → largest rectangle.
    
    Returns dict with all metrics and coordinates.
    """
    svg_path = Path(svg_path)
    
    # Step 1: Render to binary mask
    mask = svg_to_binary_silhouette(str(svg_path), resolution=resolution)
    
    # Step 2: Find largest rectangle
    rect, area = largest_rectangle(mask)
    x1, y1, x2, y2 = rect
    w, h = x2 - x1, y2 - y1
    
    results = {
        "svg_path": str(svg_path),
        "mask_shape": mask.shape,
        "silhouette_coverage": 100 * mask.sum() / mask.size,
        "rectangle": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
        "rectangle_pixels": {"width": w, "height": h},
        "rectangle_area": area,
        "aspect_ratio": w / h if h > 0 else 0,
    }

    # Optional: Visualize
    if visualize:
        viz = Image.fromarray((mask * 255).astype(np.uint8))
        draw = ImageDraw.Draw(viz)
        draw.rectangle(rect, outline=128, width=4)

        viz_path = svg_path.parent / f"{svg_path.stem}_rectangle_analysis.png"
        viz.save(viz_path)
        results["visualization"] = str(viz_path)

    return results


def pixel_to_svg_coords(
    pixel_rect: tuple[int, int, int, int],
    svg_path: str,
    render_resolution: int = 2048,
) -> dict:
    """
    Convert pixel coordinates back to actual SVG units.
    
    Returns dict with scaled coordinates ready for SolidPython.
    """
    bounds = _svg_bounds(svg_path)
    if bounds is None:
        # Last-resort fallback when explicit dimensions are unavailable.
        min_x, min_y, svg_width, svg_height = 0.0, 0.0, float(render_resolution), float(
            render_resolution
        )
    else:
        min_x, min_y, svg_width, svg_height = bounds
    
    px1, py1, px2, py2 = pixel_rect
    
    # Scale from pixel coords to SVG units
    scale_x = svg_width / render_resolution
    scale_y = svg_height / render_resolution
    
    return {
        "x": (px1 * scale_x) + min_x,
        "y": (py1 * scale_y) + min_y,
        "width": (px2 - px1) * scale_x,
        "height": (py2 - py1) * scale_y,
    }


if __name__ == "__main__":
    svg_path = Path("/home/meggleton/Projects/solid_design/svgs/utc hand logo.svg")
    results = analyze_svg(str(svg_path), resolution=2048, visualize=True)

    print(f"SVG: {results['svg_path']}")
    print(f"Silhouette: {results['mask_shape']}")
    print(f"Coverage: {results['silhouette_coverage']:.1f}%")
    print("\nLargest rectangle:")
    print(
        f"  Size: {results['rectangle_pixels']['width']}x{results['rectangle_pixels']['height']} px"
    )
    print(f"  Area: {results['rectangle_area']:,} sq px")
    print(f"  Aspect: {results['aspect_ratio']:.2f}:1")
    print(
        "  Position: "
        f"({results['rectangle']['x1']}, {results['rectangle']['y1']}) -> "
        f"({results['rectangle']['x2']}, {results['rectangle']['y2']})"
    )

    if "visualization" in results:
        print(f"\nVisualization: {results['visualization']}")

