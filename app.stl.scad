difference() {
	cube(size = [75, 12, 1.0]);
	translate(v = [5, 1, 1.0]) {
		linear_extrude(center = true, height = 1.0) {
			text(text = "Streamlit");
		}
	}
	translate(v = [2, 8, 0]) {
		cylinder(center = true, h = 3, r1 = 1, r2 = 1.0);
	}
}
