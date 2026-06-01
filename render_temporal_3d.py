"""Render the bunny toolpaths as an interactive 3D Plotly scene, colored by
deposition order (batlow as the temporal axis), exported to a standalone HTML.

Usage:
    python render_temporal_3d.py [input.ply] [output.html]
"""

import plotly.graph_objects as go
from cmcrameri import cm as cmc

from embedslicer.main import run


def batlow_plotly_scale(n=256):
    scale = []
    for k in range(n):
        r, g, b, _ = cmc.batlow(k / (n - 1))
        scale.append([k / (n - 1), f"rgb({int(255 * r)},{int(255 * g)},{int(255 * b)})"])
    return scale


def build_figure(input_path, line_width=0.4, min_branch_layers=3, flip=False):
    _, _, ordered = run(
        input_path,
        output="/tmp/_render.gcode",
        flip=flip,
        layer_height=0.2,
        line_width=line_width,
        perimeters=2,
        min_island_area=0.2,
        min_branch_layers=min_branch_layers,
    )
    n = len(ordered)
    colorscale = batlow_plotly_scale()

    xs, ys, zs, cs = [], [], [], []
    for i, (z, path) in enumerate(ordered):
        loop = path.points + [path.points[0]]  # close the loop
        for x, y in loop:
            xs.append(x)
            ys.append(y)
            zs.append(z)
            cs.append(i)
        # break the line between separate paths (None coords create a gap;
        # the color array must stay all-numeric, so reuse i as a placeholder)
        xs.append(None)
        ys.append(None)
        zs.append(None)
        cs.append(i)

    paths_trace = go.Scatter3d(
        x=xs,
        y=ys,
        z=zs,
        mode="lines",
        line=dict(color=cs, colorscale=colorscale, width=3, cmin=0, cmax=n),
        hoverinfo="skip",
        name="toolpaths",
    )

    # hidden trace that carries a visible colorbar (deposition order)
    cx = [v for v in xs if v is not None]
    cy = [v for v in ys if v is not None]
    cz = [v for v in zs if v is not None]
    center = [sum(cx) / len(cx), sum(cy) / len(cy), sum(cz) / len(cz)]
    colorbar_trace = go.Scatter3d(
        x=[center[0], center[0]],
        y=[center[1], center[1]],
        z=[center[2], center[2]],
        mode="markers",
        marker=dict(
            size=0.1,
            opacity=0.0,
            color=[0, n],
            colorscale=colorscale,
            cmin=0,
            cmax=n,
            showscale=True,
            colorbar=dict(title="deposition<br>order"),
        ),
        hoverinfo="skip",
        showlegend=False,
    )

    fig = go.Figure(data=[paths_trace, colorbar_trace])
    fig.update_layout(
        title="Bunny toolpaths colored by deposition order (batlow temporal axis)",
        scene=dict(
            xaxis_title="X (mm)",
            yaxis_title="Y (mm)",
            zaxis_title="Z height (mm)",
            aspectmode="data",
        ),
        margin=dict(l=0, r=0, t=40, b=0),
    )
    return fig


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("input", nargs="?", default="bunny.ply")
    p.add_argument("output", nargs="?", default="bunny_3d.html")
    p.add_argument("--line-width", type=float, default=0.4)
    p.add_argument("--min-branch-layers", type=int, default=3)
    p.add_argument("--flip", action="store_true")
    a = p.parse_args()
    fig = build_figure(a.input, line_width=a.line_width, min_branch_layers=a.min_branch_layers, flip=a.flip)
    fig.write_html(a.output, include_plotlyjs=True, full_html=True)
    print(f"wrote {a.output}")


if __name__ == "__main__":
    main()
