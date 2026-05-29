import trimesh

from embedslicer.slicer import slice_mesh


def test_islands_keep_true_world_xy_when_offset_varies_by_height():
    # A 'leaning' object: a lower block centered at world x=0 (z 0..2) and an
    # upper block centered at world x=4 (z 2..4). Each layer's true world X
    # depends on height. The slicer must preserve that. trimesh's to_2D()
    # recenters every section on its own origin, which collapsed all layers to
    # ~x=0 and scrambled the stacked model -- this guards against that.
    low = trimesh.creation.box(extents=[3, 3, 2])
    low.apply_translation([0, 0, 1])  # x centered at 0, z 0..2
    high = trimesh.creation.box(extents=[3, 3, 2])
    high.apply_translation([4, 0, 3])  # x centered at 4, z 2..4
    mesh = trimesh.util.concatenate([low, high])

    layers = slice_mesh(mesh, layer_height=0.5, min_island_area=0.1)
    low_layers = [l for l in layers if l.z < 2.0 and l.islands]
    high_layers = [l for l in layers if l.z > 2.0 and l.islands]
    assert low_layers and high_layers
    assert all(abs(l.islands[0].centroid.x - 0.0) < 0.1 for l in low_layers)
    assert all(abs(l.islands[0].centroid.x - 4.0) < 0.1 for l in high_layers)


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
