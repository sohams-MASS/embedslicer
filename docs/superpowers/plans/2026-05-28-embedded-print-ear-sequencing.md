# Embedded-Printing Slicer with Branch-Sequential Ordering — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Slice `bunny.ply` for embedded printing into a `StartExtrusion`/`StopExtrusion` toolpath that prints the body bottom-up, then each ear branch to completion one at a time, eliminating per-layer hops between the ears.

**Architecture:** A small Python package `embedslicer` with a strict pipeline — `mesh` (load/orient) → `slicer` (planar cross-sections → islands) → `regions` (link islands across layers, find branch splits) → `toolpath` (perimeter loops) → `sequencer` (emit in branch order) → `gcode` (toggle-extrusion output). A `main` CLI wires it together; `preview` renders a top-view sanity image.

**Tech Stack:** Python 3.13, trimesh (mesh + planar `section`), shapely (polygon offsetting), numpy, scipy + rtree (trimesh deps), matplotlib (preview), pytest. Run everything from the project `.venv`.

**Spec:** `docs/superpowers/specs/2026-05-28-embedded-print-ear-sequencing-design.md`

**Note on git:** this folder is not yet a git repo. Task 1 runs `git init` so the per-task `git commit` steps work. All commands assume the `.venv` is active (`source .venv/bin/activate`).

---

### Task 1: Project scaffold, editable install, and the synthetic Y-mesh fixture

**Files:**
- Create: `pyproject.toml`
- Create: `embedslicer/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/test_smoke.py`

- [ ] **Step 1: Initialize git (folder is not yet a repo)**

Run:
```bash
git init && printf '%s\n' '.venv/' '__pycache__/' '*.pyc' 'out.gcode' '*.png' > .gitignore
```
Expected: "Initialized empty Git repository …"

- [ ] **Step 2: Create `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"

[project]
name = "embedslicer"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = ["trimesh", "shapely", "numpy", "scipy", "rtree", "matplotlib"]

[tool.setuptools.packages.find]
include = ["embedslicer*"]
```

- [ ] **Step 3: Create the package and test package init files**

`embedslicer/__init__.py`:
```python
"""Embedded-printing slicer with branch-sequential ordering."""
```

`tests/__init__.py`:
```python
```

- [ ] **Step 4: Install (editable) + pytest into the venv**

Run:
```bash
source .venv/bin/activate && pip install -e . --quiet && pip install pytest --quiet && echo OK
```
Expected: `OK` (trimesh/shapely/etc. already present; this adds the editable package + pytest).

- [ ] **Step 5: Create the synthetic Y-mesh fixture in `tests/conftest.py`**

A base slab (z 0–2) with two posts (z 2–8) at x = ±3. Concatenated triangle soup — each box is closed, so `section` at any layer center cuts only the boxes present at that z: one island in the slab band, two islands in the posts band.

```python
import numpy as np
import pytest
import trimesh


@pytest.fixture
def y_mesh():
    """Y-shaped test object: one slab base, two separated posts.

    z in [0,2): single island (slab, 10x4).
    z in [2,8): two islands (posts, 2x2 each at x=-3 and x=+3).
    """
    base = trimesh.creation.box(extents=[10.0, 4.0, 2.0])
    base.apply_translation([0.0, 0.0, 1.0])  # z spans 0..2
    post_l = trimesh.creation.box(extents=[2.0, 2.0, 6.0])
    post_l.apply_translation([-3.0, 0.0, 5.0])  # z spans 2..8, x=-3
    post_r = trimesh.creation.box(extents=[2.0, 2.0, 6.0])
    post_r.apply_translation([3.0, 0.0, 5.0])   # z spans 2..8, x=+3
    return trimesh.util.concatenate([base, post_l, post_r])


@pytest.fixture
def bunny_path():
    import os
    p = os.path.join(os.path.dirname(__file__), "..", "bunny.ply")
    return os.path.abspath(p)
```

- [ ] **Step 6: Create a smoke test `tests/test_smoke.py`**

