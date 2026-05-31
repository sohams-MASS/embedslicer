from embedslicer.gcode_automation1 import (
    Automation1Config,
    write_automation1_gcode,
)
from embedslicer.model import Path


def _sample_ordered():
    return [
        (0.5, Path(points=[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)])),
        (1.0, Path(points=[(5.0, 5.0), (6.0, 5.0), (6.0, 6.0), (5.0, 6.0)])),
    ]


def test_program_wrapper_and_variables():
    text = write_automation1_gcode(_sample_ordered())
    assert text.lstrip().startswith("program")
    assert "var $X_start as real = 0" in text
    assert "var $Y_start as real = 0" in text
    assert "var $Z_print as real = 0" in text
    assert "$Z_safe" in text
    assert "$jog_speed" in text
    assert "var $print_speed as real =" in text
    assert "print_network(" in text
    assert "$print_speed" in text
    assert "function print_network(" in text
    assert "function StartExtrusion(" in text
    assert "function StopExtrusion(" in text


def test_extrusion_functions_have_no_lift_argument():
    text = write_automation1_gcode(_sample_ordered())
    # StopExtrusion no longer lifts to safe Z; signature drops $Z_safe.
    assert "function StopExtrusion($dwell_end as real)" in text
    # StartExtrusion still wraps DriveBrakeOff + Dwell.
    assert "DriveBrakeOff(" in text
    assert "DriveBrakeOn(" in text
    assert "Dwell($dwell_start)" in text
    assert "Dwell($dwell_end)" in text


def test_velocity_blending_toggled_once_for_the_whole_print():
    text = write_automation1_gcode(_sample_ordered())
    assert text.count("VelocityBlendingOn()") == 1
    assert text.count("VelocityBlendingOff()") == 1
    assert text.count("CornerRoundingOn()") == 1
    assert text.count("CornerRoundingOff()") == 1


def test_no_safe_z_bounce_between_passes():
    text = write_automation1_gcode(_sample_ordered())
    # Only allowed $Z_safe motion: initial setup in program block, final park
    # in print_network. No per-pass bounce.
    z_safe_moves = [
        ln for ln in text.splitlines()
        if ln.lstrip().startswith("G1 ") and "$Z_safe" in ln
    ]
    assert len(z_safe_moves) == 2, f"expected 2 $Z_safe moves, found {len(z_safe_moves)}: {z_safe_moves}"


def test_each_pass_has_one_direct_travel_then_StartExtrusion():
    text = write_automation1_gcode(_sample_ordered())
    lines = text.splitlines()
    # for each pass, immediately before StartExtrusion there must be exactly one
    # travel G1 that already includes the Z axis (XY+Z combined direct travel).
    for i, ln in enumerate(lines):
        if ln.strip() == "StartExtrusion($dwell_start)":
            prev = lines[i - 1]
            assert prev.startswith("G1 X ($X_start+")
            assert "($Z_print+" in prev
            assert "F $jog_speed" in prev


def test_extrusion_moves_use_print_speed_variable():
    text = write_automation1_gcode(_sample_ordered())
    extrusion = [
        ln for ln in text.splitlines()
        if ln.startswith("G1 X ($X_start+") and "($Z_print+" in ln and "$print_speed" in ln
    ]
    assert extrusion
    # any G1 motion that's NOT a $jog_speed travel and NOT a $Z_safe move must use $print_speed
    for ln in extrusion:
        assert "F $print_speed" in ln
        assert "F 1.0000" not in ln


def test_motion_uses_variable_relative_coordinates():
    text = write_automation1_gcode(_sample_ordered())
    assert "($X_start+" in text
    assert "($Y_start+" in text
    assert "($Z_print+" in text


def test_axis_and_printhead_are_configurable():
    cfg = Automation1Config(axis_z="U", printhead="Bb")
    text = write_automation1_gcode(_sample_ordered(), cfg)
    assert "DriveBrakeOff(Bb)" in text
    assert "DriveBrakeOn(Bb)" in text
    assert "U ($Z_print+" in text
