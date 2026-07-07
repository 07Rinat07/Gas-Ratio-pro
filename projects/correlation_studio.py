from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from las_correlation import (
    CorrelationLine,
    CorrelationMarker,
    DepthAlignment,
    correlation_line_rows,
    correlation_marker_rows,
    normalize_correlation_lines,
    normalize_correlation_markers,
    normalize_depth_alignments,
)
from projects.project_manager import append_project_history
from projects.repository import DEFAULT_PROJECT_ID, DEFAULT_PROJECTS_ROOT, safe_project_id

PROJECT_CORRELATION_STUDIO_FILE_NAME = "correlation_studio.json"
CORRELATION_SESSION_STATUSES = {"draft", "active", "approved", "archived"}
CORRELATION_EXPORT_FORMATS = {"json", "png", "svg", "pdf"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _project_dir(root: Path | str, project_id: str) -> Path:
    return Path(root) / safe_project_id(project_id)


def _correlation_path(root: Path | str, project_id: str) -> Path:
    return _project_dir(root, project_id) / PROJECT_CORRELATION_STUDIO_FILE_NAME


def _json_read(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return default


def _json_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _payload(root: Path | str, project_id: str) -> dict[str, Any]:
    payload = _json_read(_correlation_path(root, project_id), {"sessions": []})
    if not isinstance(payload, dict):
        payload = {"sessions": []}
    payload.setdefault("sessions", [])
    return payload


def _clean_text(value: Any, field_label: str, *, max_length: int = 240, required: bool = False) -> str:
    text = "" if value is None else str(value).strip()
    if required and not text:
        raise ValueError(f"{field_label}: значение обязательно.")
    if len(text) > max_length:
        raise ValueError(f"{field_label}: максимум {max_length} символов.")
    return text


def _safe_session_id(value: Any, *, default: str = "correlation-session") -> str:
    text = _clean_text(value, "ID", max_length=160) or default
    normalized = "".join(ch if ch.isalnum() or ch in "_-" else "-" for ch in text).strip("-_").lower()
    return normalized or default


def _clean_status(value: Any) -> str:
    status = _clean_text(value, "Статус", max_length=32).lower() or "draft"
    if status not in CORRELATION_SESSION_STATUSES:
        raise ValueError(f"Статус должен быть одним из: {', '.join(sorted(CORRELATION_SESSION_STATUSES))}.")
    return status


def _line_to_dict(line: CorrelationLine) -> dict[str, Any]:
    return dict(correlation_line_rows([line])[0])


def _marker_to_dict(marker: CorrelationMarker) -> dict[str, Any]:
    row = correlation_marker_rows(type("Panel", (), {"markers": (marker,)})())[0]
    result = dict(row)
    result["well"] = "" if result["well"] == "Все скважины" else result["well"]
    return result


def _alignment_to_dict(alignment: DepthAlignment) -> dict[str, Any]:
    return {
        "well": alignment.well,
        "shift": alignment.shift,
        "reference": alignment.reference,
        "note": alignment.note,
    }


@dataclass(frozen=True)
class CorrelationSession:
    """Persistent Professional Correlation Studio workspace session."""

    id: str
    name: str
    wells: tuple[str, ...] = ()
    markers: tuple[CorrelationMarker, ...] = ()
    lines: tuple[CorrelationLine, ...] = ()
    alignments: tuple[DepthAlignment, ...] = ()
    depth_range: tuple[float, float] | None = None
    selected_groups: tuple[str, ...] = ()
    grid_mode: str = "union"
    status: str = "draft"
    note: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""


@dataclass(frozen=True)
class CorrelationSessionSummary:
    sessions: int
    active: int
    wells: int
    markers: int
    lines: int
    alignments: int
    statuses: tuple[str, ...]


def session_to_dict(session: CorrelationSession) -> dict[str, Any]:
    return {
        "id": session.id,
        "name": session.name,
        "wells": list(session.wells),
        "markers": [_marker_to_dict(marker) for marker in session.markers],
        "lines": [_line_to_dict(line) for line in session.lines],
        "alignments": [_alignment_to_dict(alignment) for alignment in session.alignments],
        "depth_range": list(session.depth_range) if session.depth_range is not None else None,
        "selected_groups": list(session.selected_groups),
        "grid_mode": session.grid_mode,
        "status": session.status,
        "note": session.note,
        "metadata": dict(session.metadata),
        "created_at": session.created_at,
        "updated_at": session.updated_at,
    }


def normalize_correlation_session(raw: CorrelationSession | Mapping[str, Any]) -> CorrelationSession:
    if isinstance(raw, CorrelationSession):
        session = raw
    elif isinstance(raw, Mapping):
        now = _utc_now()
        raw_depth_range = raw.get("depth_range")
        depth_range = None
        if isinstance(raw_depth_range, (list, tuple)) and len(raw_depth_range) == 2:
            try:
                depth_range = tuple(sorted((float(raw_depth_range[0]), float(raw_depth_range[1]))))
            except (TypeError, ValueError):
                depth_range = None
        session = CorrelationSession(
            id=_safe_session_id(raw.get("id") or raw.get("name")),
            name=_clean_text(raw.get("name"), "Название сессии", required=True),
            wells=tuple(dict.fromkeys(str(item).strip() for item in raw.get("wells", ()) if str(item).strip())),
            markers=normalize_correlation_markers(raw.get("markers", ())),
            lines=normalize_correlation_lines(raw.get("lines", ())),
            alignments=normalize_depth_alignments(raw.get("alignments", ())),
            depth_range=depth_range,  # type: ignore[arg-type]
            selected_groups=tuple(dict.fromkeys(str(item).strip() for item in raw.get("selected_groups", ()) if str(item).strip())),
            grid_mode=_clean_text(raw.get("grid_mode") or "union", "Режим сетки", max_length=32),
            status=_clean_status(raw.get("status", "draft")),
            note=_clean_text(raw.get("note"), "Примечание", max_length=1000),
            metadata=raw.get("metadata", {}) if isinstance(raw.get("metadata", {}), Mapping) else {},
            created_at=_clean_text(raw.get("created_at") or now, "Дата создания", max_length=80),
            updated_at=_clean_text(raw.get("updated_at") or now, "Дата обновления", max_length=80),
        )
    else:
        raise TypeError("Correlation session должен быть CorrelationSession или mapping.")

    if not session.wells:
        raise ValueError("Сессия корреляции должна содержать минимум одну скважину.")
    return CorrelationSession(
        id=_safe_session_id(session.id),
        name=_clean_text(session.name, "Название сессии", required=True),
        wells=tuple(dict.fromkeys(str(item).strip() for item in session.wells if str(item).strip())),
        markers=tuple(session.markers),
        lines=tuple(session.lines),
        alignments=tuple(session.alignments),
        depth_range=session.depth_range,
        selected_groups=tuple(dict.fromkeys(str(item).strip() for item in session.selected_groups if str(item).strip())),
        grid_mode=_clean_text(session.grid_mode or "union", "Режим сетки", max_length=32),
        status=_clean_status(session.status),
        note=_clean_text(session.note, "Примечание", max_length=1000),
        metadata=dict(session.metadata),
        created_at=_clean_text(session.created_at or _utc_now(), "Дата создания", max_length=80),
        updated_at=_clean_text(session.updated_at or _utc_now(), "Дата обновления", max_length=80),
    )


def list_correlation_sessions(
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
    *,
    status: str = "",
) -> tuple[CorrelationSession, ...]:
    payload = _payload(root, project_id)
    sessions: list[CorrelationSession] = []
    for row in payload.get("sessions", []):
        if not isinstance(row, Mapping):
            continue
        try:
            sessions.append(normalize_correlation_session(row))
        except (TypeError, ValueError):
            continue
    if status:
        clean_status = _clean_status(status)
        sessions = [session for session in sessions if session.status == clean_status]
    return tuple(sorted(sessions, key=lambda item: (item.status != "active", item.name.lower(), item.id)))


def get_correlation_session(root: Path | str, project_id: str, session_id: str) -> CorrelationSession | None:
    clean_id = _safe_session_id(session_id)
    for session in list_correlation_sessions(root, project_id):
        if session.id == clean_id:
            return session
    return None


def save_correlation_session(root: Path | str, project_id: str, session: CorrelationSession | Mapping[str, Any]) -> CorrelationSession:
    normalized = normalize_correlation_session(session)
    now = _utc_now()
    existing = {item.id: item for item in list_correlation_sessions(root, project_id)}
    created_at = existing.get(normalized.id, normalized).created_at or now
    normalized = CorrelationSession(**{**normalized.__dict__, "created_at": created_at, "updated_at": now})

    existing[normalized.id] = normalized
    payload = _payload(root, project_id)
    payload["sessions"] = [session_to_dict(item) for item in sorted(existing.values(), key=lambda item: item.name.lower())]
    _json_write(_correlation_path(root, project_id), payload)
    append_project_history(
        root,
        project_id,
        "correlation-session-save",
        f"Correlation session saved: {normalized.name}",
        object_type="correlation_session",
        object_id=normalized.id,
    )
    return normalized


def delete_correlation_session(root: Path | str, project_id: str, session_id: str) -> bool:
    clean_id = _safe_session_id(session_id)
    sessions = list(list_correlation_sessions(root, project_id))
    remaining = [session for session in sessions if session.id != clean_id]
    if len(remaining) == len(sessions):
        return False
    payload = _payload(root, project_id)
    payload["sessions"] = [session_to_dict(item) for item in remaining]
    _json_write(_correlation_path(root, project_id), payload)
    append_project_history(
        root,
        project_id,
        "correlation-session-delete",
        f"Correlation session deleted: {clean_id}",
        object_type="correlation_session",
        object_id=clean_id,
    )
    return True


def build_correlation_session_table(sessions: Iterable[CorrelationSession]) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "ID": session.id,
            "Название": session.name,
            "Статус": session.status,
            "Скважины": len(session.wells),
            "Маркеры": len(session.markers),
            "Линии": len(session.lines),
            "Выравнивания": len(session.alignments),
            "Диапазон": "" if session.depth_range is None else f"{session.depth_range[0]:g}–{session.depth_range[1]:g}",
            "Обновлено": session.updated_at,
        }
        for session in sessions
    )


