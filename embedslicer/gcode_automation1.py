"""Automation1 (Aerotech) G-code writer for embedded-printing toolpaths.

Mirrors the single-material structure in xcavate.io.gcode.automation1:
- file is wrapped in `program ... end` with `var $X_start / $Y_start /
  $Z_print / $Z_safe / $jog_speed / $dwell_start / $dwell_end` declarations
- main program calls `print_network(...)` (defined later)
- motion uses variable-relative coordinates: ($X_start+x), ($Y_start+y),
  ($Z_print+z)
- per pass: travel XY -> drop Z -> VelocityBlendingOn() / CornerRoundingOn()
  -> StartExtrusion($dwell_start) -> initial-coord G1 -> loop moves ->
  StopExtrusion($Z_safe, $dwell_end) -> VelocityBlendingOff() /
  CornerRoundingOff() -> return to $Z_safe -> Disable(Y) / Enable(Y)
- StartExtrusion / StopExtrusion are function-defined at file end and wrap
  DriveBrakeOff/On + Dwell + (for stop) lift to $Z_safe.

Each closed-loop path becomes one Automation1 pass.
"""

from dataclasses import dataclass


@dataclass
class Automation1Config:
    """Defaults mirror xcavate.config (single-material Aerotech Automation1)."""

    axis_z: str = "A"             # Z-axis name (xcavate's axis_1)
    printhead: str = "Aa"         # printhead designator (xcavate's printhead_1)
    dwell_start: float = 0.08
    dwell_end: float = 0.08
    initial_lift: float = 0.5
    amount_up: float = 10.0
    container_height: float = 0.0
    jog_speed: float = 5.0        # mm/s
    print_feedrate: float = 1.0   # mm/s along extrusion path
    num_decimals: int = 4


def _f(v, nd):
    return f"{round(float(v), nd):.{nd}f}"


def write_automation1_gcode(ordered, config=None):
    """Return Automation1 program text for an ordered list of (z, Path)."""
    cfg = config or Automation1Config()
    nd = cfg.num_decimals
    out = []

    fp = _f(cfg.print_feedrate, nd)

    # --- top-level program block ---
    out.append("program")
    out.append("      var $X_start as real = 0")
    out.append("      var $Y_start as real = 0")
    out.append("      var $Z_print as real = 0")
    out.append(f"      var $Z_safe as real = $Z_print + {_f(cfg.container_height + cfg.amount_up, nd)}")
    out.append(f"      var $jog_speed as real = {_f(cfg.jog_speed, nd)}")
    out.append(f"      var $dwell_start as real = {_f(cfg.dwell_start, nd)}")
    out.append(f"      var $dwell_end as real = {_f(cfg.dwell_end, nd)}")
    out.append("")
    out.append("      G90")
    out.append("      G1 X $X_start Y $Y_start F 20")
    out.append(f"      G1 {cfg.axis_z} $Z_safe F 10")
    out.append("      ProgramPause()")
    out.append("      print_network($jog_speed, $X_start, $Y_start, $Z_print, $Z_safe, $dwell_start, $dwell_end)")
    out.append("end")
    out.append("")

    # --- print_network function: contains the passes ---
    out.append(
        "function print_network($jog_speed as real, $X_start as real, $Y_start as real, "
        "$Z_print as real, $Z_safe as real, $dwell_start as real, $dwell_end as real)"
    )
    out.append("; Automation1 Aerotech program")
    out.append("")

    paths = [(z, p) for z, p in ordered if p.points]
    for i, (z, path) in enumerate(paths):
        x0, y0 = path.points[0]
        marker = "; Print Pass 0 " if i == 0 else f"; Print pass {i} "
        out.append(marker)
        # travel to XY, then drop Z
        out.append(f"G1 X ($X_start+{_f(x0, nd)}) Y ($Y_start+{_f(y0, nd)}) F $jog_speed")
        out.append(f"G1 {cfg.axis_z} ($Z_print+{_f(z, nd)}) F $jog_speed")
        out.append("VelocityBlendingOn()")
        out.append("CornerRoundingOn()")
        out.append("StartExtrusion($dwell_start)")
        out.append(
            f"G1 X ($X_start+{_f(x0, nd)}) Y ($Y_start+{_f(y0, nd)}) "
            f"{cfg.axis_z} ($Z_print+{_f(z, nd)}) F {fp}"
        )
        # extrude along the loop and close it
        for x, y in path.points[1:]:
            out.append(
                f"G1 X ($X_start+{_f(x, nd)}) Y ($Y_start+{_f(y, nd)}) "
                f"{cfg.axis_z} ($Z_print+{_f(z, nd)}) F {fp}"
            )
        out.append(
            f"G1 X ($X_start+{_f(x0, nd)}) Y ($Y_start+{_f(y0, nd)}) "
            f"{cfg.axis_z} ($Z_print+{_f(z, nd)}) F {fp}"
        )
        # pass end
        out.append("StopExtrusion($Z_safe, $dwell_end)")
        out.append("VelocityBlendingOff()")
        out.append("CornerRoundingOff()")
        out.append(f"G1 {cfg.axis_z} $Z_safe F $jog_speed")
        out.append("Disable(Y)")
        out.append("Enable(Y)")

    # print_network footer
    out.append(f"G1 {cfg.axis_z} $Z_safe F $jog_speed ")
    out.append("")
    out.append("end")
    out.append("")

    # --- StartExtrusion / StopExtrusion functions ---
    out.append("function StartExtrusion($dwell_start as real)")
    out.append(f"      DriveBrakeOff({cfg.printhead})")
    out.append("      Dwell($dwell_start)")
    out.append("end")
    out.append("")
    out.append("function StopExtrusion($Z_safe as real, $dwell_end as real)")
    out.append(f"      DriveBrakeOn({cfg.printhead})")
    out.append("      Dwell($dwell_end)")
    out.append(f"      G1 {cfg.axis_z} $Z_safe F 10")
    out.append("end")
    out.append("")

    return "\n".join(out) + "\n"
