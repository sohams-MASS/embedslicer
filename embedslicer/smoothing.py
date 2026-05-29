import numpy as np
from scipy.interpolate import splev, splprep
from shapely.geometry import LinearRing, Polygon


def _smooth_ring(coords, tolerance, point_spacing):
    """Smooth one ring with a periodic cubic spline; return (N,2) points or None.

    None means the ring couldn't be smoothed (too few distinct points or the
    spline fit failed) and the caller should keep the original ring.
    """
    pts = np.asarray(coords, dtype=float)
    # shapely rings repeat the first vertex at the end; drop it for a periodic fit
    if len(pts) > 1 and np.allclose(pts[0], pts[-1]):
        pts = pts[:-1]
    # drop consecutive duplicates (splprep rejects them)
    keep = [0]
    for i in range(1, len(pts)):
        if np.linalg.norm(pts[i] - pts[keep[-1]]) > 1e-9:
            keep.append(i)
    pts = pts[keep]
    n = len(pts)
    if n < 4:
        return None

    closed = np.vstack([pts, pts[0]])
    length = float(np.linalg.norm(np.diff(closed, axis=0), axis=1).sum())
    n_out = max(16, int(round(length / max(point_spacing, 1e-6))))
    # scipy's smoothing condition s ~ sum of squared residuals; tolerance is the
    # approximate per-point RMS deviation (mm) we allow from the raw contour.
    s = n * (tolerance**2)
    try:
        tck, _ = splprep([pts[:, 0], pts[:, 1]], s=s, per=1)
    except Exception:
        return None
    u = np.linspace(0.0, 1.0, n_out, endpoint=False)
    x, y = splev(u, tck)
    return np.column_stack([x, y])


def smooth_polygon(polygon, tolerance=0.05, point_spacing=0.3):
    """Smooth a polygon's contours with a periodic spline to remove facet noise.

    tolerance: approximate RMS deviation (mm) allowed from the raw contour;
        larger = smoother. tolerance <= 0 disables smoothing (returns input).
    point_spacing: spacing (mm) at which the smoothed curve is resampled.

    Holes are preserved. Falls back to the original ring where it can't be
    smoothed, and to the original polygon if the smoothed result is invalid.
    """
    if tolerance <= 0:
        return polygon

    ext = _smooth_ring(polygon.exterior.coords, tolerance, point_spacing)
    shell = LinearRing(ext) if ext is not None else polygon.exterior

    holes = []
    for interior in polygon.interiors:
        sm = _smooth_ring(interior.coords, tolerance, point_spacing)
        holes.append(LinearRing(sm) if sm is not None else interior)

    result = Polygon(shell, holes)
    if not result.is_valid or result.is_empty:
        return polygon
    return result
