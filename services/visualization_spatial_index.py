"""Renderer-neutral uniform-grid spatial index for visualization primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import floor, isfinite
from typing import Any, Mapping, Sequence

from services.visualization_render_model import RenderPrimitive, VisualizationRenderModel


@dataclass(frozen=True, slots=True)
class PrimitiveBounds:
    """Axis-aligned screen-space bounds for one render primitive."""

    x_min: float
    y_min: float
    x_max: float
    y_max: float

    @property
    def valid(self) -> bool:
        return (
            all(isfinite(value) for value in (self.x_min, self.y_min, self.x_max, self.y_max))
            and self.x_max >= self.x_min
            and self.y_max >= self.y_min
        )

    def intersects(self, other: "PrimitiveBounds") -> bool:
        return not (
            self.x_max < other.x_min
            or self.x_min > other.x_max
            or self.y_max < other.y_min
            or self.y_min > other.y_max
        )

    def expanded(self, amount: float) -> "PrimitiveBounds":
        return PrimitiveBounds(
            self.x_min - amount,
            self.y_min - amount,
            self.x_max + amount,
            self.y_max + amount,
        )


@dataclass(frozen=True, slots=True)
class SpatialIndexStats:
    primitive_count: int
    indexed_primitive_count: int
    bucket_count: int
    cell_size: float
    max_bucket_size: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "primitive_count": self.primitive_count,
            "indexed_primitive_count": self.indexed_primitive_count,
            "bucket_count": self.bucket_count,
            "cell_size": self.cell_size,
            "max_bucket_size": self.max_bucket_size,
        }


@dataclass(slots=True)
class VisualizationSpatialIndex:
    """Reusable uniform-grid index over render-model primitive bounds."""

    cell_size: float = 64.0
    _signature: tuple[Any, ...] = field(default_factory=tuple, init=False, repr=False)
    _bounds: dict[int, PrimitiveBounds] = field(default_factory=dict, init=False, repr=False)
    _buckets: dict[tuple[int, int], tuple[int, ...]] = field(default_factory=dict, init=False, repr=False)
    _primitive_count: int = field(default=0, init=False, repr=False)

    def __post_init__(self) -> None:
        if not isfinite(self.cell_size) or self.cell_size <= 0:
            raise ValueError("cell_size must be a positive finite number")

    @classmethod
    def build(
        cls,
        model: VisualizationRenderModel | Mapping[str, Any],
        *,
        cell_size: float = 64.0,
    ) -> "VisualizationSpatialIndex":
        index = cls(cell_size=cell_size)
        index.rebuild(model)
        return index

    def rebuild(self, model: VisualizationRenderModel | Mapping[str, Any]) -> None:
        render_model = model if isinstance(model, VisualizationRenderModel) else VisualizationRenderModel.from_dict(model)
        mutable_buckets: dict[tuple[int, int], list[int]] = {}
        bounds_by_index: dict[int, PrimitiveBounds] = {}

        for primitive_index, primitive in enumerate(render_model.primitives):
            bounds = primitive_bounds(primitive)
            if bounds is None or not bounds.valid:
                continue
            bounds_by_index[primitive_index] = bounds
            for cell in self._cells_for(bounds):
                mutable_buckets.setdefault(cell, []).append(primitive_index)

        self._bounds = bounds_by_index
        self._buckets = {
            key: tuple(dict.fromkeys(value))
            for key, value in mutable_buckets.items()
        }
        self._primitive_count = len(render_model.primitives)
        self._signature = _model_signature(render_model)

    def compatible_with(self, model: VisualizationRenderModel | Mapping[str, Any]) -> bool:
        render_model = model if isinstance(model, VisualizationRenderModel) else VisualizationRenderModel.from_dict(model)
        return self._signature == _model_signature(render_model)

    def query_point(self, x: float, y: float, tolerance: float = 0.0) -> tuple[int, ...]:
        if not all(isfinite(value) for value in (x, y, tolerance)) or tolerance < 0:
            raise ValueError("query coordinates and tolerance must be finite; tolerance must be non-negative")
        area = PrimitiveBounds(x - tolerance, y - tolerance, x + tolerance, y + tolerance)
        candidate_indexes: set[int] = set()
        for cell in self._cells_for(area):
            candidate_indexes.update(self._buckets.get(cell, ()))
        return tuple(
            index
            for index in sorted(candidate_indexes)
            if self._bounds[index].intersects(area)
        )

    @property
    def stats(self) -> SpatialIndexStats:
        return SpatialIndexStats(
            primitive_count=self._primitive_count,
            indexed_primitive_count=len(self._bounds),
            bucket_count=len(self._buckets),
            cell_size=self.cell_size,
            max_bucket_size=max((len(value) for value in self._buckets.values()), default=0),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "visualization.interactive.spatial-index",
            "version": "1.0",
            "strategy": "uniform-grid",
            "stats": self.stats.to_dict(),
            "renderer_neutral": True,
        }

    def _cells_for(self, bounds: PrimitiveBounds) -> tuple[tuple[int, int], ...]:
        x_start = floor(bounds.x_min / self.cell_size)
        x_stop = floor(bounds.x_max / self.cell_size)
        y_start = floor(bounds.y_min / self.cell_size)
        y_stop = floor(bounds.y_max / self.cell_size)
        return tuple(
            (x_cell, y_cell)
            for x_cell in range(x_start, x_stop + 1)
            for y_cell in range(y_start, y_stop + 1)
        )


def primitive_bounds(primitive: RenderPrimitive) -> PrimitiveBounds | None:
    """Extract conservative screen-space bounds from a supported primitive."""

    payload = primitive.payload
    kind = primitive.kind.lower()

    if kind == "polyline":
        points = _points(payload.get("points"))
        if not points:
            return None
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        return PrimitiveBounds(min(xs), min(ys), max(xs), max(ys))

    if kind == "line":
        x1 = _number(payload.get("x1"), payload.get("x"))
        y1 = _number(payload.get("y1"), payload.get("y"))
        x2 = _number(payload.get("x2"), payload.get("x"))
        y2 = _number(payload.get("y2"), payload.get("y"))
        if None in (x1, y1, x2, y2):
            return None
        return PrimitiveBounds(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))

    if kind == "rectangle":
        x = _number(payload.get("x"))
        y = _number(payload.get("y"))
        width = _number(payload.get("width"))
        height = _number(payload.get("height"))
        if None in (x, y, width, height) or width < 0 or height < 0:
            return None
        return PrimitiveBounds(x, y, x + width, y + height)

    if kind == "text":
        x = _number(payload.get("x"))
        y = _number(payload.get("y"))
        if x is None or y is None:
            return None
        return PrimitiveBounds(x, y, x, y)

    return None


def _model_signature(model: VisualizationRenderModel) -> tuple[Any, ...]:
    return (
        model.schema,
        model.version,
        model.width,
        model.height,
        tuple((item.id, item.kind, item.z_index, item.track_id, item.clip_id, item.visible) for item in model.primitives),
    )


def _points(value: Any) -> tuple[tuple[float, float], ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    result: list[tuple[float, float]] = []
    for item in value:
        if isinstance(item, Mapping):
            x, y = _number(item.get("x")), _number(item.get("y"))
        elif isinstance(item, Sequence) and not isinstance(item, (str, bytes, bytearray)) and len(item) >= 2:
            x, y = _number(item[0]), _number(item[1])
        else:
            continue
        if x is not None and y is not None:
            result.append((x, y))
    return tuple(result)


def _number(*values: Any) -> float | None:
    for value in values:
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if isfinite(number):
            return number
    return None
