from embedslicer.gcode_aerotech import AerotechConfig, write_aerotech_gcode
from embedslicer.model import Path


def _sample_ordered():
    return [
        (0.5, Path(points=[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)])),
        (1.0, Path(points=[(5.0, 5.0), (6.0, 5.0), (6.0, 6.0), (5.0, 6.0)])),
    ]


def test_header_contains_aerotech_block():
    text = write_aerotech_gcode(_sample_ordered())
    lines = text.splitlines()
    assert any("Begin GCODE" in ln for ln in lines)
    assert any(ln.startswith("DVAR ") for ln in lines)
    assert "VELOCITY ON " in lines  # mirrors xcavate trailing-space quirk
    assert "ROUNDING ON " in lines
    assert "G90 " in lines


def test_first_pass_uses_enable_and_brake_zero():
    text = write_aerotech_gcode(_sample_ordered())
    lines = text.splitlines()
    # find first pass start marker
    i0 = next(i for i, ln in enumerate(lines) if "; Print Pass 0 " in ln)
    head = lines[i0 : i0 + 8]
    # Within the first-pass start block we set position with G92, enable, brake 0, dwell
    assert any(ln.startswith("G92 ") for ln in head)
    assert any(ln.startswith("Enable ") for ln in head)
    assert any(ln.startswith("BRAKE ") and " 0 " in ln for ln in head)
    assert any(ln.startswith("DWELL ") for ln in head)


def test_brake_pattern_matches_xcavate_single_material():
    # Xcavate's single-material pattern: each pass starts with BRAKE 0 (one per
    # pass), each pass ends with BRAKE 1, AND every SUBSEQUENT pass start
    # defensively re-issues BRAKE 1 before BRAKE 0 (xcavate aerotech.py:95).
    # For N passes: brake0 == N, brake1 == 2N-1.
    text = write_aerotech_gcode(_sample_ordered())
    lines = text.splitlines()
    brake0 = sum(1 for ln in lines if ln.startswith("BRAKE ") and " 0 " in ln)
    brake1 = sum(1 for ln in lines if ln.startswith("BRAKE ") and " 1 " in ln)
    assert brake0 == 2
    assert brake1 == 3
    # file terminates with M2
    assert lines[-1] == "M2 "


def test_subsequent_pass_uses_pass_marker_and_g91_relative_around_brake_release():
    text = write_aerotech_gcode(_sample_ordered())
    # subsequent passes use lowercase "pass" per xcavate code
    assert "; Print pass 1 " in text
    # subsequent pass body wraps BRAKE 0 in G91/G90
    assert "G91 " in text and "G90 " in text


def test_axis_and_printhead_are_configurable():
    cfg = AerotechConfig(axis_z="U", printhead="Bb")
    text = write_aerotech_gcode(_sample_ordered(), cfg)
    assert "Enable Bb " in text
    assert "BRAKE Bb 0 " in text
    assert "BRAKE Bb 1 " in text
    # axis appears in coordinated G1 motion
    assert " U" in text  # e.g. " U0.500" appears in G1/G92
