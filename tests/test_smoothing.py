import numpy as np
from shapely.geometry import Polygon

from embedslicer.smoothing import smooth_polygon


def _noisy_circle(r=10.0, n=400, noise=0.15, seed=0):
    rng = np.random.default_rng(seed)
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    rr = r + rng.normal(0, noise, n)
    return Polygon(np.column_stack([rr * np.cos(t), rr * np.sin(t)]))


def _total_abs_turning_deg(poly):
    p = np.asarray(poly.exterior.coords)[:-1]
    d = np.diff(np.vstack([p, p[0]]), axis=0)
    d = d / np.clip(np.linalg.norm(d, axis=1, keepdims=True), 1e-12, None)
    dots = np.clip((d[:-1] * d[1:]).sum(axis=1), -1, 1)
    return float(np.degrees(np.arccos(dots)).sum())


def test_smoothing_reduces_jaggedness():
    p = _noisy_circle()
    s = smooth_polygon(p, tolerance=0.2, point_spacing=0.5)
    # a clean closed curve turns ~360 deg total; noise inflates that a lot
    assert _total_abs_turning_deg(s) < 0.5 * _total_abs_turning_deg(p)


def test_smoothing_preserves_area():
    p = _noisy_circle()
    s = smooth_polygon(p, tolerance=0.2, point_spacing=0.5)
    assert abs(s.area - p.area) / p.area < 0.05


def test_smoothing_preserves_holes_and_validity():
    outer = _noisy_circle(r=10.0)
    hole = _noisy_circle(r=3.0)
    p = outer.difference(hole)
    s = smooth_polygon(p, tolerance=0.2, point_spacing=0.5)
    assert s.is_valid and not s.is_empty
    assert len(list(s.interiors)) == 1


def test_zero_tolerance_is_noop():
    p = _noisy_circle()
    assert smooth_polygon(p, tolerance=0.0) is p


def test_tiny_polygon_does_not_crash():
    tri = Polygon([(0, 0), (1, 0), (0.5, 1)])
    s = smooth_polygon(tri, tolerance=0.1, point_spacing=0.5)
    assert s.is_valid and not s.is_empty
