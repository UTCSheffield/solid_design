from solid2 import *
from pathlib import Path
from solid2.extensions.bosl2 import squircle
from designs import KeyFobParams

class mock_design:
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


shape = mock_design().build_shape(KeyFobParams(length=50, depth=20, height=5, name="Test"))
shape.save_as_stl()

