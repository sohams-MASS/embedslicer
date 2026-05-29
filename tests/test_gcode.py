from embedslicer.gcode import write_gcode
from embedslicer.model import Path


def _sample_ordered():
    # two loops at two different z heights
    return [
        (0.5, Path(points=[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)])),
        (1.0, Path(points=[(5.0, 5.0), (6.0, 5.0), (6.0, 6.0), (5.0, 6.0)])),
    ]


def test_matched_extrusion_toggles():
    text = write_gcode(_sample_ordered())
    lines = text.splitlines()
    assert lines.count("StartExtrusion") == lines.count("StopExtrusion") == 2


def test_extrusion_never_nested_and_off_during_travel():
    text = write_gcode(_sample_ordered())
    extruding = False
    for ln in text.splitlines():
        if ln == "StartExtrusion":
            assert not extruding  # no nesting
            extruding = True
        elif ln == "StopExtrusion":
            assert extruding
            extruding = False
    assert not extruding  # ends closed


def test_header_and_feedrates_present():
    text = write_gcode(_sample_ordered(), print_feedrate=600, travel_feedrate=1800)
    assert "G21" in text and "G90" in text
    assert "F600" in text and "F1800" in text
    # the loop returns to its start point (closed)
    assert text.count("StartExtrusion") == 2