```python
import embedslicer


def test_package_imports():
    assert embedslicer.__doc__


def test_y_mesh_fixture(y_mesh):
    # bbox: x in [-5,5], z in [0,8]
    assert y_mesh.bounds[1][2] == 8.0
    assert y_mesh.bounds[0][2] == 0.0
```

- [ ] **Step 7: Run the smoke tests**

Run: `pytest tests/test_smoke.py -v`
Expected: 2 passed.

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml embedslicer tests .gitignore
git commit -m "chore: scaffold embedslicer package, deps, and Y-mesh test fixture"
```

---

### Task 2: Data model (`Layer`, `Path`)

**Files:**
- Create: `embedslicer/model.py`
- Test: `tests/test_model.py`

- [ ] **Step 1: Write the failing test**

`tests/test_model.py`:
```python
from shapely.geometry import box

from embedslicer.model import Layer, Path


def test_layer_holds_islands():
    layer = Layer(index=0, z=1.5, islands=[box(0, 0, 1, 1)])
    assert layer.index == 0
    assert layer.z == 1.5
    assert len(layer.islands) == 1


def test_path_points():
    p = Path(points=[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)])
    assert len(p.points) == 3
    assert p.points[0] == (0.0, 0.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_model.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'embedslicer.model'`.

- [ ] **Step 3: Implement `embedslicer/model.py`**

```python
from dataclasses import dataclass, field

from shapely.geometry import Polygon

# A Cell identifies one island: (layer_index, island_index).
Cell = tuple  # tuple[int, int]


@dataclass
class Layer:
    index: int
    z: float
    islands: list  # list[shapely.geometry.Polygon]


@dataclass
class Path:
    """A single closed loop. points are (x, y); closure is implied (first != last)."""

    points: list = field(default_factory=list)  # list[tuple[float, float]]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_model.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add embedslicer/model.py tests/test_model.py
git commit -m "feat: add Layer and Path data model"
```

---

### Task 3: `mesh.load_oriented`

**Files:**
- Create: `embedslicer/mesh.py`
- Test: `tests/test_mesh.py`

- [ ] **Step 1: Write the failing test**

`tests/test_mesh.py`:
```python
import numpy as np

from embedslicer.mesh import load_oriented


def test_load_bunny_default(bunny_path):
    m = load_oriented(bunny_path)
    # as-is bbox (mm): ~15.57 x 12.07 x 15.43
    ext = np.asarray(m.extents)
    assert np.allclose(ext, [15.57, 12.07, 15.43], atol=0.05)


def test_scale_doubles_extents(bunny_path):
    base = np.asarray(load_oriented(bunny_path).extents)
    scaled = np.asarray(load_oriented(bunny_path, scale=2.0).extents)
    assert np.allclose(scaled, base * 2.0, atol=1e-3)


def test_up_axis_y_maps_to_z(bunny_path):
    # Re-orienting Y-up should move the original Y extent onto Z.
    base = np.asarray(load_oriented(bunny_path).extents)  # [x, y, z]
    rot = np.asarray(load_oriented(bunny_path, up_axis="y").extents)
    assert abs(rot[2] - base[1]) < 1e-3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_mesh.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'embedslicer.mesh'`.

- [ ] **Step 3: Implement `embedslicer/mesh.py`**

```python
import numpy as np
import trimesh


def load_oriented(path, scale=1.0, up_axis="z"):
    """Load a mesh, apply uniform scale, and rotate so up_axis maps to +Z."""
    mesh = trimesh.load(path, force="mesh")
    if scale != 1.0:
        mesh.apply_scale(scale)
    axis = up_axis.lower()
    if axis == "z":
        pass
    elif axis == "y":
        # rotate +90 deg about X so original +Y -> +Z
        mesh.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    elif axis == "x":
        # rotate -90 deg about Y so original +X -> +Z
        mesh.apply_transform(trimesh.transformations.rotation_matrix(-np.pi / 2, [0, 1, 0]))
    else:
        raise ValueError(f"up_axis must be x, y, or z; got {up_axis!r}")
    if not mesh.is_watertight:
        print("warning: mesh is not watertight; slicing may produce open contours")
    return mesh
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_mesh.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add embedslicer/mesh.py tests/test_mesh.py
git commit -m "feat: add oriented mesh loader with scale and up-axis"
```

---

### Task 4: `slicer.slice_mesh`

**Files:**
- Create: `embedslicer/slicer.py`
- Test: `tests/test_slicer.py`

- [ ] **Step 1: Write the failing test**

`tests/test_slicer.py`:
```python
from embedslicer.slicer import slice_mesh


def test_y_mesh_island_counts(y_mesh):
    layers = slice_mesh(y_mesh, layer_height=0.5, min_island_area=0.1)
    # z centers: 0.25, 0.75, ... 7.75  -> 16 layers
    assert len(layers) == 16
    # slab band (z < 2): single island
    slab = [l for l in layers if l.z < 2.0]
    assert all(len(l.islands) == 1 for l in slab)
    # posts band (z > 2): two islands
    posts = [l for l in layers if l.z > 2.0]
    assert all(len(l.islands) == 2 for l in posts)


def test_min_island_area_filters_tiny(y_mesh):
    # absurdly high min area drops everything
    layers = slice_mesh(y_mesh, layer_height=0.5, min_island_area=1e6)
    assert all(len(l.islands) == 0 for l in layers)


def test_layers_sorted_bottom_up(y_mesh):
    layers = slice_mesh(y_mesh, layer_height=0.5, min_island_area=0.1)
    zs = [l.z for l in layers]
    assert zs == sorted(zs)
    assert [l.index for l in layers] == list(range(len(layers)))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_slicer.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'embedslicer.slicer'`.

- [ ] **Step 3: Implement `embedslicer/slicer.py`**

```python
import warnings

import numpy as np

from .model import Layer


def _iter_polys(geom):
    if geom is None or geom.is_empty:
        return
    if geom.geom_type == "Polygon":
        yield geom
    elif geom.geom_type == "MultiPolygon":
        for g in geom.geoms:
            yield g


def slice_mesh(mesh, layer_height, min_island_area=0.0):
    """Slice along +Z into planar layers. Each layer is a list of island polygons."""
    z_min, z_max = float(mesh.bounds[0][2]), float(mesh.bounds[1][2])
    n = int(np.ceil((z_max - z_min) / layer_height))
    layers = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i in range(n):
            z = z_min + layer_height * (i + 0.5)
            islands = []
            section = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
            if section is not None:
                planar, _ = section.to_2D()
                for poly in _iter_polys(planar.polygons_full):
                    if poly.area >= min_island_area:
                        islands.append(poly)
            layers.append(Layer(index=i, z=z, islands=islands))
    return layers
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_slicer.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add embedslicer/slicer.py tests/test_slicer.py
git commit -m "feat: add planar Z-slicer producing per-layer island polygons"
```

---

### Task 5: `regions.build_plan` (branch tracking — the heart)

**Files:**
- Create: `embedslicer/regions.py`
- Test: `tests/test_regions.py`

- [ ] **Step 1: Write the failing test**

`tests/test_regions.py`:
```python
from embedslicer.regions import build_plan
from embedslicer.slicer import slice_mesh


def _x_of(plan, group_idx, layers):
    # centroid x of the lowest island in a group
    cells = sorted(plan[group_idx], key=lambda c: c[0])
    li, ii = cells[0]
    return layers[li].islands[ii].centroid.x


def test_y_mesh_gives_trunk_plus_two_branches(y_mesh):
    layers = slice_mesh(y_mesh, layer_height=0.5, min_island_area=0.1)
    plan = build_plan(layers, min_branch_layers=3)
    assert len(plan) == 3  # trunk + left ear + right ear

    trunk = plan[0]
    # trunk = slab band, all island index 0, layers 0..3
    assert sorted({li for li, _ in trunk}) == [0, 1, 2, 3]

    # branches ordered left (x=-3) then right (x=+3)
    assert _x_of(plan, 1, layers) < 0 < _x_of(plan, 2, layers)
    # each branch spans the 12 post layers
    assert len(plan[1]) == 12
    assert len(plan[2]) == 12


def test_min_branch_layers_suppresses_split(y_mesh):
    layers = slice_mesh(y_mesh, layer_height=0.5, min_island_area=0.1)
    # require longer persistence than the posts have -> no split, single group
    plan = build_plan(layers, min_branch_layers=99)
    assert len(plan) == 1


def test_each_group_is_bottom_up(y_mesh):
    layers = slice_mesh(y_mesh, layer_height=0.5, min_island_area=0.1)
    plan = build_plan(layers, min_branch_layers=3)
    for group in plan:
        layer_indices = [li for li, _ in group]
        assert layer_indices == sorted(layer_indices)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_regions.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'embedslicer.regions'`.

- [ ] **Step 3: Implement `embedslicer/regions.py`**

```python
from collections import deque


def _build_adjacency(layers, area_eps=1e-9):
    """Undirected graph: island in layer L links to overlapping island in layer L-1."""
    nodes = []
    adj = {}
    for li, layer in enumerate(layers):
        for ii in range(len(layer.islands)):
            node = (li, ii)
            nodes.append(node)
            adj.setdefault(node, set())
    for li in range(1, len(layers)):
        for ii, a in enumerate(layers[li].islands):
            for jj, b in enumerate(layers[li - 1].islands):
                if a.intersects(b):
                    inter = a.intersection(b)
                    if not inter.is_empty and inter.area > area_eps:
                        u, v = (li, ii), (li - 1, jj)
                        adj[u].add(v)
                        adj[v].add(u)
    return nodes, adj


def _components(subset, adj):
    subset = set(subset)
    seen = set()
    comps = []
    for start in subset:
        if start in seen:
            continue
        comp = []
        queue = deque([start])
        seen.add(start)
        while queue:
            node = queue.popleft()
            comp.append(node)
            for nb in adj[node]:
                if nb in subset and nb not in seen:
                    seen.add(nb)
                    queue.append(nb)
        comps.append(comp)
    return comps


def _span(comp):
    levels = [li for li, _ in comp]
    return max(levels) - min(levels) + 1


def _base_centroid_x(comp, layers):
    li = min(level for level, _ in comp)
    ii = next(i for level, i in comp if level == li)
    return layers[li].islands[ii].centroid.x


def build_plan(layers, min_branch_layers=3):
    """Return an ordered list of region groups (each a bottom-up list of cells).

    Trunk printed first, then each branch fully one at a time. Recurses for
    nested splits. A split counts only if >=2 resulting branches each persist
    for >= min_branch_layers layers.
    """
    nodes, adj = _build_adjacency(layers)
    return _plan(set(nodes), adj, layers, min_branch_layers)


def _plan(nodes, adj, layers, k):
    if not nodes:
        return []
    present = sorted({li for li, _ in nodes})
    for s in present:
        upper = {n for n in nodes if n[0] >= s}
        comps = _components(upper, adj)
        big = [c for c in comps if _span(c) >= k]
        if len(big) >= 2:
            trunk = sorted((n for n in nodes if n[0] < s), key=lambda n: n[0])
            branches = [set(c) for c in big]
            # attach any small leftover components to the nearest branch (by base x)
            for c in (c for c in comps if _span(c) < k):
                cx = _base_centroid_x(c, layers)
                nearest = min(
                    range(len(branches)),
                    key=lambda i: abs(_base_centroid_x(list(branches[i]), layers) - cx),
                )
                branches[nearest].update(c)
            branches.sort(key=lambda b: _base_centroid_x(list(b), layers))
            result = []
            if trunk:
                result.append(trunk)
            for b in branches:
                result.extend(_plan(set(b), adj, layers, k))
            return result
    return [sorted(nodes, key=lambda n: n[0])]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_regions.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add embedslicer/regions.py tests/test_regions.py
git commit -m "feat: add branch-tracking region planner (trunk then sequential branches)"
```

---

### Task 6: `toolpath.generate_perimeters`

**Files:**
- Create: `embedslicer/toolpath.py`
- Test: `tests/test_toolpath.py`

- [ ] **Step 1: Write the failing test**

`tests/test_toolpath.py`:
```python
from shapely.geometry import Polygon, box

from embedslicer.toolpath import generate_perimeters


def _bbox_size(path):
    xs = [p[0] for p in path.points]
    ys = [p[1] for p in path.points]
    return (max(xs) - min(xs), max(ys) - min(ys))


def test_two_perimeters_offset_inward():
    sq = box(0, 0, 10, 10)
    paths = generate_perimeters(sq, line_width=1.0, perimeters=2)
    assert len(paths) == 2
    w0, _ = _bbox_size(paths[0])
    w1, _ = _bbox_size(paths[1])
    assert abs(w0 - 9.0) < 1e-6   # first loop inset by line_width/2
    assert abs(w1 - 7.0) < 1e-6   # second loop inset by 3*line_width/2


def test_buffer_empty_stops_early():
    sq = box(0, 0, 1, 1)
    # 5 requested, but a 1x1 square can't hold that many 1mm-wide loops
    paths = generate_perimeters(sq, line_width=1.0, perimeters=5)
    assert 0 < len(paths) < 5


def test_holes_produce_inner_loops():
    outer = [(0, 0), (10, 0), (10, 10), (0, 10)]
    hole = [(4, 4), (6, 4), (6, 6), (4, 6)]
    poly = Polygon(outer, [hole])
    paths = generate_perimeters(poly, line_width=1.0, perimeters=1)
    # one exterior + one interior ring
    assert len(paths) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_toolpath.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'embedslicer.toolpath'`.

- [ ] **Step 3: Implement `embedslicer/toolpath.py`**

```python
from .model import Path


def _iter_polys(geom):
    if geom is None or geom.is_empty:
        return
    if geom.geom_type == "Polygon":
        yield geom
    elif geom.geom_type == "MultiPolygon":
        for g in geom.geoms:
            yield g


def _ring_to_path(ring):
    coords = list(ring.coords)
    if len(coords) > 1 and coords[0] == coords[-1]:
        coords = coords[:-1]
    return Path(points=[(float(x), float(y)) for x, y in coords])


def generate_perimeters(polygon, line_width, perimeters):
    """Return inward-offset perimeter loops (exterior + any interior rings)."""
    paths = []
    for i in range(perimeters):
        offset = -line_width * (i + 0.5)
        shrunk = polygon.buffer(offset, join_style=2)  # 2 = mitre
        if shrunk.is_empty:
            break
        for poly in _iter_polys(shrunk):
            paths.append(_ring_to_path(poly.exterior))
            for interior in poly.interiors:
                paths.append(_ring_to_path(interior))
    return paths
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_toolpath.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add embedslicer/toolpath.py tests/test_toolpath.py
git commit -m "feat: add perimeter-loop toolpath generation"
```

---

### Task 7: `sequencer.order_paths`

**Files:**
- Create: `embedslicer/sequencer.py`
- Test: `tests/test_sequencer.py`

- [ ] **Step 1: Write the failing test**

`tests/test_sequencer.py`:
```python
from embedslicer.regions import build_plan
from embedslicer.sequencer import order_paths
from embedslicer.slicer import slice_mesh


def _downward_transitions(ordered, eps=1e-9):
    zs = [z for z, _ in ordered]
    return sum(1 for a, b in zip(zs, zs[1:]) if b < a - eps)


def test_one_downward_transition_for_two_branches(y_mesh):
    layers = slice_mesh(y_mesh, layer_height=0.5, min_island_area=0.1)
    plan = build_plan(layers, min_branch_layers=3)
    ordered = order_paths(plan, layers, line_width=0.4, perimeters=1)
    # trunk up, ear A up, ONE drop to ear B base, ear B up -> exactly one down step
    assert _downward_transitions(ordered) == 1


def test_paths_follow_plan_group_order(y_mesh):
    layers = slice_mesh(y_mesh, layer_height=0.5, min_island_area=0.1)
    plan = build_plan(layers, min_branch_layers=3)
    ordered = order_paths(plan, layers, line_width=0.4, perimeters=1)
    # every emitted path has at least 3 points (a rectangle loop)
    assert all(len(path.points) >= 3 for _, path in ordered)
    # total paths == total cells (1 perimeter loop per island here)
    total_cells = sum(len(g) for g in plan)
    assert len(ordered) == total_cells
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_sequencer.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'embedslicer.sequencer'`.

- [ ] **Step 3: Implement `embedslicer/sequencer.py`**

```python
from .toolpath import generate_perimeters


def order_paths(plan, layers, line_width, perimeters):
    """Flatten the region plan into an ordered list of (z, Path).

    Groups are emitted in plan order; within a group, cells bottom-up. This is
    the single point that enforces branch-sequential (anti-streak) ordering.
    """
    ordered = []
    for group in plan:
        for li, ii in group:
            z = layers[li].z
            polygon = layers[li].islands[ii]
            for path in generate_perimeters(polygon, line_width, perimeters):
                ordered.append((z, path))
    return ordered
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_sequencer.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add embedslicer/sequencer.py tests/test_sequencer.py
git commit -m "feat: add sequencer enforcing branch-sequential path order"
```

---

### Task 8: `gcode.write_gcode`

**Files:**
- Create: `embedslicer/gcode.py`
- Test: `tests/test_gcode.py`

- [ ] **Step 1: Write the failing test**

`tests/test_gcode.py`:
```python
from embedslicer.gcode import write_gcode
from embedslicer.model import Path


def _sample_ordered():
    # two loops at two different z heights
    return [
        (0.5, Path(points=[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)])),
        (1.0, Path(points=[(5.0, 5.0), (6.0, 5.0), (6.0, 6.0), (5.0, 6.0)])),
    ]


