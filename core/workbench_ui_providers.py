"""Application-level providers for the production Workbench UI.

The providers translate existing application/tool contracts into small,
serializable presentation models.  They do not read Streamlit state directly,
perform engineering calculations or expose repositories/dataframes to the UI.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, MutableMapping

from core.workbench_context import WorkspaceContext
from core.workbench_las_primary_module import WorkbenchLasPrimaryModuleService


def _text(value: Any, fallback: str = "—") -> str:
    clean = str(value or "").strip()
    return clean or fallback


def _finite_number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number


@dataclass(frozen=True, slots=True)
class WorkbenchUIProviderPayload:
    project_tree: tuple[dict[str, Any], ...]
    properties: tuple[dict[str, Any], ...]
    status_items: tuple[dict[str, Any], ...]
    workspace_runtime: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_tree": [dict(item) for item in self.project_tree],
            "properties": [dict(item) for item in self.properties],
            "status_items": [dict(item) for item in self.status_items],
            "workspace_runtime": dict(self.workspace_runtime),
        }


class WorkbenchUIProviderService:
    """Hydrate Workbench panes from existing application-level contracts."""

    def __init__(self, state: MutableMapping[str, Any]) -> None:
        self.state = state

    def build(self, context: WorkspaceContext, active_module: Mapping[str, Any]) -> WorkbenchUIProviderPayload:
        tool = dict(active_module.get("tool", {}) or {})
        content = dict(tool.get("content", {}) or {})
        visualization = dict(content.get("visualization", {}) or {})
        selected = dict(context.selection.to_dict())
        primary = WorkbenchLasPrimaryModuleService(self.state).snapshot()
        viewer_state = dict(primary.get("viewer_state", {}) or {})

        tracks = list(visualization.get("tracks", ()) or ())
        curves = list(visualization.get("curves", ()) or ())
        project_id = context.application.project_id
        well_id = context.application.well_id or content.get("selected_las", {}).get("well_id", "")
        las_id = context.application.las_id

        tree: list[dict[str, Any]] = [
            {"id": "tree.project", "title": _text(project_id, "No project open"), "kind": "project", "level": 0, "count": 1 if project_id else 0, "selectable": bool(project_id), "target": "project", "object_id": project_id},
            {"id": "tree.wells", "title": "Wells", "kind": "collection", "level": 1, "count": 1 if well_id else 0, "selectable": False},
        ]
        if well_id:
            tree.append({"id": f"tree.well.{well_id}", "title": _text(well_id), "kind": "well", "level": 2, "count": 1, "selectable": True, "target": "well", "object_id": well_id})
        tree.append({"id": "tree.las", "title": "LAS", "kind": "collection", "level": 1, "count": 1 if las_id else 0, "selectable": False})
        if las_id:
            tree.append({"id": f"tree.las.{las_id}", "title": _text(las_id), "kind": "las", "level": 2, "count": len(curves), "selectable": True, "target": "las", "object_id": las_id})
        tree.append({"id": "tree.curves", "title": "Curves", "kind": "collection", "level": 1, "count": len(curves), "selectable": False})
        for curve in curves[:200]:
            curve_id = str(curve.get("id") or curve.get("mnemonic") or curve.get("name") or "").strip()
            if curve_id:
                tree.append({"id": f"tree.curve.{curve_id}", "title": str(curve.get("title") or curve.get("mnemonic") or curve_id), "kind": "curve", "level": 2, "count": 0, "selectable": True, "target": "curve", "object_id": curve_id, "metadata": {"unit": curve.get("unit", ""), "track_id": curve.get("track_id", "")}})
        project_counts = dict(self.state.get("workbench_project_counts", {}) or {})
        tree.extend((
            {"id": "tree.correlation", "title": "Correlation", "kind": "collection", "level": 1, "count": int(project_counts.get("correlations", 0) or 0), "selectable": True},
            {"id": "tree.calculations", "title": "Calculations", "kind": "collection", "level": 1, "count": int(project_counts.get("calculations", 0) or 0), "selectable": False},
            {"id": "tree.reports", "title": "Reports", "kind": "collection", "level": 1, "count": int(project_counts.get("reports", 1 if context.active_report else 0) or 0), "selectable": False},
            {"id": "tree.exports", "title": "Exports", "kind": "collection", "level": 1, "count": int(project_counts.get("exports", len(tuple(self.state.get("recent_exports", ()) or ()))) or 0), "selectable": False},
        ))

        target = str(selected.get("target") or "").strip()
        object_id = str(selected.get("object_id") or "").strip()
        metadata = dict(selected.get("metadata", {}) or {})
        properties: list[dict[str, Any]] = []
        if object_id:
            target_titles = {
                "project": "Project",
                "well": "Well",
                "las": "LAS file",
                "curve": "Curve",
                "calculation": "Calculation",
                "report": "Report",
                "document": "Document",
                "collection": "Collection",
            }
            properties.extend((
                {"label": "Selected", "value": target_titles.get(target, target.replace("_", " ").title() or "Object")},
                {"label": "Object", "value": object_id},
            ))
            preferred_order = (
                "title", "path", "kind", "count", "unit", "track_id", "depth_start",
                "depth_stop", "step", "curve_count", "status", "modified_at", "size",
                "format", "language", "description", "navigation_id",
            )
            emitted: set[str] = set()
            for key in preferred_order:
                if key in metadata and isinstance(metadata[key], (str, int, float, bool)) or (key in metadata and metadata[key] is None):
                    properties.append({"label": key.replace("_", " ").title(), "value": _text(metadata[key])})
                    emitted.add(key)
            for key, value in sorted(metadata.items()):
                if key not in emitted and (isinstance(value, (str, int, float, bool)) or value is None):
                    properties.append({"label": str(key).replace("_", " ").title(), "value": _text(value)})
        else:
            properties.extend((
                {"label": "Nothing selected", "value": "Choose a project, well, LAS, curve, calculation, report or document."},
                {"label": "Active project", "value": _text(project_id)},
                {"label": "Active module", "value": _text(tool.get("title"), "Dashboard")},
            ))
            if well_id:
                properties.append({"label": "Active well", "value": _text(well_id)})
            if las_id:
                properties.append({"label": "Active LAS", "value": _text(las_id)})

        viewport = dict(viewer_state.get("viewport", {}) or {})
        viewport_start = _finite_number(viewport.get("start"))
        viewport_stop = _finite_number(viewport.get("stop"))
        viewport_text = "—"
        if viewport_start is not None and viewport_stop is not None:
            viewport_text = f"{viewport_start:g} – {viewport_stop:g}"
        scale = str(viewer_state.get("scale") or viewer_state.get("zoom") or "1.0").strip() or "1.0"
        status_items = (
            {"label": "Project", "value": _text(project_id)},
            {"label": "Well", "value": _text(well_id)},
            {"label": "LAS", "value": _text(las_id)},
            {"label": "Module", "value": _text(tool.get("title"), "Dashboard")},
            {"label": "Viewport", "value": viewport_text},
            {"label": "Scale", "value": scale},
            {"label": "Tracks", "value": str(len(tracks))},
            {"label": "Curves", "value": str(len(curves))},
            {"label": "Status", "value": "Ready" if tool.get("status") == "ready" else _text(tool.get("status"), "Awaiting project")},
        )
        workspace_runtime = {
            "kind": "las_viewer" if tool.get("id") == "tool.las_viewer" else "module",
            "embedded": bool(tool.get("id") == "tool.las_viewer" and visualization),
            "visualization": visualization,
            "primary_module": primary,
            "track_count": len(tracks),
            "curve_count": len(curves),
            "viewport": viewport,
            "scale": scale,
            "raw_dataframe_included": False,
        }
        return WorkbenchUIProviderPayload(tuple(tree), tuple(properties), status_items, workspace_runtime)
