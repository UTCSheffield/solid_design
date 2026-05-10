from __future__ import annotations

import ast
from dataclasses import dataclass
from math import inf
from pathlib import Path
from struct import Struct, error as StructError
from tempfile import TemporaryDirectory
from typing import Any

from solid2 import import_stl
from solid2.extensions.bosl2 import CENTER, UP, attachable


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

    def translation_to_zero(self) -> tuple[float, float, float]:
        return tuple(-coordinate for coordinate in self.min_corner)

    def anchor(self, direction: Any) -> tuple[float, float, float]:
        direction_vector = _coerce_direction_vector(direction)
        return tuple(
            center + axis * size / 2
            for center, axis, size in zip(self.center, direction_vector, self.size, strict=True)
        )

    def translation_to_anchor(self, anchor: Any) -> tuple[float, float, float]:
        return tuple(-coordinate for coordinate in self.anchor(anchor))


@dataclass(frozen=True)
class MeasuredShape:
    shape: Any
    bounds: BoundingBox

    def as_attachable(
        self,
        anchor: Any = CENTER,
        spin: float | int = 0,
        orient: Any = UP,
    ) -> Any:
        centered_shape = self.shape.translate(self.bounds.translation_to_center())
        return attachable(
            anchor=anchor,
            spin=spin,
            orient=orient,
            size=list(self.bounds.size),
        )(centered_shape)

    def position(self, at: Any) -> Any:
        return self.shape.translate(self.bounds.translation_to_anchor(at))

    def scaled(self, sx: float, sy: float = 1.0, sz: float = 1.0) -> MeasuredShape:
        scales = (sx, sy, sz)
        scaled_shape = self.shape.scale(list(scales))

        scaled_mins: list[float] = []
        scaled_maxes: list[float] = []
        for lower, upper, scale in zip(self.bounds.min_corner, self.bounds.max_corner, scales, strict=True):
            lower_scaled = lower * scale
            upper_scaled = upper * scale
            scaled_mins.append(min(lower_scaled, upper_scaled))
            scaled_maxes.append(max(lower_scaled, upper_scaled))

        return MeasuredShape(
            shape=scaled_shape,
            bounds=BoundingBox(min_corner=tuple(scaled_mins), max_corner=tuple(scaled_maxes)),
        )

    def resize_to(
        self,
        *,
        x: float | None = None,
        y: float | None = None,
        z: float | None = None,
    ) -> MeasuredShape:
        size_x, size_y, size_z = self.bounds.size

        sx = x / size_x if x is not None else 1.0
        sy = y / size_y if y is not None else 1.0
        sz = z / size_z if z is not None else 1.0

        return self.scaled(sx=sx, sy=sy, sz=sz)


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


def measure_shape(
    shape: Any,
    *,
    stl_path: str | Path | None = None,
) -> MeasuredShape:
    return MeasuredShape(shape=shape, bounds=calculate_shape_bounding_box(shape, stl_path=stl_path))


def measure_stl_bounding_box(stl_path: str | Path) -> BoundingBox:
    path = Path(stl_path)
    if not path.exists():
        raise FileNotFoundError(f"STL file not found: {path}")

    if _is_binary_stl(path):
        return _measure_binary_stl(path)
    return _measure_ascii_stl(path)


def measure_stl_as_shape(stl_path: str | Path) -> MeasuredShape:
    path = Path(stl_path)
    stl_shape = import_stl(file=str(path))
    return MeasuredShape(shape=stl_shape, bounds=measure_stl_bounding_box(path))


def center_shape_on_origin(
    shape: Any,
    axes: tuple[bool, bool, bool] = (True, True, True),
    *,
    anchor: Any = None,
) -> tuple[Any, BoundingBox]:
    bounds = calculate_shape_bounding_box(shape)
    if anchor is not None:
        return shape.translate(bounds.translation_to_anchor(anchor)), bounds
    return shape.translate(bounds.translation_to_center(axes)), bounds


def _coerce_direction_vector(direction: Any) -> tuple[float, float, float]:
    if isinstance(direction, tuple | list):
        if len(direction) != 3:
            raise ValueError(f"Anchor direction must have 3 components, got {len(direction)}")
        return tuple(float(value) for value in direction)

    direction_value = getattr(direction, "value", None)
    if isinstance(direction_value, str):
        return _parse_anchor_expression(direction_value)

    raise TypeError(f"Unsupported anchor direction: {direction!r}")


def _parse_anchor_expression(expression: str) -> tuple[float, float, float]:
    axis_map: dict[str, tuple[float, float, float]] = {
        "TOP": (0.0, 0.0, 1.0),
        "BOTTOM": (0.0, 0.0, -1.0),
        "LEFT": (-1.0, 0.0, 0.0),
        "RIGHT": (1.0, 0.0, 0.0),
        "FRONT": (0.0, -1.0, 0.0),
        "BACK": (0.0, 1.0, 0.0),
        "CENTER": (0.0, 0.0, 0.0),
    }

    parsed = ast.parse(expression, mode="eval")

    def eval_node(node: ast.AST) -> tuple[float, float, float]:
        if isinstance(node, ast.Expression):
            return eval_node(node.body)

        if isinstance(node, ast.Name):
            if node.id not in axis_map:
                raise ValueError(f"Unsupported anchor symbol: {node.id}")
            return axis_map[node.id]

        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add | ast.Sub):
            left = eval_node(node.left)
            right = eval_node(node.right)
            if isinstance(node.op, ast.Add):
                return tuple(a + b for a, b in zip(left, right, strict=True))
            return tuple(a - b for a, b in zip(left, right, strict=True))

        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub | ast.UAdd):
            value = eval_node(node.operand)
            if isinstance(node.op, ast.USub):
                return tuple(-component for component in value)
            return value

        raise ValueError(f"Unsupported anchor expression: {expression!r}")

    return tuple(float(value) for value in eval_node(parsed))


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
    maxes = [-inf, -inf, -inf]

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
                _update_bounds(values[start : start + 3], mins, maxes)

    return _build_bounds(path, mins, maxes)


def _measure_ascii_stl(path: Path) -> BoundingBox:
    mins = [inf, inf, inf]
    maxes = [-inf, -inf, -inf]

    with path.open("r", encoding="utf-8", errors="ignore") as stl_file:
        for raw_line in stl_file:
            stripped = raw_line.strip()
            if not stripped.startswith("vertex "):
                continue

            _, x_value, y_value, z_value = stripped.split(maxsplit=3)
            _update_bounds((float(x_value), float(y_value), float(z_value)), mins, maxes)

    return _build_bounds(path, mins, maxes)


def _update_bounds(
    point: tuple[float, float, float] | list[float],
    mins: list[float],
    maxes: list[float],
) -> None:
    for axis, value in enumerate(point):
        mins[axis] = min(mins[axis], value)
        maxes[axis] = max(maxes[axis], value)


def _build_bounds(path: Path, mins: list[float], maxes: list[float]) -> BoundingBox:
    if any(value == inf for value in mins):
        raise ValueError(f"No vertices found in STL file: {path}")

    return BoundingBox(
        min_corner=tuple(float(value) for value in mins),
        max_corner=tuple(float(value) for value in maxes),
    )