def test_matched_extrusion_toggles():
    text = write_gcode(_sample_ordered())
    lines = text.splitlines()
    assert lines.count("StartExtrusion") == lines.count("StopExtrusion") == 2


def test_extrusion_never_nested_and_off_during_travel():
    text = write_gcode(_sample_ordered())
    extruding = False
    for ln in text.splitlines():
        if ln == "StartExtrusion":
            assert not extruding  # no nesting
            extruding = True
        elif ln == "StopExtrusion":
            assert extruding
            extruding = False
    assert not extruding  # ends closed


def test_header_and_feedrates_present():
    text = write_gcode(_sample_ordered(), print_feedrate=600, travel_feedrate=1800)
    assert "G21" in text and "G90" in text
    assert "F600" in text and "F1800" in text
    # the loop returns to its start point (closed)
    assert text.count("StartExtrusion") == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_gcode.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'embedslicer.gcode'`.

- [ ] **Step 3: Implement `embedslicer/gcode.py`**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_gcode.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add embedslicer/gcode.py tests/test_gcode.py
git commit -m "feat: add toggle-extrusion G-code writer"
```

---

### Task 9: `main` CLI + bunny integration test

**Files:**
- Create: `embedslicer/main.py`
- Modify: `pyproject.toml` (add console entry point)
- Test: `tests/test_integration.py`

