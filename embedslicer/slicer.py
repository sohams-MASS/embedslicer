import warnings

import numpy as np

from .model import Layer


def _iter_polys(geom):
    if geom is None:
        return
    # trimesh's Path2D.polygons_full returns a sequence (list/array) of
    # shapely Polygons (one per island); handle that as well as a single
    # shapely Polygon/MultiPolygon geometry.
    if isinstance(geom, (list, tuple, np.ndarray)):
        for g in geom:
            yield from _iter_polys(g)
        return
    if geom.is_empty:
        return
    if geom.geom_type == "Polygon":
        yield geom
    elif geom.geom_type == "MultiPolygon":
        for g in geom.geoms:
            yield g


def slice_mesh(mesh, layer_height, min_island_area=0.0):
    """Slice along +Z into planar layers. Each layer is a list of island polygons."""
    z_min, z_max = float(mesh.bounds[0][2]), float(mesh.bounds[1][2])
    n = int(np.ceil((z_max - z_min) / layer_height))
    layers = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(n):
            z = z_min + layer_height * (i + 0.5)
            islands = []
            section = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
            if section is not None:
                planar, _ = section.to_2D()
                for poly in _iter_polys(planar.polygons_full):
                    if poly.area >= min_island_area:
                        islands.append(poly)
            layers.append(Layer(index=i, z=z, islands=islands))
    return layers
