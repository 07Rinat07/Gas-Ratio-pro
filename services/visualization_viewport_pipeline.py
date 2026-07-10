"""Viewport-aware adapter for the renderer-neutral visualization pipeline.

The adapter applies an ``InteractiveViewport`` to a LAS visualization payload
before scene construction.  UI code therefore does not filter curve samples,
clip intervals or recalculate render geometry.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field, replace
from hashlib import sha256
import json
from math import isfinite
from typing import Any, Mapping

from services.visualization_interactive_viewport import InteractiveViewport
from services.visualization_scene_pipeline import (
    VisualizationScenePipeline,
    VisualizationScenePipelineResult,
)


@dataclass(frozen=True, slots=True)
class ViewportPipelineProfile:
    requested_start: float
    requested_stop: float
    applied_start: float
    applied_stop: float
    source_start: float
    source_stop: float
    curve_count: int = 0
    source_point_count: int = 0
    visible_point_count: int = 0
    clipped_overlay_count: int = 0
    cache_key: str = ""
    cache_hit: bool = False
    cache_enabled: bool = True
    cache_entries: int = 0
    diagnostics: tuple[str, ...] = field(default_factory=tuple)

    @property
    def clipped(self) -> bool:
        return self.applied_start != self.source_start or self.applied_stop != self.source_stop

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "visualization.viewport.pipeline.profile",
            "version": "1.0",
            "requested_start": self.requested_start,
            "requested_stop": self.requested_stop,
            "applied_start": self.applied_start,
            "applied_stop": self.applied_stop,
            "source_start": self.source_start,
            "source_stop": self.source_stop,
            "curve_count": self.curve_count,
            "source_point_count": self.source_point_count,
            "visible_point_count": self.visible_point_count,
            "clipped_overlay_count": self.clipped_overlay_count,
            "cache_key": self.cache_key,
            "cache_hit": self.cache_hit,
            "cache_enabled": self.cache_enabled,
            "cache_entries": self.cache_entries,
            "clipped": self.clipped,
            "diagnostics": list(self.diagnostics),
            "renderer_neutral": True,
        }


@dataclass(frozen=True, slots=True)
class ViewportPipelineResult:
    pipeline: VisualizationScenePipelineResult
    profile: ViewportPipelineProfile
    payload: dict[str, Any]

    @property
    def ok(self) -> bool:
        return self.pipeline.ok and not any(
            item.startswith("viewport_pipeline_error:") for item in self.profile.diagnostics
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "visualization.viewport.pipeline.result",
            "version": "1.0",
            "pipeline": self.pipeline.to_dict(),
            "profile": self.profile.to_dict(),
            "payload": dict(self.payload),
            "ok": self.ok,
            "renderer_neutral": True,
        }


class VisualizationViewportPayloadCache:
    """Small LRU cache for prepared viewport payloads and profiles."""

    def __init__(self, capacity: int = 16) -> None:
        self.capacity = max(1, int(capacity))
        self._items: OrderedDict[str, tuple[dict[str, Any], ViewportPipelineProfile]] = OrderedDict()

    def get(self, key: str) -> tuple[dict[str, Any], ViewportPipelineProfile] | None:
        item = self._items.get(key)
        if item is None:
            return None
        self._items.move_to_end(key)
        payload, profile = item
        return _deep_copy(payload), profile

    def put(self, key: str, payload: Mapping[str, Any], profile: ViewportPipelineProfile) -> None:
        self._items[key] = (_deep_copy(payload), profile)
        self._items.move_to_end(key)
        while len(self._items) > self.capacity:
            self._items.popitem(last=False)

    def clear(self) -> None:
        self._items.clear()

    def __len__(self) -> int:
        return len(self._items)


class VisualizationViewportPipeline:
    """Apply viewport depth bounds and run the standard scene pipeline."""

    def __init__(
        self,
        pipeline: VisualizationScenePipeline | None = None,
        payload_cache: VisualizationViewportPayloadCache | None = None,
    ) -> None:
        self.pipeline = pipeline or VisualizationScenePipeline()
        self.payload_cache = payload_cache if payload_cache is not None else VisualizationViewportPayloadCache()

    def run(
        self,
        payload: Mapping[str, Any],
        viewport: InteractiveViewport | Mapping[str, Any],
    ) -> ViewportPipelineResult:
        resolved = (
            viewport
            if isinstance(viewport, InteractiveViewport)
            else InteractiveViewport.from_dict(viewport)
        )
        cache_enabled = bool(payload.get("viewport_cache", True))
        cache_key = self.cache_key(payload, resolved)
        cached = self.payload_cache.get(cache_key) if cache_enabled else None
        if cached is None:
            prepared, profile = self.prepare_payload(payload, resolved)
            if cache_enabled:
                self.payload_cache.put(cache_key, prepared, profile)
            profile = replace(
                profile,
                cache_key=cache_key,
                cache_hit=False,
                cache_enabled=cache_enabled,
                cache_entries=len(self.payload_cache),
            )
        else:
            prepared, cached_profile = cached
            profile = replace(
                cached_profile,
                cache_key=cache_key,
                cache_hit=True,
                cache_enabled=True,
                cache_entries=len(self.payload_cache),
            )

        prepared["viewport_pipeline"] = {
            "cache_key": cache_key,
            "cache_hit": profile.cache_hit,
            "cache_enabled": cache_enabled,
        }
        result = self.pipeline.run(prepared)
        result.validation["viewport_cache_key"] = cache_key
        result.validation["viewport_cache_hit"] = profile.cache_hit
        result.validation["viewport_cache_enabled"] = cache_enabled
        return ViewportPipelineResult(pipeline=result, profile=profile, payload=prepared)

    @staticmethod
    def cache_key(
        payload: Mapping[str, Any],
        viewport: InteractiveViewport | Mapping[str, Any],
    ) -> str:
        viewport_contract = (
            viewport.to_dict() if isinstance(viewport, InteractiveViewport) else dict(viewport)
        )
        canonical = json.dumps(
            [dict(payload), viewport_contract],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
        return sha256(canonical).hexdigest()

    def prepare_payload(
        self,
        payload: Mapping[str, Any],
        viewport: InteractiveViewport,
    ) -> tuple[dict[str, Any], ViewportPipelineProfile]:
        prepared = _deep_copy(payload)
        diagnostics: list[str] = []
        depth_range = prepared.get("depth_range")
        if not isinstance(depth_range, Mapping):
            raise ValueError("visualization payload requires depth_range")

        source_start = _finite(depth_range.get("start"), "depth_range.start")
        source_stop = _finite(depth_range.get("stop"), "depth_range.stop")
        if source_stop <= source_start:
            raise ValueError("depth_range.stop must be greater than depth_range.start")

        applied_start = max(source_start, viewport.domain_start)
        applied_stop = min(source_stop, viewport.domain_stop)
        if applied_stop <= applied_start:
            diagnostics.append("viewport_pipeline_error:no_domain_intersection")
            applied_start = source_start
            applied_stop = source_stop

        prepared["depth_range"] = {
            **dict(depth_range),
            "start": applied_start,
            "stop": applied_stop,
        }
        prepared["viewport"] = viewport.to_dict()

        curves = prepared.get("curves")
        curve_items = curves if isinstance(curves, list) else []
        source_point_count = 0
        visible_point_count = 0
        for curve in curve_items:
            if not isinstance(curve, dict):
                continue
            points = curve.get("points")
            point_items = points if isinstance(points, list) else []
            source_point_count += len(point_items)
            filtered = _clip_curve_points(point_items, applied_start, applied_stop)
            visible_point_count += len(filtered)
            curve["points"] = filtered
            curve["sampled_count"] = len(filtered)
            curve["point_count_visible"] = len(filtered)
            quality = curve.get("quality")
            if isinstance(quality, dict):
                quality["within_depth_range"] = {
                    "start": applied_start,
                    "stop": applied_stop,
                }

        overlays = prepared.get("overlays")
        overlay_items = overlays if isinstance(overlays, list) else []
        clipped_overlays: list[dict[str, Any]] = []
        clipped_overlay_count = 0
        for overlay in overlay_items:
            if not isinstance(overlay, Mapping):
                continue
            top = _optional_finite(overlay.get("top"))
            base = _optional_finite(overlay.get("base"))
            if top is None or base is None:
                clipped_overlays.append(dict(overlay))
                continue
            visible_top = max(min(top, base), applied_start)
            visible_base = min(max(top, base), applied_stop)
            if visible_base <= visible_top:
                continue
            item = _deep_copy(overlay)
            item["top"] = visible_top
            item["base"] = visible_base
            if visible_top != min(top, base) or visible_base != max(top, base):
                item["viewport_clipped"] = True
                clipped_overlay_count += 1
            clipped_overlays.append(item)
        prepared["overlays"] = clipped_overlays

        profile = ViewportPipelineProfile(
            requested_start=viewport.domain_start,
            requested_stop=viewport.domain_stop,
            applied_start=applied_start,
            applied_stop=applied_stop,
            source_start=source_start,
            source_stop=source_stop,
            curve_count=len(curve_items),
            source_point_count=source_point_count,
            visible_point_count=visible_point_count,
            clipped_overlay_count=clipped_overlay_count,
            diagnostics=tuple(diagnostics),
        )
        return prepared, profile


def _clip_curve_points(
    points: list[Any],
    start: float,
    stop: float,
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for point in points:
        if not isinstance(point, Mapping):
            continue
        depth = _optional_finite(point.get("depth"))
        if depth is None:
            continue
        normalized.append(dict(point))
    normalized.sort(key=lambda item: float(item["depth"]))
    if not normalized:
        return []

    result = [item for item in normalized if start <= float(item["depth"]) <= stop]
    for boundary in (start, stop):
        if any(abs(float(item["depth"]) - boundary) <= 1e-12 for item in result):
            continue
        interpolated = _interpolate_boundary(normalized, boundary)
        if interpolated is not None:
            result.append(interpolated)
    result.sort(key=lambda item: float(item["depth"]))
    return result


def _interpolate_boundary(points: list[dict[str, Any]], depth: float) -> dict[str, Any] | None:
    for left, right in zip(points, points[1:]):
        left_depth = float(left["depth"])
        right_depth = float(right["depth"])
        if not (left_depth < depth < right_depth):
            continue
        left_value = _optional_finite(left.get("value"))
        right_value = _optional_finite(right.get("value"))
        if left_value is None or right_value is None or right_depth == left_depth:
            return None
        ratio = (depth - left_depth) / (right_depth - left_depth)
        return {
            "depth": depth,
            "value": left_value + (right_value - left_value) * ratio,
            "viewport_interpolated": True,
        }
    return None


def _finite(value: Any, name: str) -> float:
    resolved = _optional_finite(value)
    if resolved is None:
        raise ValueError(f"{name} must be a finite number")
    return resolved


def _optional_finite(value: Any) -> float | None:
    try:
        resolved = float(value)
    except (TypeError, ValueError):
        return None
    return resolved if isfinite(resolved) else None


def _deep_copy(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _deep_copy(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_deep_copy(item) for item in value]
    if isinstance(value, tuple):
        return [_deep_copy(item) for item in value]
    return value


__all__ = [
    "ViewportPipelineProfile",
    "ViewportPipelineResult",
    "VisualizationViewportPayloadCache",
    "VisualizationViewportPipeline",
]