- [ ] **Step 1: Write the failing integration test**

`tests/test_integration.py`:
```python
import os

from embedslicer.main import run


def _downward_transitions(ordered, eps=1e-3):
    zs = [z for z, _ in ordered]
    return sum(1 for a, b in zip(zs, zs[1:]) if b < a - eps)


def test_bunny_end_to_end(bunny_path, tmp_path):
    out = tmp_path / "bunny.gcode"
    plan, layers, ordered = run(
        bunny_path,
        output=str(out),
        layer_height=0.2,
        line_width=0.4,
        perimeters=2,
        min_island_area=0.2,
        min_branch_layers=3,
    )
    assert out.exists()
    text = out.read_text()
    assert text.count("StartExtrusion") == text.count("StopExtrusion") > 0

    # trunk + (at least) two ear branches
    assert len(plan) >= 3
    # anti-streak: the ears must NOT alternate per layer. A per-layer-hopping
    # slicer would produce one downward Z transition per ear layer (~10+).
    # Branch-sequential printing yields only a couple.
    assert _downward_transitions(ordered) <= 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_integration.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'embedslicer.main'`.

- [ ] **Step 3: Implement `embedslicer/main.py`**

```python
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
    print_feedrate=600.0,
    travel_feedrate=1800.0,
    preview=None,
):
    m = mesh.load_oriented(input_path, scale=scale, up_axis=up_axis)
    layers = slicer.slice_mesh(m, layer_height, min_island_area)
    plan = regions.build_plan(layers, min_branch_layers)
    ordered = sequencer.order_paths(plan, layers, line_width, perimeters)
    text = gcode.write_gcode(ordered, print_feedrate, travel_feedrate)
    with open(output, "w") as f:
        f.write(text)
    print(
        f"layers={len(layers)} regions={len(plan)} "
        f"paths={len(ordered)} -> {output}"
    )
    if preview:
        from . import preview as preview_mod

        preview_mod.render(plan, layers, preview, line_width, perimeters)
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
        print_feedrate=a.print_feedrate,
        travel_feedrate=a.travel_feedrate,
        preview=a.preview,
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Add a console entry point to `pyproject.toml`**

Add this block to `pyproject.toml` (after the `[project]` table):
```toml
[project.scripts]
embedslicer = "embedslicer.main:main"
```
Then re-run the editable install so the entry point registers:
```bash
source .venv/bin/activate && pip install -e . --quiet && echo OK
```

- [ ] **Step 5: Run the integration test**

Run: `pytest tests/test_integration.py -v`
Expected: PASS. (If `regions` count or downward-transition assertions fail, inspect with the preview in Task 10 before adjusting `min_island_area` / `min_branch_layers`.)

- [ ] **Step 6: Commit**

```bash
git add embedslicer/main.py pyproject.toml tests/test_integration.py
git commit -m "feat: add CLI + bunny end-to-end test (anti-streak ear sequencing)"
```

---

### Task 10: `preview` top-view render + full suite

**Files:**
- Create: `embedslicer/preview.py`
- Test: `tests/test_preview.py`

- [ ] **Step 1: Write the failing test**

`tests/test_preview.py`:
```python
import os

