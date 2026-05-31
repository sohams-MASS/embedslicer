from .smoothing import smooth_polygon
from .toolpath import generate_perimeters


# Irrational shift step (~ golden ratio fraction) so consecutive-layer seams
# never repeat in vertical alignment.
_SEAM_STEP = 0.61803398875


def order_paths(plan, layers, line_width, perimeters, smoothing=0.0, point_spacing=None):
    """Flatten the region plan into an ordered list of (z, Path).

    Groups are emitted in plan order; within a group, cells bottom-up. This is
    the single point that enforces branch-sequential (anti-streak) ordering.

    smoothing > 0 spline-smooths each island contour (mm tolerance) before
    offsetting, removing mesh-facet jaggedness from the toolpaths. The seam of
    each smoothed loop is shifted by a layer-dependent fraction so the closing
    chord doesn't align vertically across layers (which would otherwise read
    as a visible "C-shape gap" in 3D previews).

    point_spacing defaults to line_width when None — keeps sample density
    matched to bead width.
    """
    if point_spacing is None:
        point_spacing = max(line_width, 0.05)
    ordered = []
    for group in plan:
        for li, ii in group:
            z = layers[li].z
            polygon = layers[li].islands[ii]
            if smoothing > 0:
                seam_shift = (li * _SEAM_STEP) % 1.0
                polygon = smooth_polygon(polygon, smoothing, point_spacing, seam_shift=seam_shift)
            for path in generate_perimeters(polygon, line_width, perimeters):
                ordered.append((z, path))
    return ordered
