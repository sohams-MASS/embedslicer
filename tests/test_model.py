from shapely.geometry import box

from embedslicer.model import Layer, Path


def test_layer_holds_islands():
    layer = Layer(index=0, z=1.5, islands=[box(0, 0, 1, 1)])
    assert layer.index == 0
    assert layer.z == 1.5
    assert len(layer.islands) == 1


def test_path_points():
    p = Path(points=[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)])
    assert len(p.points) == 3
    assert p.points[0] == (0.0, 0.0)
