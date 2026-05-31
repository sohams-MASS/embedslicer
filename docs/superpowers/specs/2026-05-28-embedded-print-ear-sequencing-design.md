# Embedded-Printing Slicer with Branch-Sequential Ordering — Design

**Date:** 2026-05-28
**Input model:** `bunny.ply` (Stanford bunny; binary little-endian PLY, 34,832 verts / 69,660 faces, single watertight body)

## Problem

We are slicing `bunny.ply` for **embedded 3D printing** (deposition into a support
bath/gel). In embedded printing the nozzle moves *through* the support medium, so
every travel move drags through the bath and through already-deposited material.
Travel moves that hop between disconnected regions leave visible **streaks**.

The bunny is one connected body for the bottom ~80% of its height and then splits
into **two disconnected islands — the ears — from ~80% to ~95% of Z**. A conventional
slicer prints both ear cross-sections on each layer, then steps up, which produces a
nozzle hop *between the two ears on every single layer*. Each hop streaks the bath.

**Goal:** print the shared body bottom-up as normal, then print each ear branch to
completion **one at a time**, so there is exactly **one** travel move between the ears
instead of one per layer.

## Orientation & scale (measured)

- **Up axis = Z** (verified: this is the only axis where a single island splits into
  two persistent islands near the top — the ears).
- Axis-aligned size, units treated as millimeters: **X 15.57 × Y 12.07 × Z 15.43 mm**.
- Bounding cylinder about Z: ~16–17 mm diameter, 15.43 mm tall.

## Parameters (all configurable; defaults shown)

| Parameter        | Default        | Notes                                            |
|------------------|----------------|--------------------------------------------------|
| `up_axis`        | `z`            | Slicing is perpendicular to this axis.           |
| `scale`          | `1.0`          | Uniform scale; 1.0 = treat PLY units as mm.      |
| `layer_height`   | `0.2` mm       | Free parameter. 0.2mm → ~78 layers.              |
| `line_width`     | `0.4` mm       | Perimeter trace width / inward-offset step.      |
| `perimeters`     | `2`            | Number of concentric wall loops per island.      |
| `infill`         | **off**        | Perimeters only, hollow interior (per request).  |
| `print_feedrate` | `600` mm/min   | Speed while extruding (`G1 F`).                  |
| `travel_feedrate`| `1800` mm/min  | Speed during non-extruding moves.                |
| `min_island_area`| `0.2` mm²      | Drop tiny transient islands (scan saw a rare 3rd).|
| `min_branch_layers` | `3`         | A split must persist ≥ this many layers to be a branch. |

## Architecture

A small Python package run from the project venv. Strict pipeline; each module has one
job and a plain-data interface so it can be tested in isolation.

```
bunny.ply
   │  mesh.load_oriented()          -> Trimesh (Z-up, scaled)
   ▼
 [layers]   slicer.slice()          -> list[Layer]; Layer = (z, [Island])
   │                                   Island = shapely Polygon (with holes)
   ▼
 region tree  regions.build_plan()  -> PrintPlan: ordered [RegionGroup]
   │                                   trunk first, then each branch bottom-up
   ▼
 toolpaths  toolpath.generate()     -> per Island: list[Path] (perimeter loops)
   │
   ▼
 ordered   sequencer.order()        -> flat ordered list[Path] following PrintPlan
   │
   ▼
 output    gcode.write()            -> .gcode with StartExtrusion / StopExtrusion
```

