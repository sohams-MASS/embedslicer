from embedslicer.preview import render
from embedslicer.regions import build_plan
from embedslicer.slicer import slice_mesh


def test_render_writes_png(y_mesh, tmp_path):
    layers = slice_mesh(y_mesh, layer_height=0.5, min_island_area=0.1)
    plan = build_plan(layers, min_branch_layers=3)
    out = tmp_path / "preview.png"
    render(plan, layers, str(out), line_width=0.4, perimeters=1)
    assert out.exists() and out.stat().st_size > 0
