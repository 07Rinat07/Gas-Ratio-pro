"""Renderer-neutral hit testing for Visualization Engine render models.

The engine consumes only :class:`VisualizationRenderModel` primitives (or their
serialized dictionaries). It performs no UI work and exposes deterministic,
serializable hit results suitable for cursor, tooltip and selection adapters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import hypot, isfinite
from typing import Any, Iterable, Mapping, Sequence

from services.visualization_render_model import RenderPrimitive, VisualizationRenderModel
from services.visualization_spatial_index import VisualizationSpatialIndex


_SUPPORTED_KINDS = frozenset({"polyline", "rectangle", "line", "text"})


@dataclass(frozen=True, slots=True)
class HitTestQuery:
    """Screen-space hit-test request."""

    x: float
    y: float
    tolerance: float = 6.0
    track_id: str = ""
    kinds: tuple[str, ...] = field(default_factory=tuple)
    include_hidden: bool = False
    max_results: int = 8

    @property
    def valid(self) -> bool:
        return (
            isfinite(self.x)
            and isfinite(self.y)
            and isfinite(self.tolerance)
            and self.tolerance >= 0
            and self.max_results > 0
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "visualization.interactive.hit-test-query",
            "version": "1.0",
            "x": self.x,
            "y": self.y,
            "tolerance": self.tolerance,
            "track_id": self.track_id,
            "kinds": list(self.kinds),
            "include_hidden": self.include_hidden,
            "max_results": self.max_results,
            "valid": self.valid,
            "renderer_neutral": True,
        }


@dataclass(frozen=True, slots=True)
class HitTestResult:
    """Normalized match between a screen coordinate and one render primitive."""

    primitive_id: str
    primitive_kind: str
    track_id: str
    source_layer_id: str
    data_kind: str
    distance: float
    hit_x: float
    hit_y: float
    query_x: float
    query_y: float
    z_index: int
    segment_index: int | None = None
    point_index: int | None = None
    segment_ratio: float | None = None
    inside: bool = False
    payload: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "HitTestResult":
        return cls(
            primitive_id=str(value.get("primitive_id") or ""),
            primitive_kind=str(value.get("primitive_kind") or ""),
            track_id=str(value.get("track_id") or ""),
            source_layer_id=str(value.get("source_layer_id") or ""),
            data_kind=str(value.get("data_kind") or ""),
            distance=float(value.get("distance") or 0.0),
            hit_x=float(value.get("hit_x") or 0.0),
            hit_y=float(value.get("hit_y") or 0.0),
            query_x=float(value.get("query_x") or 0.0),
            query_y=float(value.get("query_y") or 0.0),
            z_index=int(value.get("z_index") or 0),
            segment_index=_optional_int(value.get("segment_index")),
            point_index=_optional_int(value.get("point_index")),
            segment_ratio=(None if value.get("segment_ratio") is None else float(value["segment_ratio"])),
            inside=bool(value.get("inside", False)),
            payload=dict(value.get("payload") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "primitive_id": self.primitive_id,
            "primitive_kind": self.primitive_kind,
            "track_id": self.track_id,
            "source_layer_id": self.source_layer_id,
            "data_kind": self.data_kind,
            "distance": self.distance,
            "hit_x": self.hit_x,
            "hit_y": self.hit_y,
            "query_x": self.query_x,
            "query_y": self.query_y,
            "z_index": self.z_index,
            "segment_index": self.segment_index,
            "point_index": self.point_index,
            "segment_ratio": self.segment_ratio,
            "inside": self.inside,
            "payload": dict(self.payload),
        }


@dataclass(frozen=True, slots=True)
class HitTestResponse:
    """Serializable deterministic response for one query."""

    query: HitTestQuery
    results: tuple[HitTestResult, ...] = field(default_factory=tuple)
    inspected_primitive_count: int = 0
    candidate_primitive_count: int = 0
    diagnostics: tuple[str, ...] = field(default_factory=tuple)

    @property
    def hit(self) -> bool:
        return bool(self.results)

    @property
    def nearest(self) -> HitTestResult | None:
        return self.results[0] if self.results else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "visualization.interactive.hit-test-response",
            "version": "1.0",
            "query": self.query.to_dict(),
            "results": [item.to_dict() for item in self.results],
            "hit": self.hit,
            "inspected_primitive_count": self.inspected_primitive_count,
            "candidate_primitive_count": self.candidate_primitive_count,
            "diagnostics": list(self.diagnostics),
            "renderer_neutral": True,
        }


class VisualizationHitTestingEngine:
    """Find nearest interactive primitives in a renderer-neutral render model."""

    def hit_test(
        self,
        model: VisualizationRenderModel | Mapping[str, Any],
        query: HitTestQuery,
        spatial_index: VisualizationSpatialIndex | None = None,
    ) -> HitTestResponse:
        if not query.valid:
            raise ValueError("hit-test query is invalid")

        render_model = (
            model if isinstance(model, VisualizationRenderModel)
            else VisualizationRenderModel.from_dict(model)
        )
        clip_regions = {item.id: item for item in render_model.clip_regions}
        requested_kinds = frozenset(item.strip().lower() for item in query.kinds if item.strip())
        diagnostics: list[str] = []
        results: list[HitTestResult] = []
        inspected = 0
        candidates = 0

        if spatial_index is not None:
            if not spatial_index.compatible_with(render_model):
                raise ValueError("spatial index is not compatible with render model")
            primitive_indexes = spatial_index.query_point(query.x, query.y, query.tolerance)
            diagnostics.append("hit_test_spatial_index_used")
        else:
            primitive_indexes = range(len(render_model.primitives))

        for primitive_index in primitive_indexes:
            primitive = render_model.primitives[primitive_index]
            inspected += 1
            if not query.include_hidden and not primitive.visible:
                continue
            if query.track_id and primitive.track_id != query.track_id:
                continue
            kind = primitive.kind.lower()
            if kind not in _SUPPORTED_KINDS:
                continue
            if requested_kinds and kind not in requested_kinds:
                continue
            if primitive.clip_id:
                clip = clip_regions.get(primitive.clip_id)
                if clip is None:
                    diagnostics.append(f"hit_test_missing_clip:{primitive.id}:{primitive.clip_id}")
                    continue
                if not _inside_rectangle(
                    query.x, query.y, clip.x, clip.y, clip.width, clip.height
                ):
                    continue

            candidates += 1
            result = self._hit_primitive(primitive, query)
            if result is not None and result.distance <= query.tolerance:
                results.append(result)

        results.sort(key=lambda item: (item.distance, -item.z_index, item.primitive_id))
        return HitTestResponse(
            query=query,
            results=tuple(results[: query.max_results]),
            inspected_primitive_count=inspected,
            candidate_primitive_count=candidates,
            diagnostics=tuple(dict.fromkeys(diagnostics)),
        )

    def _hit_primitive(
        self,
        primitive: RenderPrimitive,
        query: HitTestQuery,
    ) -> HitTestResult | None:
        payload = primitive.payload
        kind = primitive.kind.lower()
        base = {
            "primitive_id": primitive.id,
            "primitive_kind": kind,
            "track_id": primitive.track_id,
            "source_layer_id": str(payload.get("source_layer_id") or ""),
            "data_kind": str(payload.get("data_kind") or ""),
            "query_x": query.x,
            "query_y": query.y,
            "z_index": primitive.z_index,
            "payload": _interaction_payload(payload),
        }

        if kind == "polyline":
            points = _points(payload.get("points"))
            if not points:
                return None
            if len(points) == 1:
                x, y = points[0]
                return HitTestResult(**base, distance=hypot(query.x - x, query.y - y), hit_x=x, hit_y=y, point_index=0)
            best: tuple[float, float, float, int, float] | None = None
            for index, ((x1, y1), (x2, y2)) in enumerate(zip(points, points[1:])):
                hit_x, hit_y, ratio = _nearest_on_segment(query.x, query.y, x1, y1, x2, y2)
                distance = hypot(query.x - hit_x, query.y - hit_y)
                candidate = (distance, hit_x, hit_y, index, ratio)
                if best is None or candidate[0] < best[0]:
                    best = candidate
            if best is None:
                return None
            distance, hit_x, hit_y, segment_index, ratio = best
            point_index = segment_index if ratio <= 0.5 else segment_index + 1
            return HitTestResult(
                **base,
                distance=distance,
                hit_x=hit_x,
                hit_y=hit_y,
                segment_index=segment_index,
                point_index=point_index,
                segment_ratio=ratio,
            )

        if kind == "line":
            x1 = _number(payload.get("x1"), payload.get("x"))
            y1 = _number(payload.get("y1"), payload.get("y"))
            x2 = _number(payload.get("x2"), payload.get("x"))
            y2 = _number(payload.get("y2"), payload.get("y"))
            if None in (x1, y1, x2, y2):
                return None
            hit_x, hit_y, ratio = _nearest_on_segment(query.x, query.y, x1, y1, x2, y2)
            return HitTestResult(
                **base,
                distance=hypot(query.x - hit_x, query.y - hit_y),
                hit_x=hit_x,
                hit_y=hit_y,
                segment_index=0,
                segment_ratio=ratio,
            )

        if kind == "rectangle":
            x = _number(payload.get("x"))
            y = _number(payload.get("y"))
            width = _number(payload.get("width"))
            height = _number(payload.get("height"))
            if None in (x, y, width, height) or width < 0 or height < 0:
                return None
            hit_x = min(max(query.x, x), x + width)
            hit_y = min(max(query.y, y), y + height)
            inside = x <= query.x <= x + width and y <= query.y <= y + height
            distance = 0.0 if inside else hypot(query.x - hit_x, query.y - hit_y)
            return HitTestResult(**base, distance=distance, hit_x=hit_x, hit_y=hit_y, inside=inside)

        if kind == "text":
            x = _number(payload.get("x"))
            y = _number(payload.get("y"))
            if x is None or y is None:
                return None
            return HitTestResult(**base, distance=hypot(query.x - x, query.y - y), hit_x=x, hit_y=y)

        return None


def _nearest_on_segment(
    px: float, py: float, x1: float, y1: float, x2: float, y2: float
) -> tuple[float, float, float]:
    dx = x2 - x1
    dy = y2 - y1
    length_squared = dx * dx + dy * dy
    if length_squared <= 1e-24:
        return x1, y1, 0.0
    ratio = ((px - x1) * dx + (py - y1) * dy) / length_squared
    ratio = min(max(ratio, 0.0), 1.0)
    return x1 + ratio * dx, y1 + ratio * dy, ratio


def _points(value: Any) -> tuple[tuple[float, float], ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    result: list[tuple[float, float]] = []
    for item in value:
        if isinstance(item, Mapping):
            x, y = _number(item.get("x")), _number(item.get("y"))
        elif isinstance(item, Sequence) and len(item) >= 2:
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


def _inside_rectangle(
    px: float, py: float, x: float, y: float, width: float, height: float
) -> bool:
    return x <= px <= x + width and y <= py <= y + height


def _interaction_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Keep small semantic metadata and omit heavy geometry/style arrays."""

    excluded = {"points", "quality"}
    allowed = {
        "data_kind", "source_layer_id", "title", "text", "label", "segment_index",
        "top", "base", "value", "depth", "unit", "mnemonic",
    }
    return {
        str(key): value
        for key, value in payload.items()
        if key in allowed and key not in excluded and isinstance(value, (str, int, float, bool, type(None)))
    }


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
