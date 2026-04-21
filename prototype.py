from solid2 import *
from pathlib import Path
from solid2.extensions.bosl2 import squircle
from designs import KeyFobParams
from geometry import calculate_shape_bounding_box, center_shape_on_origin

class mock_design:
    def build_shape(self, params: KeyFobParams): 
        # building from the center so the box and text are aligned,
        shape = cube([params.length, params.depth, params.height], center=True)

        distance_from_corner = 3

        textshape = text(text=params.name).linear_extrude(params.height, center=True)
        bounds = calculate_shape_bounding_box(textshape)
        textshape = textshape.translate(*bounds.translation_to_center())
        #textshape = center_shape_on_origin(textshape)

        #nudging the text up so it's not flush with the bottom of the keyfob
        shape -= textshape.up(params.height/2)

        #  then translating to the corner for the hole
        shape -= (
            cylinder(h=params.height * 3, r=2)
            .left(params.length / 2 - distance_from_corner)
            .forward(params.depth / 2 - distance_from_corner)
            .down(params.height)
        )

        return shape


shape = mock_design().build_shape(KeyFobParams(length=50, depth=20, height=3, name="Martyn"))
shape.save_as_stl()

