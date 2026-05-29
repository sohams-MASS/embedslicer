import os

from embedslicer.main import run


def _downward_transitions(ordered, eps=1e-3):
    zs = [z for z, _ in ordered]
    return sum(1 for a, b in zip(zs, zs[1:]) if b < a - eps)


def test_bunny_end_to_end(bunny_path, tmp_path):
    out = tmp_path / "bunny.gcode"
    plan, layers, ordered = run(
        bunny_path,
        output=str(out),
        layer_height=0.2,
        line_width=0.4,
        perimeters=2,
        min_island_area=0.2,
        min_branch_layers=3,
    )
    assert out.exists()
    text = out.read_text()
    assert text.count("StartExtrusion") == text.count("StopExtrusion") > 0

    # trunk + (at least) two ear branches
    assert len(plan) >= 3
    # anti-streak: the ears must NOT alternate per layer. A per-layer-hopping
    # slicer would produce one downward Z transition per ear layer (~10+).
    # Branch-sequential printing yields only a couple.
    assert _downward_transitions(ordered) <= 3
