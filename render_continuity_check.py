"""Continuity preview: side view + deposition ribbon, plus a text sequence
summary. Each region becomes a contiguous color block in the ribbon if and
only if it is printed without interleaving with any other region.
"""

import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mpatches  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

from embedslicer.main import run  # noqa: E402
from embedslicer.smoothing import smooth_polygon  # noqa: E402
from embedslicer.toolpath import generate_perimeters  # noqa: E402

INPUT = sys.argv[1] if len(sys.argv) > 1 else "bunny.ply"
OUT_PNG = sys.argv[2] if len(sys.argv) > 2 else "bunny_continuity.png"
OUT_TXT = sys.argv[3] if len(sys.argv) > 3 else "bunny_sequence.txt"

LINE_WIDTH = 0.4
PERIMETERS = 2
SMOOTHING = 0.05

plan, layers, ordered = run(
    INPUT, output="/tmp/_continuity.gcode",
    line_width=LINE_WIDTH, perimeters=PERIMETERS, smoothing=SMOOTHING,
)

# Re-derive which group each emitted path belongs to (sequencer order)
group_of_path = []
group_cells = []
for gi, g in enumerate(plan):
    cells_here = 0
    for li, ii in g:
        sm = smooth_polygon(layers[li].islands[ii], SMOOTHING)
        for _ in generate_perimeters(sm, LINE_WIDTH, PERIMETERS):
            group_of_path.append(gi)
        cells_here += 1
    group_cells.append(cells_here)
assert len(group_of_path) == len(ordered)

cmap = plt.get_cmap("tab10")
group_color = [cmap(gi % 10) for gi in range(len(plan))]


def _group_extent(g):
    lis = [li for li, _ in g]
    z0, z1 = layers[min(lis)].z, layers[max(lis)].z
    li, ii = sorted(g, key=lambda c: c[0])[0]
    base = layers[li].islands[ii].centroid
    return z0, z1, base.x, base.y


# Heuristic labels: bottom-most region = body; remaining ordered by base height
# Find the two "ear" regions: same top-z band and disjoint base x/y
extents = [_group_extent(g) for g in plan]
labels = [None] * len(plan)
# tag the body (group containing layer 0)
body_idx = next(i for i, g in enumerate(plan) if any(li == 0 for li, _ in g))
labels[body_idx] = "Body (trunk)"
# tag the two tallest non-body regions as ears, ordered by x
non_body = [i for i in range(len(plan)) if i != body_idx]
non_body_sorted_by_top = sorted(non_body, key=lambda i: -extents[i][1])
ears = sorted(non_body_sorted_by_top[:2], key=lambda i: extents[i][2])
labels[ears[0]] = "Ear A (left)"
labels[ears[1]] = "Ear B (right)"
for i in non_body:
    if labels[i] is None:
        labels[i] = f"Branch {i}"

# ---------- Figure ----------
fig = plt.figure(figsize=(13, 8.5))
gs = fig.add_gridspec(2, 1, height_ratios=[4, 1], hspace=0.32)
ax = fig.add_subplot(gs[0])
ax_rib = fig.add_subplot(gs[1])

for k, (z, path) in enumerate(ordered):
    col = group_color[group_of_path[k]]
    xs = [p[0] for p in path.points] + [path.points[0][0]]
    ax.plot(xs, [z] * len(xs), color=col, lw=0.7)
ax.set_aspect("equal")
ax.set_xlabel("X (mm)")
ax.set_ylabel("Z (mm)")
ax.set_title("Side view — toolpaths colored by print region")
ax.legend(
    handles=[mpatches.Patch(color=group_color[i], label=f"{labels[i]}  ({group_cells[i]} cells)") for i in range(len(plan))],
    loc="upper right", fontsize=8,
)

# Ribbon: deposition order as a horizontal bar; segments = contiguous runs
n = len(ordered)
prev = None
start = 0
runs = []
for k in range(n + 1):
    cur = group_of_path[k] if k < n else None
    if cur != prev:
        if prev is not None:
            runs.append((start, k, prev))
        start = k
        prev = cur
for s, e, gi in runs:
    ax_rib.barh(0, e - s, left=s, color=group_color[gi], edgecolor="white", linewidth=0.5)
    if e - s > n * 0.04:
        ax_rib.text((s + e) / 2, 0, labels[gi], ha="center", va="center", fontsize=8, color="white", weight="bold")
ax_rib.set_yticks([])
ax_rib.set_xlim(0, n)
ax_rib.set_xlabel(f"Deposition order  (path index, 0 → {n})")
ax_rib.set_title("Deposition timeline — one contiguous color block per region = no interleaving")

fig.savefig(OUT_PNG, dpi=150, bbox_inches="tight")
print(f"wrote {OUT_PNG}")

# ---------- Text sequence summary ----------
n_runs_per_group = {gi: 0 for gi in range(len(plan))}
for _, _, gi in runs:
    n_runs_per_group[gi] += 1

with open(OUT_TXT, "w") as f:
    f.write(f"Print sequence for {INPUT}\n")
    f.write("=" * 60 + "\n")
    f.write(f"{len(layers)} layers, {len(plan)} regions, {len(ordered)} paths total\n\n")
    f.write("Region order (as emitted):\n")
    for s, e, gi in runs:
        z0, z1, cx, cy = extents[gi]
        f.write(
            f"  paths {s:4d}–{e-1:<4d}  "
            f"({e-s:3d} paths)  "
            f"{labels[gi]:<14s}  z {z0:6.2f} → {z1:6.2f}  "
            f"base @({cx:5.2f},{cy:5.2f})\n"
        )
    f.write("\nContinuity check (paths per region == number of contiguous runs?):\n")
    counts = {gi: sum(1 for g in group_of_path if g == gi) for gi in range(len(plan))}
    for gi in range(len(plan)):
        cont = "YES" if n_runs_per_group[gi] == 1 else f"NO (split into {n_runs_per_group[gi]} runs)"
        f.write(f"  {labels[gi]:<14s} {counts[gi]:3d} paths in {n_runs_per_group[gi]} run(s) -> continuous: {cont}\n")
print(f"wrote {OUT_TXT}")
