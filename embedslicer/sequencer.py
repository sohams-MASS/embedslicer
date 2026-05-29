from .toolpath import generate_perimeters


def order_paths(plan, layers, line_width, perimeters):
    """Flatten the region plan into an ordered list of (z, Path).

    Groups are emitted in plan order; within a group, cells bottom-up. This is
    the single point that enforces branch-sequential (anti-streak) ordering.
    """
    ordered = []
    for group in plan:
        for li, ii in group:
            z = layers[li].z
            polygon = layers[li].islands[ii]
            for path in generate_perimeters(polygon, line_width, perimeters):
                ordered.append((z, path))
    return ordered
