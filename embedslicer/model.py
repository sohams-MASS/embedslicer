from dataclasses import dataclass, field

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
