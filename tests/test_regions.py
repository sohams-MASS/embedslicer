from embedslicer.regions import build_plan
from embedslicer.slicer import slice_mesh


def _x_of(plan, group_idx, layers):
    # centroid x of the lowest island in a group
    cells = sorted(plan[group_idx], key=lambda c: c[0])
    li, ii = cells[0]
    return layers[li].islands[ii].centroid.x


def test_y_mesh_gives_trunk_plus_two_branches(y_mesh):
    layers = slice_mesh(y_mesh, layer_height=0.5, min_island_area=0.1)
    plan = build_plan(layers, min_branch_layers=3)
    assert len(plan) == 3  # trunk + left ear + right ear

    trunk = plan[0]
    # trunk = slab band, all island index 0, layers 0..3
    assert sorted({li for li, _ in trunk}) == [0, 1, 2, 3]

    # branches ordered left (x=-3) then right (x=+3)
    assert _x_of(plan, 1, layers) < 0 < _x_of(plan, 2, layers)
    # each branch spans the 12 post layers
    assert len(plan[1]) == 12
    assert len(plan[2]) == 12


def test_min_branch_layers_suppresses_split(y_mesh):
    layers = slice_mesh(y_mesh, layer_height=0.5, min_island_area=0.1)
    # require longer persistence than the posts have -> no split, single group
    plan = build_plan(layers, min_branch_layers=99)
    assert len(plan) == 1


def test_each_group_is_bottom_up(y_mesh):
    layers = slice_mesh(y_mesh, layer_height=0.5, min_island_area=0.1)
    plan = build_plan(layers, min_branch_layers=3)
    for group in plan:
        layer_indices = [li for li, _ in group]
        assert layer_indices == sorted(layer_indices)
