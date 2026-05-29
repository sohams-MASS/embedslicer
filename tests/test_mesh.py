import numpy as np

from embedslicer.mesh import load_oriented


def test_load_bunny_default(bunny_path):
    m = load_oriented(bunny_path)
    # as-is bbox (mm): ~15.57 x 12.07 x 15.43
    ext = np.asarray(m.extents)
    assert np.allclose(ext, [15.57, 12.07, 15.43], atol=0.05)


def test_scale_doubles_extents(bunny_path):
    base = np.asarray(load_oriented(bunny_path).extents)
    scaled = np.asarray(load_oriented(bunny_path, scale=2.0).extents)
    assert np.allclose(scaled, base * 2.0, atol=1e-3)


def test_up_axis_y_maps_to_z(bunny_path):
    # Re-orienting Y-up should move the original Y extent onto Z.
    base = np.asarray(load_oriented(bunny_path).extents)  # [x, y, z]
    rot = np.asarray(load_oriented(bunny_path, up_axis="y").extents)
    assert abs(rot[2] - base[1]) < 1e-3
