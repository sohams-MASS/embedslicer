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


def _base_layer(comp):
    return min(li for li, _ in comp)


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
            branches.sort(key=lambda b: (_base_layer(list(b)), _base_centroid_x(list(b), layers)))
            result = []
            if trunk:
                result.append(trunk)
            for b in branches:
                result.extend(_plan(set(b), adj, layers, k))
            return result
    return [sorted(nodes, key=lambda n: n[0])]
