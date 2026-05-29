from .model import Path


def _iter_polys(geom):
    if geom is None or geom.is_empty:
        return
    if geom.geom_type == "Polygon":
        yield geom
    elif geom.geom_type == "MultiPolygon":
        for g in geom.geoms:
            yield g


def _ring_to_path(ring):
    coords = list(ring.coords)
    if len(coords) > 1 and coords[0] == coords[-1]:
        coords = coords[:-1]
    return Path(points=[(float(x), float(y)) for x, y in coords])


def generate_perimeters(polygon, line_width, perimeters):
    """Return inward-offset perimeter loops (exterior + any interior rings)."""
    paths = []
    for i in range(perimeters):
        offset = -line_width * (i + 0.5)
        shrunk = polygon.buffer(offset, join_style=2)  # 2 = mitre
        if shrunk.is_empty:
            # Region exhausted for this offset. If we already have loops,
            # stop. If this is the first (thinnest) loop and the island is
            # simply too thin to hold a full-width loop, back the offset
            # magnitude off until a valid centerline loop appears, emit it,
            # then stop.
            if paths or polygon.is_empty:
                break
            for _ in range(64):
                offset *= 0.9
                shrunk = polygon.buffer(offset, join_style=2)
                if not shrunk.is_empty:
                    break
            if shrunk.is_empty:
                break
            for poly in _iter_polys(shrunk):
                paths.append(_ring_to_path(poly.exterior))
                for interior in poly.interiors:
                    paths.append(_ring_to_path(interior))
            break
        for poly in _iter_polys(shrunk):
            paths.append(_ring_to_path(poly.exterior))
            for interior in poly.interiors:
                paths.append(_ring_to_path(interior))
    return paths
