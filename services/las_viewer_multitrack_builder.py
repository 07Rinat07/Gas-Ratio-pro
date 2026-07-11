"""Build a complete renderer-neutral multi-track LAS Viewer from an imported payload.

The builder is the application boundary between LAS-open payload creation and the
existing viewer session/render pipeline. It removes non-renderable curves,
rebuilds track membership deterministically, and returns compact serializable
viewer and render contracts without retaining a raw DataFrame.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from typing import Any, Mapping

from services.las_viewer_render_pipeline import LasViewerRenderPipeline
from services.las_viewer_session import LasViewerSession


def _curve_id(curve: Mapping[str, Any]) -> str:
    return str(curve.get("mnemonic") or curve.get("id") or "").strip()


def _track_id(curve: Mapping[str, Any]) -> str:
    return str(curve.get("track_id") or "track.other").strip() or "track.other"


def _renderable_points(curve: Mapping[str, Any]) -> list[Any]:
    result: list[Any] = []
    for point in curve.get("points") or ():
        if isinstance(point, Mapping):
            depth, value = point.get("depth"), point.get("value")
        elif isinstance(point, (list, tuple)) and len(point) >= 2:
            depth, value = point[0], point[1]
        else:
            continue
        try:
            if isfinite(float(depth)) and isfinite(float(value)):
                result.append(point)
        except (TypeError, ValueError):
            continue
    return result


@dataclass(frozen=True, slots=True)
class LasViewerMultiTrackResult:
    payload: Mapping[str, Any]
    viewer_state: Mapping[str, Any]
    render_result: Mapping[str, Any]
    track_count: int
    curve_count: int
    excluded_curves: tuple[str, ...] = field(default_factory=tuple)
    diagnostics: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return bool(self.track_count and self.curve_count and self.render_result.get("ok", False))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "las.viewer.multitrack.result",
            "version": "1.0",
            "payload": dict(self.payload),
            "viewer_state": dict(self.viewer_state),
            "render_result": dict(self.render_result),
            "track_count": self.track_count,
            "curve_count": self.curve_count,
            "excluded_curves": list(self.excluded_curves),
            "diagnostics": list(self.diagnostics),
            "ok": self.ok,
            "raw_dataframe_included": False,
            "renderer_neutral": True,
        }


class LasViewerMultiTrackBuilder:
    """Normalize imported LAS curves and build the first complete viewer render."""

    def __init__(self, render_pipeline: LasViewerRenderPipeline | None = None) -> None:
        self.render_pipeline = render_pipeline or LasViewerRenderPipeline()

    def build(self, payload: Mapping[str, Any]) -> LasViewerMultiTrackResult:
        las_id = str(payload.get("las_id") or "").strip()
        if not las_id:
            raise ValueError("LAS multi-track viewer requires las_id")

        source_tracks = [dict(item) for item in payload.get("tracks") or () if isinstance(item, Mapping)]
        source_curves = [dict(item) for item in payload.get("curves") or () if isinstance(item, Mapping)]
        excluded: list[str] = []
        curves: list[dict[str, Any]] = []
        for curve in source_curves:
            mnemonic = _curve_id(curve)
            if not mnemonic:
                excluded.append("<unnamed>")
                continue
            points = _renderable_points(curve)
            if not points:
                excluded.append(mnemonic)
                continue
            curve["mnemonic"] = mnemonic
            curve["track_id"] = _track_id(curve)
            curve["points"] = points
            curves.append(curve)

        if not curves:
            raise ValueError("LAS payload does not contain renderable curves")

        curves_by_track: dict[str, list[str]] = {}
        for curve in curves:
            curves_by_track.setdefault(curve["track_id"], []).append(curve["mnemonic"])

        tracks: list[dict[str, Any]] = []
        seen: set[str] = set()
        for source in source_tracks:
            track_id = str(source.get("id") or "").strip()
            if not track_id or track_id not in curves_by_track or track_id in seen:
                continue
            source["id"] = track_id
            source["curve_ids"] = list(curves_by_track[track_id])
            source["visible"] = True
            source["order"] = len(tracks)
            tracks.append(source)
            seen.add(track_id)
        for track_id, curve_ids in curves_by_track.items():
            if track_id in seen:
                continue
            tracks.append({
                "id": track_id,
                "title": track_id.removeprefix("track.").replace("_", " ").title(),
                "curve_ids": list(curve_ids),
                "width": 1.0,
                "visible": True,
                "order": len(tracks),
                "printable": True,
            })

        prepared = dict(payload)
        prepared["tracks"] = tracks
        prepared["curves"] = curves
        prepared["visible_tracks"] = [track["id"] for track in tracks]
        flags = [str(item) for item in payload.get("quality_flags") or ()]
        if excluded and "empty_curves_excluded" not in flags:
            flags.append("empty_curves_excluded")
        prepared["quality_flags"] = flags
        prepared["las_viewer_multitrack"] = {
            "track_count": len(tracks),
            "curve_count": len(curves),
            "excluded_curves": list(excluded),
            "renderer_neutral": True,
        }

        session = LasViewerSession(prepared)
        render = self.render_pipeline.run(prepared, session)
        diagnostics = tuple(render.profile.diagnostics)
        return LasViewerMultiTrackResult(
            payload=prepared,
            viewer_state=session.state.to_dict(),
            render_result=render.to_dict(),
            track_count=len(tracks),
            curve_count=len(curves),
            excluded_curves=tuple(excluded),
            diagnostics=diagnostics,
        )
