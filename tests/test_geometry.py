from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from solid2 import cube
from solid2.extensions.bosl2 import BACK, BOTTOM, FRONT, LEFT, TOP

from geometry import BoundingBox, measure_shape, measure_stl_as_shape


class GeometryInterfacesTest(unittest.TestCase):
    def test_bounding_box_anchor_math_with_bosl2_constants(self) -> None:
        bounds = BoundingBox(min_corner=(0.0, 0.0, 0.0), max_corner=(10.0, 20.0, 30.0))

        self.assertEqual(bounds.anchor(TOP), (5.0, 10.0, 30.0))
        self.assertEqual(bounds.anchor(TOP + LEFT + BACK), (0.0, 20.0, 30.0))
        self.assertEqual(bounds.translation_to_anchor(BOTTOM + LEFT + FRONT), (-0.0, -0.0, -0.0))

    def test_measured_shape_scaled_updates_bounds(self) -> None:
        measured = measure_shape(cube([2, 4, 6]))
        scaled = measured.scaled(sx=2.0, sy=0.5, sz=3.0)

        self.assertEqual(scaled.bounds.size, (4.0, 2.0, 18.0))

    def test_measured_shape_resize_to_updates_target_dimensions(self) -> None:
        measured = measure_shape(cube([2, 4, 6]))
        resized = measured.resize_to(x=10.0, y=8.0, z=3.0)

        self.assertEqual(resized.bounds.size, (10.0, 8.0, 3.0))

    def test_measure_stl_as_shape_round_trip(self) -> None:
        with TemporaryDirectory() as temp_dir:
            stl_path = Path(temp_dir) / "probe.stl"
            cube([3, 5, 7]).save_as_stl(str(stl_path))

            measured = measure_stl_as_shape(stl_path)

            self.assertEqual(measured.bounds.size, (3.0, 5.0, 7.0))
            self.assertEqual(type(measured.shape).__name__, "import_stl")


if __name__ == "__main__":
    unittest.main()
