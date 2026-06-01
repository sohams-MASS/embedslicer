import argparse

from . import gcode, gcode_aerotech, gcode_automation1, mesh, regions, sequencer, slicer


def run(
    input_path,
    output="out.gcode",
    scale=1.0,
    up_axis="z",
    flip=False,
    layer_height=0.2,
    line_width=0.4,
    perimeters=2,
    min_island_area=0.2,
    min_branch_layers=3,
    smoothing=0.05,
    print_feedrate=600.0,
    travel_feedrate=1800.0,
    flavor="toggle",
    aerotech_config=None,
    preview=None,
):
    m = mesh.load_oriented(input_path, scale=scale, up_axis=up_axis, flip=flip)
    layers = slicer.slice_mesh(m, layer_height, min_island_area)
    plan = regions.build_plan(layers, min_branch_layers)
    ordered = sequencer.order_paths(plan, layers, line_width, perimeters, smoothing=smoothing)
    if flavor == "aerotech":
        text = gcode_aerotech.write_aerotech_gcode(ordered, aerotech_config)
    elif flavor == "automation1":
        text = gcode_automation1.write_automation1_gcode(ordered, aerotech_config)
    else:
        text = gcode.write_gcode(ordered, print_feedrate, travel_feedrate)
    with open(output, "w") as f:
        f.write(text)
    print(
        f"layers={len(layers)} regions={len(plan)} "
        f"paths={len(ordered)} -> {output}"
    )
    if preview:
        from . import preview as preview_mod

        preview_mod.render(plan, layers, preview, line_width, perimeters, smoothing)
    return plan, layers, ordered


def main(argv=None):
    p = argparse.ArgumentParser(description="Embedded-printing slicer with branch sequencing.")
    p.add_argument("input")
    p.add_argument("-o", "--output", default="out.gcode")
    p.add_argument("--scale", type=float, default=1.0)
    p.add_argument("--up-axis", default="z")
    p.add_argument("--flip", action="store_true", help="flip the mesh upside down (180 deg about X) so ears print first")
    p.add_argument("--layer-height", type=float, default=0.2)
    p.add_argument("--line-width", type=float, default=0.4)
    p.add_argument("--perimeters", type=int, default=2)
    p.add_argument("--min-island-area", type=float, default=0.2)
    p.add_argument("--min-branch-layers", type=int, default=3)
    p.add_argument(
        "--smoothing",
        type=float,
        default=0.05,
        help="contour smoothing tolerance in mm (0 = off; larger = smoother)",
    )
    p.add_argument("--print-feedrate", type=float, default=600.0)
    p.add_argument("--travel-feedrate", type=float, default=1800.0)
    p.add_argument(
        "--flavor",
        choices=["toggle", "aerotech", "automation1"],
        default="toggle",
        help=(
            "G-code flavor: 'toggle' (StartExtrusion/StopExtrusion), "
            "'aerotech' (DVAR + Enable/BRAKE/DWELL passes), "
            "or 'automation1' (program/function wrapper with variable-relative coords)"
        ),
    )
    p.add_argument("--aerotech-axis-z", default="A", help="Aerotech Z-axis name (single-material)")
    p.add_argument("--aerotech-printhead", default="Aa", help="Aerotech printhead designator")
    p.add_argument("--aerotech-print-speed", type=float, default=1.0, help="Aerotech extrusion speed (mm/s)")
    p.add_argument("--aerotech-container-height", type=float, default=0.0, help="Aerotech container/bath surface Z (mm)")
    p.add_argument("--preview", default=None, help="path to write a top-view PNG")
    a = p.parse_args(argv)
    if a.flavor == "aerotech":
        aero_cfg = gcode_aerotech.AerotechConfig(
            axis_z=a.aerotech_axis_z,
            printhead=a.aerotech_printhead,
            print_feedrate=a.aerotech_print_speed,
            container_height=a.aerotech_container_height,
        )
    elif a.flavor == "automation1":
        aero_cfg = gcode_automation1.Automation1Config(
            axis_z=a.aerotech_axis_z,
            printhead=a.aerotech_printhead,
            print_feedrate=a.aerotech_print_speed,
            container_height=a.aerotech_container_height,
        )
    else:
        aero_cfg = None
    run(
        a.input,
        output=a.output,
        scale=a.scale,
        up_axis=a.up_axis,
        flip=a.flip,
        layer_height=a.layer_height,
        line_width=a.line_width,
        perimeters=a.perimeters,
        min_island_area=a.min_island_area,
        min_branch_layers=a.min_branch_layers,
        smoothing=a.smoothing,
        print_feedrate=a.print_feedrate,
        travel_feedrate=a.travel_feedrate,
        flavor=a.flavor,
        aerotech_config=aero_cfg,
        preview=a.preview,
    )


if __name__ == "__main__":
    main()
