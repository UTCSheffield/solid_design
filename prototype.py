from solid2.extensions.bosl2 import (
    BACK,
    BOTTOM,
    FRONT,
    LEFT,
    cyl,
    linear_sweep,
    squircle,
    text3d,
)

from designs import KeyFobParamsLogan
from geometry import measure_shape


class MockDesign:
    def calculate_text_bounding_box(self, txt: str, font: str):
        probe = text3d(text=txt, font=font, size=10, h=1, anchor=BOTTOM+LEFT+FRONT)
        return measure_shape(probe).bounds

    def build_text_shape(self, params: KeyFobParamsLogan):
        bounds = self.calculate_text_bounding_box(txt=params.name, font=params.font)
        left_text_buffer = params.buffer * 2
        right_text_buffer = params.buffer
        new_text_length = params.length - left_text_buffer - right_text_buffer
        measured_text = measure_shape(
            text3d(
            text=params.name,
            font=params.font,
            size=10,
            h=params.height,
            anchor=LEFT,
        )
        ).resize_to(x=new_text_length)

        text_shape = measured_text.position(BOTTOM + LEFT + FRONT)
        text_depth = measured_text.bounds.size[1]

        return text_shape, text_depth

    def build_shape(self, params: KeyFobParamsLogan):
        text_shape, text_depth = self.build_text_shape(params)
        left_text_buffer = params.buffer * 2
        right_text_buffer = params.buffer
        top_bottom_buffer = params.buffer
        depth = text_depth + top_bottom_buffer * 2

        base = linear_sweep(
            region=squircle([params.length, depth], 0.8, anchor=LEFT+FRONT),
            height=params.height,
            #anchor=BOTTOM + LEFT + FRONT,
        )

        hole = (
            cyl(h=params.height * 3, r=1.5, _fn=16)
            .position( LEFT + BACK)
            .right(params.buffer)
            .back(params.buffer)
            .tag("remove")
        )

        text_cutout = (
            text_shape
            .right(left_text_buffer)
            .fwd(top_bottom_buffer)
            .tag("remove")
        )

        return base(hole, text_cutout).diff()


shape = MockDesign().build_shape(
    KeyFobParamsLogan(length=50, buffer=2.5, height=3, name="Matthew", font="Liberation Mono")
    #KeyFobParamsLogan(length=50, buffer=2.5, height=3, name="Martyn", font="Times New Roman")

)

shape.save_as_stl()

