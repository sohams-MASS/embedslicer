import pytest
import trimesh


@pytest.fixture
def y_mesh():
    """Y-shaped test object: one slab base, two separated posts.

    z in [0,2): single island (slab, 10x4).
    z in [2,8): two islands (posts, 2x2 each at x=-3 and x=+3).
    """
    base = trimesh.creation.box(extents=[10.0, 4.0, 2.0])
    base.apply_translation([0.0, 0.0, 1.0])  # z spans 0..2
    post_l = trimesh.creation.box(extents=[2.0, 2.0, 6.0])
    post_l.apply_translation([-3.0, 0.0, 5.0])  # z spans 2..8, x=-3
    post_r = trimesh.creation.box(extents=[2.0, 2.0, 6.0])
    post_r.apply_translation([3.0, 0.0, 5.0])   # z spans 2..8, x=+3
    return trimesh.util.concatenate([base, post_l, post_r])


@pytest.fixture
def inverted_y_mesh():
    """Inverted Y-shape: two posts at the BOTTOM, single slab on top.

    z in [0,6): two islands (posts at x=-3, x=+3) — the 'branches'.
    z in [6,8): single island (slab, 10x4) — the merged trunk.
    """
    post_l = trimesh.creation.box(extents=[2.0, 2.0, 6.0])
    post_l.apply_translation([-3.0, 0.0, 3.0])
    post_r = trimesh.creation.box(extents=[2.0, 2.0, 6.0])
    post_r.apply_translation([3.0, 0.0, 3.0])
    slab = trimesh.creation.box(extents=[10.0, 4.0, 2.0])
    slab.apply_translation([0.0, 0.0, 7.0])
    return trimesh.util.concatenate([post_l, post_r, slab])


@pytest.fixture
def bunny_path():
    import os
    p = os.path.join(os.path.dirname(__file__), "..", "bunny.ply")
    return os.path.abspath(p)