from embedslicer.preview import render
from embedslicer.regions import build_plan
from embedslicer.slicer import slice_mesh


def test_render_writes_png(y_mesh, tmp_path):
    layers = slice_mesh(y_mesh, layer_height=0.5, min_island_area=0.1)
    plan = build_plan(layers, min_branch_layers=3)
    out = tmp_path / "preview.png"
    render(plan, layers, str(out), line_width=0.4, perimeters=1)
    assert out.exists() and out.stat().st_size > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_preview.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'embedslicer.preview'`.

- [ ] **Step 3: Implement `embedslicer/preview.py`**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_preview.py -v`
Expected: 1 passed.

- [ ] **Step 5: Generate a real bunny preview and eyeball it**

Run:
```bash
source .venv/bin/activate && embedslicer bunny.ply -o bunny.gcode --preview bunny_preview.png && echo done
```
Expected: prints `layers=… regions=… paths=… -> bunny.gcode` and writes `bunny_preview.png`. Open the PNG: the two ears should be drawn in two distinct colors (separate regions), the body in another.

- [ ] **Step 6: Run the full test suite**

Run: `pytest -v`
Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add embedslicer/preview.py tests/test_preview.py
git commit -m "feat: add top-view region preview renderer"
```

---

## Verification summary (maps to spec guarantees)

- **Guarantee 1 (matched toggles):** `tests/test_gcode.py::test_matched_extrusion_toggles`.
- **Guarantee 2 (no extrusion during travel):** `tests/test_gcode.py::test_extrusion_never_nested_and_off_during_travel`.
- **Guarantee 3 (branches contiguous, not per-layer hops):** `tests/test_sequencer.py::test_one_downward_transition_for_two_branches` (synthetic) and `tests/test_integration.py::test_bunny_end_to_end` (`downward_transitions <= 3`).
- **Branch detection correctness:** `tests/test_regions.py` (trunk + 2 ordered branches; `min_branch_layers` filter).
- **Visual confirmation:** Task 10 Step 5 bunny preview PNG.
