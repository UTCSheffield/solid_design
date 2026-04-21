from __future__ import annotations

from dataclasses import dataclass
from math import inf
from pathlib import Path
from struct import Struct, error as StructError
from tempfile import TemporaryDirectory
from typing import Any


_BINARY_FACET = Struct("<12fH")


@dataclass(frozen=True)
class BoundingBox:
    min_corner: tuple[float, float, float]
    max_corner: tuple[float, float, float]

    @property
    def size(self) -> tuple[float, float, float]:
        return tuple(
            upper - lower for lower, upper in zip(self.min_corner, self.max_corner, strict=True)
        )

    @property
    def center(self) -> tuple[float, float, float]:
        return tuple(
            (lower + upper) / 2 for lower, upper in zip(self.min_corner, self.max_corner, strict=True)
        )

    def translation_to_center(
        self,
        axes: tuple[bool, bool, bool] = (True, True, True),
    ) -> tuple[float, float, float]:
        return tuple(
            -coordinate if axis_enabled else 0.0
            for axis_enabled, coordinate in zip(axes, self.center, strict=True)
        )


def calculate_shape_bounding_box(
    shape: Any,
    *,
    stl_path: str | Path | None = None,
) -> BoundingBox:
    if stl_path is not None:
        target_path = Path(stl_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shape.save_as_stl(str(target_path))
        return measure_stl_bounding_box(target_path)

    with TemporaryDirectory() as temp_dir:
        target_path = Path(temp_dir) / "shape_bounds.stl"
        shape.save_as_stl(str(target_path))
        return measure_stl_bounding_box(target_path)


def measure_stl_bounding_box(stl_path: str | Path) -> BoundingBox:
    path = Path(stl_path)
    if not path.exists():
        raise FileNotFoundError(f"STL file not found: {path}")

    if _is_binary_stl(path):
        return _measure_binary_stl(path)
    return _measure_ascii_stl(path)


def center_shape_on_origin(
    shape: Any,
    axes: tuple[bool, bool, bool] = (True, True, True),
) -> tuple[Any, BoundingBox]:
    bounds = calculate_shape_bounding_box(shape)
    return shape.translate(*bounds.translation_to_center(axes)), bounds


def _is_binary_stl(path: Path) -> bool:
    if path.stat().st_size < 84:
        return False

    with path.open("rb") as stl_file:
        header = stl_file.read(84)

    triangle_count = int.from_bytes(header[80:84], byteorder="little", signed=False)
    expected_size = 84 + triangle_count * _BINARY_FACET.size
    return path.stat().st_size == expected_size


def _measure_binary_stl(path: Path) -> BoundingBox:
    mins = [inf, inf, inf]
    maxs = [-inf, -inf, -inf]

    with path.open("rb") as stl_file:
        stl_file.read(84)
        while chunk := stl_file.read(_BINARY_FACET.size):
            if len(chunk) != _BINARY_FACET.size:
                raise ValueError(f"Invalid binary STL facet in {path}")

            try:
                values = _BINARY_FACET.unpack(chunk)
            except StructError as exc:
                raise ValueError(f"Could not parse binary STL facet in {path}") from exc

            for start in (3, 6, 9):
                _update_bounds(values[start : start + 3], mins, maxs)

    return _build_bounds(path, mins, maxs)


def _measure_ascii_stl(path: Path) -> BoundingBox:
    mins = [inf, inf, inf]
    maxs = [-inf, -inf, -inf]

    with path.open("r", encoding="utf-8", errors="ignore") as stl_file:
        for raw_line in stl_file:
            stripped = raw_line.strip()
            if not stripped.startswith("vertex "):
                continue

            _, x_value, y_value, z_value = stripped.split(maxsplit=3)
            _update_bounds((float(x_value), float(y_value), float(z_value)), mins, maxs)

    return _build_bounds(path, mins, maxs)


def _update_bounds(
    point: tuple[float, float, float] | list[float],
    mins: list[float],
    maxs: list[float],
) -> None:
    for axis, value in enumerate(point):
        mins[axis] = min(mins[axis], value)
        maxs[axis] = max(maxs[axis], value)


def _build_bounds(path: Path, mins: list[float], maxs: list[float]) -> BoundingBox:
    if any(value == inf for value in mins):
        raise ValueError(f"No vertices found in STL file: {path}")

    return BoundingBox(
        min_corner=tuple(float(value) for value in mins),
        max_corner=tuple(float(value) for value in maxs),
    )