import embedslicer


def test_package_imports():
    assert embedslicer.__doc__


def test_y_mesh_fixture(y_mesh):
    # bbox: x in [-5,5], z in [0,8]
    assert y_mesh.bounds[1][2] == 8.0
    assert y_mesh.bounds[0][2] == 0.0
