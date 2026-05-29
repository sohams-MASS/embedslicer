import warnings

import numpy as np
from shapely.affinity import affine_transform
from shapely.geometry import Polygon

from .model import Layer


def _drop_small_holes(poly, min_area):
    """Remove interior rings (holes) smaller than min_area.

    The Stanford bunny's reconstructed base produces speckle holes (sub-mm^2)
    that are mesh noise, not real cavities. Dropping them stops them from
    becoming jagged inner perimeters.
    """
    if min_area <= 0 or not poly.interiors:
        return poly
    kept = [r for r in poly.interiors if Polygon(r).area >= min_area]
    if len(kept) == len(poly.interiors):
        return poly
    return Polygon(poly.exterior, kept)


def _planar_to_world(poly, to_3D):
    """Map a polygon from trimesh's recentered 2D section frame back to world XY.

    `section.to_2D()` recenters each layer's coordinates on that section's own
    origin, so the raw planar polygons lose their true XY position. The returned
    to_3D transform inverts that; for our Z-normal slices its rotation is
    identity, so this restores each layer's true world offset (and any rotation,
    in the general case). Without this, every layer is recentered independently
    and the stacked model is scrambled.
    """
    a, b = to_3D[0, 0], to_3D[0, 1]
    d, e = to_3D[1, 0], to_3D[1, 1]
    xoff, yoff = to_3D[0, 3], to_3D[1, 3]
    return affine_transform(poly, [a, b, d, e, xoff, yoff])


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
                planar, to_3D = section.to_2D()
                to_3D = np.asarray(to_3D)
                for poly in _iter_polys(planar.polygons_full):
                    if poly.area >= min_island_area:
                        world = _planar_to_world(poly, to_3D)
                        islands.append(_drop_small_holes(world, min_island_area))
            layers.append(Layer(index=i, z=z, islands=islands))
    return layers
