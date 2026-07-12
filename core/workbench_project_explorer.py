"""Framework-neutral helpers for Modern Workbench Project Explorer 2.0."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping


@dataclass(frozen=True, slots=True)
class ProjectExplorerView:
    nodes: tuple[dict[str, Any], ...]
    total_nodes: int
    matched_nodes: int
    query: str


_KIND_ICONS = {
    "project": "▣",
    "folder": "▸",
    "custom_folder": "▸",
    "well_group": "▸",
    "well": "◉",
    "las_version": "▤",
    "las": "▤",
    "curve": "⌁",
    "calculation": "∑",
    "report": "▧",
    "export": "⇩",
    "folder_item": "•",
    "missing": "!",
    "empty": "·",
    "collection": "▸",
}


def explorer_kind_icon(kind: str) -> str:
    return _KIND_ICONS.get(str(kind or "").strip(), "•")


def explorer_status_marker(node: Mapping[str, Any]) -> str:
    """Return a compact, non-alarming status marker for one explorer node."""
    kind = str(node.get("kind") or "")
    status = str(node.get("status") or "").lower()
    metadata = dict(node.get("metadata", {}) or {})
    warnings = metadata.get("warnings_count", 0)
    try:
        warnings_count = int(warnings or 0)
    except (TypeError, ValueError):
        warnings_count = 0
    if kind == "missing" or "ошиб" in status or "error" in status:
        return "🔴"
    if warnings_count > 0 or "предупреж" in status or "warning" in status:
        return "🟡"
    if kind == "empty" or "пока нет" in status or "нет " in status:
        return "⚪"
    return "🟢"


def filter_project_explorer_nodes(
    nodes: Iterable[Mapping[str, Any]],
    query: str = "",
) -> ProjectExplorerView:
    """Filter nodes while preserving every ancestor of a matching node."""
    normalized = tuple(dict(node) for node in nodes)
    clean_query = str(query or "").strip().casefold()
    if not clean_query:
        return ProjectExplorerView(normalized, len(normalized), len(normalized), "")

    by_id = {str(node.get("id") or ""): node for node in normalized}
    matched_ids: set[str] = set()
    for node in normalized:
        haystack = " ".join(
            (
                str(node.get("title") or ""),
                str(node.get("status") or ""),
                str(node.get("kind") or ""),
                str(node.get("object_id") or ""),
            )
        ).casefold()
        if clean_query in haystack:
            node_id = str(node.get("id") or "")
            while node_id and node_id not in matched_ids:
                matched_ids.add(node_id)
                node_id = str(by_id.get(node_id, {}).get("parent_id") or "")

    visible = tuple(node for node in normalized if str(node.get("id") or "") in matched_ids)
    direct_matches = sum(
        1
        for node in normalized
        if clean_query
        in " ".join(
            (
                str(node.get("title") or ""),
                str(node.get("status") or ""),
                str(node.get("kind") or ""),
                str(node.get("object_id") or ""),
            )
        ).casefold()
    )
    return ProjectExplorerView(visible, len(normalized), direct_matches, clean_query)


def visible_project_explorer_nodes(
    nodes: Iterable[Mapping[str, Any]],
    expanded_ids: Iterable[str],
    *,
    force_expand: bool = False,
) -> tuple[dict[str, Any], ...]:
    """Return nodes whose ancestor chain is expanded.

    Search results pass ``force_expand=True`` so matching descendants and their
    ancestors are visible regardless of the persisted expansion state.
    """
    normalized = tuple(dict(node) for node in nodes)
    if force_expand:
        return normalized
    expanded = {str(item) for item in expanded_ids}
    by_id = {str(node.get("id") or ""): node for node in normalized}
    visible: list[dict[str, Any]] = []
    for node in normalized:
        parent_id = str(node.get("parent_id") or "")
        show = True
        while parent_id:
            if parent_id not in expanded:
                show = False
                break
            parent_id = str(by_id.get(parent_id, {}).get("parent_id") or "")
        if show:
            visible.append(node)
    return tuple(visible)
