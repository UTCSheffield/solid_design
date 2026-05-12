from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image
from solid2 import linear_extrude, projection, square

from designs.svg_keyfob import SvgKeyfobDesign, SvgKeyfobParams
from svg_tools import analyze_svg, svg_to_binary_silhouette


def _mask_bbox(mask: np.ndarray) -> tuple[int, int, int, int] | None:
    ys, xs = np.where(mask)
    if xs.size == 0 or ys.size == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def _fit_mask_to_bbox(mask: np.ndarray, src_bbox: tuple[int, int, int, int], dst_bbox: tuple[int, int, int, int]) -> np.ndarray:
    sx1, sy1, sx2, sy2 = src_bbox
    dx1, dy1, dx2, dy2 = dst_bbox

    src_crop = mask[sy1:sy2, sx1:sx2]
    src_img = Image.fromarray((src_crop.astype(np.uint8) * 255), mode="L")
    resized = src_img.resize((dx2 - dx1, dy2 - dy1), resample=Image.Resampling.NEAREST)

    out = np.zeros_like(mask, dtype=bool)
    out[dy1:dy2, dx1:dx2] = np.array(resized) > 127
    return out


def _apply_orientation(mask: np.ndarray, orientation: str) -> np.ndarray:
    if orientation == "flipud":
        return np.flipud(mask)
    if orientation == "fliplr":
        return np.fliplr(mask)
    if orientation == "flipud_fliplr":
        return np.flipud(np.fliplr(mask))
    return mask