### 1. `mesh`
- Load PLY with trimesh. Apply `scale`. Rotate so `up_axis` maps to +Z (no-op for `z`).
- Assert single watertight body; warn (don't fail) if not watertight.

### 2. `slicer`
- For `z` from `z_min + layer_height/2` to `z_max` step `layer_height`, compute the
  planar cross-section (`mesh.section` → `to_2D`).
- Each layer becomes a list of **islands** (shapely Polygons, holes preserved).
- Drop islands with area < `min_island_area`.
- Output: ordered `list[Layer]`, each `Layer = (z_index, z_height, [Island])`.

### 3. `regions` — branch tracking (the heart)
1. **Link** islands between adjacent layers: island *i* in layer *L* connects to island
   *j* in layer *L-1* if their polygons overlap (intersection area > 0).
2. This forms a forest/DAG over all islands; the bottom is a single root island.
3. **Find splits recursively.** Given a connected sub-stack over a z-range, walk
   bottom-up until the islands at some layer fan out into ≥2 groups that never
   re-merge higher up. Everything below that layer is the **trunk** for this segment;
   each group above is a **branch**, recursed into independently.
   - A candidate split is accepted only if each resulting branch persists for
     ≥ `min_branch_layers` (filters 1-layer blips / the rare transient 3rd island).
4. **Emit a `PrintPlan`:** an ordered list of `RegionGroup`s. Ordering rule:
   print a trunk segment bottom-up, then fully print branch A bottom-up to its tip,
   then branch B, etc. Nested splits recurse with the same rule.
   - For the bunny this yields: `[body-trunk, ear-A, ear-B]`.

### 4. `toolpath`
- For each island, generate `perimeters` concentric loops by inward `shapely.buffer`
  at multiples of `line_width` (`-line_width/2`, `-3·line_width/2`, …). Stop when a
  buffer becomes empty.
- Holes are respected (buffering a polygon-with-holes yields valid inner loops).
- No infill (default). Order loops outer→inner; choose loop start points to keep the
  pen-down transition between consecutive loops short.

### 5. `sequencer`
- Walk the `PrintPlan` in order. For each `RegionGroup`, emit its islands' toolpaths
  layer-by-layer bottom-up. A group is fully emitted before the next begins.
- This is the single point that enforces branch-sequential, anti-streak ordering.

### 6. `gcode`
- Header (units mm `G21`, absolute `G90`, optional home), then the ordered paths,
  then footer.
- **Travel** (extrusion off): `G1 X.. Y.. Z.. F<travel_feedrate>` with no extrusion
  command active.
- **Print path:** emit `StartExtrusion`, then `G1` moves along the loop at
  `F<print_feedrate>`, then `StopExtrusion`.
- Z only changes on travel moves between layers (planar layers).

### 7. `main`
- CLI: input path, output path, and the parameter table above (argparse). Wires the
  pipeline and prints a summary (layer count, region count, path count, branch order).

## Anti-streak guarantees (asserted in tests)

1. Every `StartExtrusion` is matched by exactly one following `StopExtrusion`; no
   nesting; no motion-without-state.
2. Extrusion state is **off** during every inter-region and inter-layer travel move.
3. All paths of branch A appear contiguously in the output stream before any path of
   branch B — i.e. exactly one ear↔ear travel transition, not one per layer.

## Testing

- **Synthetic Y-mesh** (two posts on a shared slab): `regions.build_plan` must return
  one trunk + two branches, and the sequencer must emit one branch fully before the
  other. This is the core correctness test, independent of the bunny.
- **Bunny island counts**: assert single island in low layers and exactly two
  persistent islands in the ~80–95% Z band.
- **G-code lint**: parse output, assert the three anti-streak guarantees above.
- **Toolpath preview**: dump per-region paths to an SVG/PNG (and optionally a 3D
  scatter) to visually confirm ears are sequenced and perimeters look right.

## Out of scope (YAGNI)

- Infill patterns, top/bottom solid layers, supports (embedded bath is the support).
- Machine-specific extrusion tuning (volumetric/pressure values) — extrusion is a bare
  `StartExtrusion`/`StopExtrusion` toggle for now.
- Non-planar / conical slicing, seam optimization beyond short loop-to-loop hops.
- A GUI. CLI only.

## Assumptions

- PLY units are millimeters at `scale = 1.0`.
- Planar layers along Z are acceptable for this embedded process (no gravity/overhang
  constraint because the bath supports the part — which is also what makes
  branch-sequential ordering physically valid).
- One travel move down-and-over between the two ears is acceptable (it is unavoidable
  and is the whole point: 1 streak-risk transition instead of ~per-layer).
