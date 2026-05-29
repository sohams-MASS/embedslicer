import argparse

from . import gcode, mesh, regions, sequencer, slicer


def run(
    input_path,
    output="out.gcode",
    scale=1.0,
    up_axis="z",
    layer_height=0.2,
    line_width=0.4,
    perimeters=2,
    min_island_area=0.2,
    min_branch_layers=3,
    smoothing=0.05,
    print_feedrate=600.0,
    travel_feedrate=1800.0,
    preview=None,
):
    m = mesh.load_oriented(input_path, scale=scale, up_axis=up_axis)
    layers = slicer.slice_mesh(m, layer_height, min_island_area)
    plan = regions.build_plan(layers, min_branch_layers)
    ordered = sequencer.order_paths(plan, layers, line_width, perimeters, smoothing=smoothing)
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
    p.add_argument("--preview", default=None, help="path to write a top-view PNG")
    a = p.parse_args(argv)
    run(
        a.input,
        output=a.output,
        scale=a.scale,
        up_axis=a.up_axis,
        layer_height=a.layer_height,
        line_width=a.line_width,
        perimeters=a.perimeters,
        min_island_area=a.min_island_area,
        min_branch_layers=a.min_branch_layers,
        smoothing=a.smoothing,
        print_feedrate=a.print_feedrate,
        travel_feedrate=a.travel_feedrate,
        preview=a.preview,
    )


if __name__ == "__main__":
    main()