def _save_mask_png(mask: np.ndarray, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray((mask.astype(np.uint8) * 255), mode="L").save(out_path)


def _save_overlay(expected: np.ndarray, projected: np.ndarray, out_path: Path) -> None:
    # Green: overlap, Red: expected-only, Blue: projected-only
    overlap = expected & projected
    expected_only = expected & ~projected
    projected_only = projected & ~expected

    rgb = np.zeros((expected.shape[0], expected.shape[1], 3), dtype=np.uint8)
    rgb[..., 1] = overlap.astype(np.uint8) * 255
    rgb[..., 0] = expected_only.astype(np.uint8) * 255
    rgb[..., 2] = projected_only.astype(np.uint8) * 255

    Image.fromarray(rgb, mode="RGB").save(out_path)


def _iou(a: np.ndarray, b: np.ndarray) -> float:
    intersection = np.count_nonzero(a & b)
    union = np.count_nonzero(a | b)
    return (intersection / union) if union else 1.0


def _render_projected_mask(shape_3d, out_prefix: Path, resolution: int) -> np.ndarray:
    out_prefix.parent.mkdir(parents=True, exist_ok=True)
    scad_path = out_prefix.with_suffix(".scad")
    svg_path = out_prefix.with_suffix(".svg")
    png_path = out_prefix.with_suffix(".png")

    shape_2d = projection(cut=True)(shape_3d)
    shape_2d.save_as_scad(str(scad_path))
    subprocess.run(["openscad", "-o", str(svg_path), str(scad_path)], check=True)

    import cairosvg

    cairosvg.svg2png(
        url=str(svg_path),
        write_to=str(png_path),
        output_width=resolution,
        output_height=resolution,
    )
    rgba = np.array(Image.open(png_path).convert("RGBA"))
    return rgba[:, :, 3] > 127


def _orient_and_align(
    aligned_projected_mask: np.ndarray,
    bitmap_bbox: tuple[int, int, int, int],
    expected_mask: np.ndarray,
) -> tuple[str, np.ndarray, float]:
    candidates: dict[str, np.ndarray] = {
        "none": aligned_projected_mask,
        "flipud": np.flipud(aligned_projected_mask),
        "fliplr": np.fliplr(aligned_projected_mask),
        "flipud_fliplr": np.flipud(np.fliplr(aligned_projected_mask)),
    }
    _ = bitmap_bbox
    best_orientation = "none"
    best_mask = aligned_projected_mask
    best_iou = -1.0
    for orientation_name, candidate in candidates.items():
        score = _iou(expected_mask, candidate)
        if score > best_iou:
            best_iou = score
            best_orientation = orientation_name
            best_mask = candidate
    return best_orientation, best_mask, best_iou


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare bitmap rectangle cutout vs SolidPython projected cutout")
    parser.add_argument("--svg", default="svgs/utc hand logo.svg", help="Path to input SVG")
    parser.add_argument("--name", default="Matthew", help="Text (unused, but kept for consistent design params)")
    parser.add_argument("--length", type=float, default=50.0, help="Solid target X size")
    parser.add_argument("--height", type=float, default=3.0, help="Solid thickness")
    parser.add_argument("--buffer", type=float, default=0.0, help="Rectangle inset buffer for this test")
    parser.add_argument("--resolution", type=int, default=1024, help="Comparison raster resolution")
    parser.add_argument("--out-dir", default="artifacts/rectangle_compare", help="Output directory")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    design = SvgKeyfobDesign()
    params = SvgKeyfobParams(
        name=args.name,
        length=args.length,
        height=args.height,
        svg_path=args.svg,
        buffer=args.buffer,
        hole_radius=1.5,
    )

    # Bitmap-space expected masks.
    analysis = analyze_svg(args.svg, resolution=args.resolution, visualize=False)
    rect = analysis["rectangle"]
    bitmap_mask = svg_to_binary_silhouette(args.svg, resolution=args.resolution)

    expected_cutout = bitmap_mask.copy()
    expected_cutout[rect["y1"]:rect["y2"], rect["x1"]:rect["x2"]] = False
    expected_rect_only = bitmap_mask & ~expected_cutout

    # Solid-space rectangle projected back to 2D.
    svg_shape, svg_bounds = design._build_svg_shape(params)
    fit_min_x, fit_max_x, fit_min_y, fit_max_y = design._text_fit_box(params, svg_bounds)
    rect_w = max(0.1, fit_max_x - fit_min_x)
    rect_h = max(0.1, fit_max_y - fit_min_y)

    rect_2d = square([rect_w, rect_h]).translate([fit_min_x, fit_min_y, 0])
    rect_3d = linear_extrude(height=args.height + 2.0)(rect_2d).translate([0, 0, -1.0])
    cut_3d = svg_shape - rect_3d

    projected_silhouette_mask = _render_projected_mask(
        svg_shape, out_dir / "projected_silhouette", args.resolution
    )
    projected_boolean_cutout_mask = _render_projected_mask(
        cut_3d, out_dir / "projected_boolean_cutout", args.resolution
    )

    # Align projected raster to bitmap bbox so both share the same image frame.
    bitmap_bbox = _mask_bbox(bitmap_mask)
    projected_sil_bbox = _mask_bbox(projected_silhouette_mask)
    if bitmap_bbox is None or projected_sil_bbox is None:
        raise RuntimeError("Could not compute non-empty mask bbox for comparison")

    aligned_silhouette_base = _fit_mask_to_bbox(projected_silhouette_mask, projected_sil_bbox, bitmap_bbox)
    aligned_boolean_cutout_base = _fit_mask_to_bbox(
        projected_boolean_cutout_mask, projected_sil_bbox, bitmap_bbox
    )
    # Build rectangle mask directly in the aligned silhouette frame from normalized fit box.
    svg_min_x, svg_min_y, _ = svg_bounds.min_corner
    svg_w, svg_h, _ = svg_bounds.size
    norm_min_x = (fit_min_x - svg_min_x) / max(1e-6, svg_w)
    norm_max_x = (fit_max_x - svg_min_x) / max(1e-6, svg_w)
    norm_min_y = (fit_min_y - svg_min_y) / max(1e-6, svg_h)
    norm_max_y = (fit_max_y - svg_min_y) / max(1e-6, svg_h)

    bx1, by1, bx2, by2 = bitmap_bbox
    bw = max(1, bx2 - bx1)
    bh = max(1, by2 - by1)

    rx1 = int(round(bx1 + norm_min_x * bw))
    rx2 = int(round(bx1 + norm_max_x * bw))
    ry1 = int(round(by1 + norm_min_y * bh))
    ry2 = int(round(by1 + norm_max_y * bh))

    rx1 = max(0, min(args.resolution, rx1))
    rx2 = max(0, min(args.resolution, rx2))
    ry1 = max(0, min(args.resolution, ry1))
    ry2 = max(0, min(args.resolution, ry2))

    aligned_rect_base = np.zeros_like(bitmap_mask, dtype=bool)
    if rx2 > rx1 and ry2 > ry1:
        aligned_rect_base[ry1:ry2, rx1:rx2] = True

    # Find best orientation from silhouette first (baseline transform check).
    silhouette_orientation, aligned_silhouette, silhouette_iou = _orient_and_align(
        aligned_silhouette_base, bitmap_bbox, bitmap_mask
    )

    # Apply the same orientation to cutout so rectangle comparison is apples-to-apples.
    aligned_rect = _apply_orientation(aligned_rect_base, silhouette_orientation)
    aligned_boolean_cutout = _apply_orientation(
        aligned_boolean_cutout_base, silhouette_orientation
    )

    # Derive cutout masks in raster space to avoid SVG fill-rule artifacts.
    aligned_cutout = aligned_silhouette & ~aligned_rect

    # Rectangle-only removal is silhouette minus cutout.
    projected_rect_only = aligned_silhouette & aligned_rect

    # Persist debug artifacts.
    expected_sil_png = out_dir / "expected_bitmap_silhouette.png"
    aligned_sil_png = out_dir / "aligned_projected_silhouette.png"
    sil_overlay_png = out_dir / "silhouette_overlay.png"

    expected_cut_png = out_dir / "expected_bitmap_cutout.png"
    aligned_cut_png = out_dir / "aligned_projected_cutout.png"
    cut_overlay_png = out_dir / "comparison_overlay.png"

    expected_rect_png = out_dir / "expected_bitmap_rectangle_only.png"
    aligned_rect_png = out_dir / "aligned_projected_rectangle_only.png"
    rect_overlay_png = out_dir / "rectangle_only_overlay.png"

    aligned_boolean_cut_png = out_dir / "aligned_projected_boolean_cutout.png"
    boolean_overlay_png = out_dir / "boolean_cutout_overlay.png"

    _save_mask_png(bitmap_mask, expected_sil_png)
    _save_mask_png(aligned_silhouette, aligned_sil_png)
    _save_overlay(bitmap_mask, aligned_silhouette, sil_overlay_png)

    _save_mask_png(expected_cutout, expected_cut_png)
    _save_mask_png(aligned_cutout, aligned_cut_png)
    _save_overlay(expected_cutout, aligned_cutout, cut_overlay_png)

    _save_mask_png(expected_rect_only, expected_rect_png)
    _save_mask_png(projected_rect_only, aligned_rect_png)
    _save_overlay(expected_rect_only, projected_rect_only, rect_overlay_png)

    _save_mask_png(aligned_boolean_cutout, aligned_boolean_cut_png)
    _save_overlay(expected_cutout, aligned_boolean_cutout, boolean_overlay_png)

    overlap = np.count_nonzero(expected_cutout & aligned_cutout)
    expected_area = np.count_nonzero(expected_cutout)
    projected_area = np.count_nonzero(aligned_cutout)
    union = np.count_nonzero(expected_cutout | aligned_cutout)
    iou = (overlap / union) if union else 1.0

    rect_overlap = np.count_nonzero(expected_rect_only & projected_rect_only)
    rect_expected_area = np.count_nonzero(expected_rect_only)
    rect_projected_area = np.count_nonzero(projected_rect_only)
    rect_union = np.count_nonzero(expected_rect_only | projected_rect_only)
    rect_iou = (rect_overlap / rect_union) if rect_union else 1.0

    boolean_overlap = np.count_nonzero(expected_cutout & aligned_boolean_cutout)
    boolean_projected_area = np.count_nonzero(aligned_boolean_cutout)
    boolean_union = np.count_nonzero(expected_cutout | aligned_boolean_cutout)
    boolean_iou = (boolean_overlap / boolean_union) if boolean_union else 1.0

    print("== Silhouette Baseline ==")
    print(f"IoU:            {silhouette_iou:.6f}")
    print(f"Orientation:    {silhouette_orientation}")
    print(f"Wrote: {expected_sil_png}")
    print(f"Wrote: {aligned_sil_png}")
    print(f"Wrote: {sil_overlay_png}")
    print()
    print("== Cutout Compare ==")
    print(f"Expected area:  {expected_area}")
    print(f"Projected area: {projected_area}")
    print(f"Overlap area:   {overlap}")
    print(f"IoU:            {iou:.6f}")
    print(f"Wrote: {expected_cut_png}")
    print(f"Wrote: {aligned_cut_png}")
    print(f"Wrote: {cut_overlay_png}")
    print()
    print("== Actual Boolean Cutout Compare ==")
    print(f"Expected area:  {expected_area}")
    print(f"Projected area: {boolean_projected_area}")
    print(f"Overlap area:   {boolean_overlap}")
    print(f"IoU:            {boolean_iou:.6f}")
    print(f"Wrote: {aligned_boolean_cut_png}")
    print(f"Wrote: {boolean_overlay_png}")
    print()
    print("== Rectangle-Only Compare ==")
    print(f"Expected area:  {rect_expected_area}")
    print(f"Projected area: {rect_projected_area}")
    print(f"Overlap area:   {rect_overlap}")
    print(f"IoU:            {rect_iou:.6f}")
    print(f"Wrote: {expected_rect_png}")
    print(f"Wrote: {aligned_rect_png}")
    print(f"Wrote: {rect_overlay_png}")


if __name__ == "__main__":
    main()