def summarize_correlation_sessions(sessions: Iterable[CorrelationSession]) -> CorrelationSessionSummary:
    selected = tuple(sessions)
    return CorrelationSessionSummary(
        sessions=len(selected),
        active=sum(1 for session in selected if session.status == "active"),
        wells=len({well for session in selected for well in session.wells}),
        markers=sum(len(session.markers) for session in selected),
        lines=sum(len(session.lines) for session in selected),
        alignments=sum(len(session.alignments) for session in selected),
        statuses=tuple(sorted({session.status for session in selected})),
    )


def export_correlation_session_json(session: CorrelationSession) -> str:
    return json.dumps(session_to_dict(normalize_correlation_session(session)), ensure_ascii=False, indent=2)


def import_correlation_session_json(text: str) -> CorrelationSession:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("JSON сессии корреляции поврежден.") from exc
    if not isinstance(payload, Mapping):
        raise ValueError("JSON сессии корреляции должен быть объектом.")
    return normalize_correlation_session(payload)


def build_correlation_export_manifest(session: CorrelationSession, *, formats: Iterable[str] = ("json",)) -> dict[str, Any]:
    clean_formats = []
    for fmt in formats:
        clean = _clean_text(fmt, "Формат экспорта", max_length=16).lower().lstrip(".")
        if clean not in CORRELATION_EXPORT_FORMATS:
            raise ValueError(f"Формат экспорта должен быть одним из: {', '.join(sorted(CORRELATION_EXPORT_FORMATS))}.")
        clean_formats.append(clean)
    normalized = normalize_correlation_session(session)
    return {
        "session_id": normalized.id,
        "session_name": normalized.name,
        "formats": tuple(dict.fromkeys(clean_formats)),
        "wells": normalized.wells,
        "markers": len(normalized.markers),
        "lines": len(normalized.lines),
        "created_at": _utc_now(),
    }
