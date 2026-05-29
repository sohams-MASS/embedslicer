from .smoothing import smooth_polygon
from .toolpath import generate_perimeters


def order_paths(plan, layers, line_width, perimeters, smoothing=0.0, point_spacing=0.3):
    """Flatten the region plan into an ordered list of (z, Path).

    Groups are emitted in plan order; within a group, cells bottom-up. This is
    the single point that enforces branch-sequential (anti-streak) ordering.

    smoothing > 0 spline-smooths each island contour (mm tolerance) before
    offsetting, removing mesh-facet jaggedness from the toolpaths.
    """
    ordered = []
    for group in plan:
        for li, ii in group:
            z = layers[li].z
            polygon = layers[li].islands[ii]
            if smoothing > 0:
                polygon = smooth_polygon(polygon, smoothing, point_spacing)
            for path in generate_perimeters(polygon, line_width, perimeters):
                ordered.append((z, path))
    return ordered
