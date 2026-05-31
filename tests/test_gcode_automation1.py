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
    # top-level program block opens the file
    assert text.lstrip().startswith("program")
    # canonical variable declarations
    assert "var $X_start as real = 0" in text
    assert "var $Y_start as real = 0" in text
    assert "var $Z_print as real = 0" in text
    assert "$Z_safe" in text
    assert "$jog_speed" in text
    # print speed is now also a declared variable
    assert "var $print_speed as real =" in text
    # main program calls into print_network() with $print_speed
    assert "print_network(" in text
    assert "$print_speed" in text
    # functions exist
    assert "function print_network(" in text
    assert "function StartExtrusion(" in text
    assert "function StopExtrusion(" in text


def test_extrusion_moves_use_print_speed_variable():
    text = write_automation1_gcode(_sample_ordered())
    # extrusion moves carry the axis-Z token "($Z_print+"; travel-only moves
    # don't. Every extrusion move's feedrate must reference $print_speed.
    extrusion = [
        ln for ln in text.splitlines()
        if ln.startswith("G1 X ($X_start+") and "($Z_print+" in ln
    ]
    assert extrusion
    for ln in extrusion:
        assert "F $print_speed" in ln
        assert "F 1.0000" not in ln


def test_extrusion_functions_use_drive_brake_and_dwell():
    text = write_automation1_gcode(_sample_ordered())
    assert "DriveBrakeOff(" in text  # StartExtrusion body
    assert "DriveBrakeOn(" in text   # StopExtrusion body
    assert "Dwell($dwell_start)" in text
    assert "Dwell($dwell_end)" in text


def test_pass_uses_velocity_blending_and_corner_rounding():
    text = write_automation1_gcode(_sample_ordered())
    assert "VelocityBlendingOn()" in text
    assert "CornerRoundingOn()" in text
    assert "VelocityBlendingOff()" in text
    assert "CornerRoundingOff()" in text


def test_each_pass_ends_with_disable_then_enable_y():
    text = write_automation1_gcode(_sample_ordered())
    # one Disable(Y) and one Enable(Y) per pass
    assert text.count("Disable(Y)") == 2
    assert text.count("Enable(Y)") == 2
    # StartExtrusion / StopExtrusion are called once per pass (plus their own
    # function definitions, which contain neither the call nor a stray match)
    assert text.count("StartExtrusion($dwell_start)") == 2
    assert text.count("StopExtrusion($Z_safe, $dwell_end)") == 2


def test_motion_uses_variable_relative_coordinates():
    text = write_automation1_gcode(_sample_ordered())
    # at least one G1 with the $X_start / $Y_start / $Z_print idiom
    assert "($X_start+" in text
    assert "($Y_start+" in text
    assert "($Z_print+" in text


def test_axis_and_printhead_are_configurable():
    cfg = Automation1Config(axis_z="U", printhead="Bb")
    text = write_automation1_gcode(_sample_ordered(), cfg)
    assert "DriveBrakeOff(Bb)" in text
    assert "DriveBrakeOn(Bb)" in text
    # motion uses the configured axis name
    assert " U (" in text or "U ($Z_print+" in text
