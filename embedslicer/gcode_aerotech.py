"""Aerotech single-material G-code writer for embedded-printing toolpaths.

Mirrors the single-material patterns in xcavate.io.gcode.aerotech:
- header: DVAR + VELOCITY ON + ROUNDING ON + G90
- first pass: G92 -> Enable -> BRAKE 0 -> DWELL -> G1
- subsequent pass: G90 -> BRAKE 1 -> travel XY -> drop Z -> Enable ->
  G91 -> BRAKE 0 -> DWELL -> G90 -> G1
- pass end: Enable -> G91 -> DWELL -> BRAKE 1 -> relative lift -> G90 ->
  return to network_top
- footer: G90 -> park above container -> M2

Each closed-loop path in the deposition sequence becomes one Aerotech pass.
"""

from dataclasses import dataclass


@dataclass
class AerotechConfig:
    """Defaults match xcavate.config (single-material Aerotech setup)."""

    axis_z: str = "A"             # Aerotech Z-axis name (xcavate's axis_1)
    printhead: str = "Aa"         # printhead designator (xcavate's printhead_1)
    dwell_start: float = 0.08     # seconds, brake-release dwell
    dwell_end: float = 0.08       # seconds, end-of-pass dwell
    initial_lift: float = 0.5     # mm, relative lift after a pass
    amount_up: float = 10.0       # mm above container at footer
    container_height: float = 0.0 # mm, bath surface (top of container)
    jog_speed: float = 5.0        # mm/s, between-pass moves
    jog_speed_lift: float = 0.25  # mm/s, initial relative lift
    print_feedrate: float = 1.0   # mm/s along extrusion path
    num_decimals: int = 4


def _f(v, nd):
    return f"{round(float(v), nd):.{nd}f}"


def write_aerotech_gcode(ordered, config=None):
    """Return Aerotech G-code text for an ordered list of (z, Path)."""
    cfg = config or AerotechConfig()
    nd = cfg.num_decimals
    out = []

    out.append(";=========== Begin GCODE ============= ")
    out.append("DVAR $AP, $COM,$hFile,$press,$length,$lame,$cCheck ")
    out.append("VELOCITY ON ")
    out.append("ROUNDING ON ")
    out.append("G90 ")

    # network_top: highest Z plus a safety margin (mirrors xcavate's return-to-top).
    paths = [(z, p) for z, p in ordered if p.points]
    if not paths:
        out.append("G90 ")
        out.append(f"G1 {cfg.axis_z}{_f(cfg.container_height + cfg.amount_up, nd)} ")
        out.append("M2 ")
        return "\n".join(out) + "\n"

    z_max = max(z for z, _ in paths)
    network_top = round(z_max + cfg.initial_lift, nd)
    fp = _f(cfg.print_feedrate, nd)
    fj = _f(cfg.jog_speed, nd)
    fl = _f(cfg.jog_speed_lift, nd)

    def first_pass_start(x, y, z):
        out.append("; Print Pass 0 ")
        out.append(f"G92 X{_f(x, nd)} Y{_f(y, nd)} {cfg.axis_z}{_f(z, nd)} ")
        out.append(f"Enable {cfg.printhead} ")
        out.append(f"G90 F{fp} ")
        out.append(f"BRAKE {cfg.printhead} 0 ")
        out.append(f"DWELL {cfg.dwell_start} ")
        # the trailing G1 in first-pass-start has no trailing space (matches xcavate)
        out.append(f"G1 X{_f(x, nd)} Y{_f(y, nd)} {cfg.axis_z}{_f(z, nd)} F{fp}")

    def subsequent_pass_start(idx, x, y, z):
        out.append(f"; Print pass {idx} ")
        out.append("G90 ")
        out.append(f"BRAKE {cfg.printhead} 1 ")
        out.append(f"G1 X{_f(x, nd)} Y{_f(y, nd)} ")
        out.append("G90 ")
        out.append(f"G1 X{_f(x, nd)} Y{_f(y, nd)} {cfg.axis_z}{_f(z, nd)}")
        out.append(f"Enable {cfg.printhead} ")
        out.append("G91 ")
        out.append(f"BRAKE {cfg.printhead} 0 ")
        out.append(f"DWELL {cfg.dwell_start} ")
        out.append("G90 ")
        out.append(f"G1 X{_f(x, nd)} Y{_f(y, nd)} {cfg.axis_z}{_f(z, nd)} F{fp}")

    def pass_end():
        out.append(f"Enable {cfg.printhead} ")
        out.append("G91 ")
        out.append(f"DWELL {cfg.dwell_end} ")
        out.append(f"BRAKE {cfg.printhead} 1 ")
        out.append(f"G1 {cfg.axis_z}{_f(cfg.initial_lift, nd)} F{fl} ")
        out.append("G90 ")
        out.append(f"G1 {cfg.axis_z}{_f(network_top, nd)} F{fj} ")

    for i, (z, path) in enumerate(paths):
        x0, y0 = path.points[0]
        if i == 0:
            first_pass_start(x0, y0, z)
        else:
            subsequent_pass_start(i, x0, y0, z)
        # extrude along the loop and close it
        for x, y in path.points[1:]:
            out.append(f"G1 X{_f(x, nd)} Y{_f(y, nd)} {cfg.axis_z}{_f(z, nd)} F{fp}")
        out.append(f"G1 X{_f(x0, nd)} Y{_f(y0, nd)} {cfg.axis_z}{_f(z, nd)} F{fp}")
        pass_end()

    out.append("G90 ")
    out.append(f"G1 {cfg.axis_z}{_f(cfg.container_height + cfg.amount_up, nd)} ")
    out.append("M2 ")
    return "\n".join(out) + "\n"
