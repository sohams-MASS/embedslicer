from embedslicer.slicer import slice_mesh


def test_y_mesh_island_counts(y_mesh):
    layers = slice_mesh(y_mesh, layer_height=0.5, min_island_area=0.1)
    # z centers: 0.25, 0.75, ... 7.75  -> 16 layers
    assert len(layers) == 16
    # slab band (z < 2): single island
    slab = [l for l in layers if l.z < 2.0]
    assert all(len(l.islands) == 1 for l in slab)
    # posts band (z > 2): two islands
    posts = [l for l in layers if l.z > 2.0]
    assert all(len(l.islands) == 2 for l in posts)


def test_min_island_area_filters_tiny(y_mesh):
    # absurdly high min area drops everything
    layers = slice_mesh(y_mesh, layer_height=0.5, min_island_area=1e6)
    assert all(len(l.islands) == 0 for l in layers)


def test_layers_sorted_bottom_up(y_mesh):
    layers = slice_mesh(y_mesh, layer_height=0.5, min_island_area=0.1)
    zs = [l.z for l in layers]
    assert zs == sorted(zs)
    assert [l.index for l in layers] == list(range(len(layers)))
