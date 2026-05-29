from shapely.geometry import Polygon, box

from embedslicer.toolpath import generate_perimeters


def _bbox_size(path):
    xs = [p[0] for p in path.points]
    ys = [p[1] for p in path.points]
    return (max(xs) - min(xs), max(ys) - min(ys))


def test_two_perimeters_offset_inward():
    sq = box(0, 0, 10, 10)
    paths = generate_perimeters(sq, line_width=1.0, perimeters=2)
    assert len(paths) == 2
    w0, _ = _bbox_size(paths[0])
    w1, _ = _bbox_size(paths[1])
    assert abs(w0 - 9.0) < 1e-6   # first loop inset by line_width/2
    assert abs(w1 - 7.0) < 1e-6   # second loop inset by 3*line_width/2


def test_buffer_empty_stops_early():
    sq = box(0, 0, 5, 5)
    # 5 loops requested, but a 5x5 square only holds 2 full 1mm-wide loops
    # (offsets -0.5 -> 4x4, -1.5 -> 2x2, -2.5 -> empty) so it stops early.
    paths = generate_perimeters(sq, line_width=1.0, perimeters=5)
    assert 0 < len(paths) < 5


def test_thin_island_below_line_width_produces_no_loops():
    # An island thinner than one line width yields no perimeters (known
    # limitation: no thin-wall/gap-fill handling).
    sq = box(0, 0, 0.5, 0.5)
    paths = generate_perimeters(sq, line_width=1.0, perimeters=3)
    assert paths == []


def test_holes_produce_inner_loops():
    outer = [(0, 0), (10, 0), (10, 10), (0, 10)]
    hole = [(4, 4), (6, 4), (6, 6), (4, 6)]
    poly = Polygon(outer, [hole])
    paths = generate_perimeters(poly, line_width=1.0, perimeters=1)
    # one exterior + one interior ring
    assert len(paths) == 2
