from solid2 import *
from pathlib import Path
from solid2.extensions.bosl2 import squircle, BOTTOM, TOP, LEFT, RIGHT, FORWARD, BACK
from designs import KeyFobParams, KeyFobParamsLogan
from geometry import calculate_shape_bounding_box, center_shape_on_origin

class mock_design:
    def build_shape(self, params: KeyFobParamsLogan): 
        # Create the text shape, extrude it
        textshape = text(text=params.name, font=params.font).linear_extrude(1)
        # Calculate the bounding box of the text shape
        bounds = calculate_shape_bounding_box(textshape)
        
        # Calculate the new length of the text after accounting for the buffer, then scale the text shape to fit within the desired length
        new_text_length = params.length - (params.buffer * 3) # the end with the hole is a buffer wider
        
        # Calculate the scale factor based on the new text length and the original text length, then scale the text shape accordingly
        scale_factor = new_text_length / bounds.size[0]

        #Make the text again so we have the height ok
        textshape = text(text=params.name, font=params.font).translate(*bounds.translation_to_zero())
        textshape = textshape.scale(scale_factor).linear_extrude(params.height)
        
        # Calculate the new depth of the shape based on the scaled text size and the buffer
        depth = (bounds.size[1] * scale_factor) + params.buffer * 2

        # Create the base shape as a cube with the calculated dimensions
        # shape = cube([params.length, depth, params.height])
        shape = squircle([params.length, depth], 0.8).forward(depth / 2).right(params.length / 2).linear_extrude(params.height)
        
        # move the text up by half the thickness and right by 2 buffers and forward by the buffer, then cut it out of the base shape
        shape -= textshape.up(params.height/2).right(params.buffer*2).forward(params.buffer)

        #  then translating the hole into the top left corner
        shape -= (
            cylinder(h=params.height * 3, r=1.5, _fn=16)
            .right(params.buffer)
            .forward(depth - params.buffer)
            .down(params.height)
        )

        return shape


shape = mock_design().build_shape(KeyFobParamsLogan(length=50, buffer=2.5, height=3, name="Matthew", font="Liberation Mono"))
#shape = mock_design().build_shape(KeyFobParamsLogan(length=50, buffer=2.5, height=3, name="Martyn", font="Times New Roman"))


shape.save_as_stl()

