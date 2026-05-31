"""Interactive 3D Plotly view with a TIME SLIDER (and play/pause).

Scrub the slider to a time point and see the deposited-so-far toolpath plus a
marker at the current nozzle position. A faint ghost of the whole print (batlow,
deposition order) gives context. Exported to a standalone HTML.

Usage:
    python render_temporal_slider.py [input.ply] [output.html]
"""

import sys

import numpy as np
import plotly.graph_objects as go
from cmcrameri import cm as cmc

from embedslicer.main import run

N_STEPS = 80          # slider checkpoints
MAX_DRAWN_POINTS = 4500  # cap geometry so the HTML stays light
PRINT_FEEDRATE = 600.0   # mm/min (extruding)
TRAVEL_FEEDRATE = 1800.0  # mm/min (repositioning)


def _batlow_scale(n=256):
    out = []
    for k in range(n):
        r, g, b, _ = cmc.batlow(k / (n - 1))
        out.append([k / (n - 1), f"rgb({int(255 * r)},{int(255 * g)},{int(255 * b)})"])
    return out


def _downsample(loop, stride):
    if stride <= 1 or len(loop) <= 3:
        return loop
    kept = loop[::stride]
    if kept[-1] != loop[-1]:
        kept = kept + [loop[-1]]
    return kept


def _mmss(seconds):
    m, s = divmod(int(round(seconds)), 60)
    return f"{m:d}:{s:02d}"


def build_sequence(ordered):
    """Flatten deposition into per-vertex arrays with cumulative time (seconds).

    None coords mark travel gaps (not drawn). Time accounts for print vs travel
    feedrate. Returns xs, ys, zs (with None gaps) and tcum (numeric, monotonic).
    """
    total_pts = sum(len(p.points) + 1 for _, p in ordered)
    stride = max(1, total_pts // MAX_DRAWN_POINTS)
    pf = PRINT_FEEDRATE / 60.0
    tf = TRAVEL_FEEDRATE / 60.0

    xs, ys, zs, tcum = [], [], [], []
    t = 0.0
    prev = None
    for z, path in ordered:
        loop = _downsample(path.points + [path.points[0]], stride)
        x0, y0 = loop[0]
        if prev is not None:
            d = float(np.linalg.norm(np.array([x0, y0, z]) - np.array(prev)))
            t += d / tf
            xs.append(None); ys.append(None); zs.append(None); tcum.append(t)
        xs.append(x0); ys.append(y0); zs.append(z); tcum.append(t)
        for (ax, ay), (bx, by) in zip(loop, loop[1:]):
            t += float(np.hypot(bx - ax, by - ay)) / pf
            xs.append(bx); ys.append(by); zs.append(z); tcum.append(t)
        prev = (loop[-1][0], loop[-1][1], z)
    return xs, ys, zs, np.array(tcum), t


def build_figure(input_path):
    _, _, ordered = run(input_path, output="/tmp/_slider.gcode")
    xs, ys, zs, tcum, total = build_sequence(ordered)
    scale = _batlow_scale()

    # static faint ghost of the full print (batlow by time)
    ghost = go.Scatter3d(
        x=xs, y=ys, z=zs, mode="lines",
        line=dict(color=list(tcum), colorscale=scale, width=2, cmin=0, cmax=total),
        opacity=0.25, hoverinfo="skip", name="full print",
    )

    def reveal(thr):
        k = int(np.searchsorted(tcum, thr, side="right"))
        k = max(k, 1)
        rx, ry, rz = xs[:k], ys[:k], zs[:k]
        # current nozzle position = last non-None revealed vertex
        cx = cy = cz = None
        for j in range(k - 1, -1, -1):
            if xs[j] is not None:
                cx, cy, cz = xs[j], ys[j], zs[j]
                break
        return rx, ry, rz, cx, cy, cz

    def traces_for(thr):
        rx, ry, rz, cx, cy, cz = reveal(thr)
        done = go.Scatter3d(
            x=rx, y=ry, z=rz, mode="lines",
            line=dict(color="#1f3b73", width=4), hoverinfo="skip", name="deposited",
        )
        head = go.Scatter3d(
            x=[cx], y=[cy], z=[cz], mode="markers",
            marker=dict(size=5, color="crimson"), hoverinfo="skip", name="nozzle",
        )
        return [done, head]

    thresholds = [total * s / N_STEPS for s in range(N_STEPS + 1)]
    init = traces_for(thresholds[-1])
    frames = [
        go.Frame(data=traces_for(thr), traces=[1, 2], name=str(s))
        for s, thr in enumerate(thresholds)
    ]
    steps = [
        dict(method="animate", label=_mmss(thr),
             args=[[str(s)], dict(mode="immediate",
                                  frame=dict(duration=0, redraw=True),
                                  transition=dict(duration=0))])
        for s, thr in enumerate(thresholds)
    ]

    fig = go.Figure(data=[ghost, init[0], init[1]], frames=frames)
    fig.update_layout(
        title=f"Bunny print over time (total ~{_mmss(total)} at {PRINT_FEEDRATE:.0f}/{TRAVEL_FEEDRATE:.0f} mm/min)",
        scene=dict(xaxis_title="X (mm)", yaxis_title="Y (mm)", zaxis_title="Z (mm)", aspectmode="data"),
        margin=dict(l=0, r=0, t=40, b=0),
        sliders=[dict(active=N_STEPS, currentvalue=dict(prefix="elapsed time  "), steps=steps, pad=dict(t=40))],
        updatemenus=[dict(type="buttons", showactive=False, x=0.0, y=0.0, xanchor="right", yanchor="top",
            buttons=[
                dict(label="Play", method="animate",
                     args=[None, dict(frame=dict(duration=120, redraw=True), fromcurrent=True, transition=dict(duration=0))]),
                dict(label="Pause", method="animate",
                     args=[[None], dict(mode="immediate", frame=dict(duration=0, redraw=False), transition=dict(duration=0))]),
            ])],
    )
    return fig


def main():
    input_path = sys.argv[1] if len(sys.argv) > 1 else "bunny.ply"
    output_html = sys.argv[2] if len(sys.argv) > 2 else "bunny_time_slider.html"
    fig = build_figure(input_path)
    fig.write_html(output_html, include_plotlyjs=True, full_html=True, auto_play=False)
    print(f"wrote {output_html}")


if __name__ == "__main__":
    main()
