import numpy as np
import trimesh


def load_oriented(path, scale=1.0, up_axis="z", flip=False):
    """Load a mesh, apply uniform scale, rotate so up_axis maps to +Z,
    optionally flip it upside-down (180 deg about X).
    """
    mesh = trimesh.load(path, force="mesh")
    if scale != 1.0:
        mesh.apply_scale(scale)
    axis = up_axis.lower()
    if axis == "z":
        pass
    elif axis == "y":
        # rotate +90 deg about X so original +Y -> +Z
        mesh.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    elif axis == "x":
        # rotate -90 deg about Y so original +X -> +Z
        mesh.apply_transform(trimesh.transformations.rotation_matrix(-np.pi / 2, [0, 1, 0]))
    else:
        raise ValueError(f"up_axis must be x, y, or z; got {up_axis!r}")
    if flip:
        # 180 deg about X: +Z -> -Z, so the model is upside down
        mesh.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]))
    if not mesh.is_watertight:
        print("warning: mesh is not watertight; slicing may produce open contours")
    return mesh
