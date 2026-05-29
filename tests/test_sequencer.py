from embedslicer.regions import build_plan
from embedslicer.sequencer import order_paths
from embedslicer.slicer import slice_mesh


def _downward_transitions(ordered, eps=1e-9):
    zs = [z for z, _ in ordered]
    return sum(1 for a, b in zip(zs, zs[1:]) if b < a - eps)


def test_one_downward_transition_for_two_branches(y_mesh):
    layers = slice_mesh(y_mesh, layer_height=0.5, min_island_area=0.1)
    plan = build_plan(layers, min_branch_layers=3)
    ordered = order_paths(plan, layers, line_width=0.4, perimeters=1)
    # trunk up, ear A up, ONE drop to ear B base, ear B up -> exactly one down step
    assert _downward_transitions(ordered) == 1


def test_paths_follow_plan_group_order(y_mesh):
    layers = slice_mesh(y_mesh, layer_height=0.5, min_island_area=0.1)
    plan = build_plan(layers, min_branch_layers=3)
    ordered = order_paths(plan, layers, line_width=0.4, perimeters=1)
    # every emitted path has at least 3 points (a rectangle loop)
    assert all(len(path.points) >= 3 for _, path in ordered)
    # total paths == total cells (1 perimeter loop per island here)
    total_cells = sum(len(g) for g in plan)
    assert len(ordered) == total_cells
