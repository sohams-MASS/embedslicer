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


def test_rootless_fragment_does_not_print_first():
    # A rooted body (layers 0-3, at x=10) and a graph-disconnected fragment
    # (layers 4-7, at x=0) that does NOT overlap the body. The rooted body must
    # be printed before the floating fragment, regardless of centroid x.
    from shapely.geometry import box

    from embedslicer.model import Layer

    layers = []
    for i in range(4):
        layers.append(Layer(index=i, z=float(i), islands=[box(10, 0, 12, 2)]))
    for i in range(4, 8):
        layers.append(Layer(index=i, z=float(i), islands=[box(0, 0, 2, 2)]))

    plan = build_plan(layers, min_branch_layers=3)
    base_layers = [min(li for li, _ in g) for g in plan]
    # non-decreasing base layers -> no group prints above an un-printed support
    assert base_layers == sorted(base_layers)
    # printing starts at the bottom
    assert 0 in {li for li, _ in plan[0]}


def test_nested_split_recurses():
    # Trunk (0-2) splits into left and right (3-5); the right branch itself
    # splits into two prongs (6-8). Exercises the recursion.
    from shapely.geometry import box

    from embedslicer.model import Layer

    layers = []
    for i in range(3):
        layers.append(Layer(index=i, z=float(i), islands=[box(0, 0, 20, 2)]))
    for i in range(3, 6):
        layers.append(Layer(index=i, z=float(i), islands=[box(2, 0, 4, 2), box(10, 0, 18, 2)]))
    for i in range(6, 9):
        layers.append(
            Layer(
                index=i,
                z=float(i),
                islands=[box(2, 0, 4, 2), box(10, 0, 12, 2), box(16, 0, 18, 2)],
            )
        )

    plan = build_plan(layers, min_branch_layers=2)
    # trunk + left + (right-trunk + 2 prongs) => at least 4 groups (nested split happened)
    assert len(plan) >= 4
    assert 0 in {li for li, _ in plan[0]}  # trunk prints first
    for g in plan:
        lis = [li for li, _ in g]
        assert lis == sorted(lis)  # every group bottom-up
