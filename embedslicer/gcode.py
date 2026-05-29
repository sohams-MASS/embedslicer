def write_gcode(ordered, print_feedrate=600, travel_feedrate=1800):
    """Emit toggle-extrusion G-code.

    Travel moves run with extrusion OFF; each closed loop is wrapped in
    StartExtrusion / StopExtrusion. Z only changes on travel between layers.
    """
    lines = ["; embedded-print toolpath", "G21", "G90"]
    cur_z = None
    for z, path in ordered:
        if not path.points:
            continue
        x0, y0 = path.points[0]
        if cur_z is None or abs(z - cur_z) > 1e-9:
            lines.append(f"G1 Z{z:.3f} F{travel_feedrate:.0f}")
            cur_z = z
        # travel to loop start (extrusion off)
        lines.append(f"G1 X{x0:.3f} Y{y0:.3f} F{travel_feedrate:.0f}")
        lines.append("StartExtrusion")
        for x, y in path.points[1:]:
            lines.append(f"G1 X{x:.3f} Y{y:.3f} F{print_feedrate:.0f}")
        lines.append(f"G1 X{x0:.3f} Y{y0:.3f} F{print_feedrate:.0f}")  # close loop
        lines.append("StopExtrusion")
    lines.append("; end")
    return "\n".join(lines) + "\n"
