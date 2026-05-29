import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from .toolpath import generate_perimeters  # noqa: E402


def render(plan, layers, out_path, line_width=0.4, perimeters=2):
    """Top-view (XY) plot of all toolpaths, colored by region group."""
    fig, ax = plt.subplots(figsize=(6, 6))
    cmap = plt.get_cmap("tab10")
    for gi, group in enumerate(plan):
        color = cmap(gi % 10)
        for li, ii in group:
            polygon = layers[li].islands[ii]
            for path in generate_perimeters(polygon, line_width, perimeters):
                xs = [p[0] for p in path.points] + [path.points[0][0]]
                ys = [p[1] for p in path.points] + [path.points[0][1]]
                ax.plot(xs, ys, color=color, linewidth=0.4)
    ax.set_aspect("equal")
    ax.set_title("toolpaths colored by region (top view)")
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
