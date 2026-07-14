from __future__ import annotations

"""Persistent multi-well correlation workspaces based on published revisions."""

import csv
import hashlib
import io
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from uuid import UUID, uuid4

from core.repository_io import AtomicJsonStore, RepositoryIOMetrics
from projects.interpretation_intervals import InterpretationInterval, _interval_from_dict
from projects.repository import DEFAULT_PROJECTS_ROOT, safe_project_id
from projects.well_cards import safe_well_id

CORRELATION_SCHEMA = "gas-ratio-pro/interpretation-correlation/v1"
CORRELATION_DIR_NAME = "correlations"
MAX_NAME = 160
MAX_NOTE = 2000
TIE_DASHES = {"solid", "dot", "dash", "longdash", "dashdot", "longdashdot"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _clean(value: Any, label: str, limit: int, required: bool = False) -> str:
    result = str(value or "").strip()
    if required and not result:
        raise ValueError(f"{label}: значение обязательно.")
    if len(result) > limit:
        raise ValueError(f"{label}: максимум {limit} символов.")
    return result


def _uuid(value: Any = "") -> str:
    clean = str(value or "").strip()
    if not clean:
        return str(uuid4())
    try:
        return str(UUID(clean))
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError("Некорректный UUID.") from exc


def _atomic_write(
    path: Path,
    payload: Mapping[str, Any],
    *,
    metrics: RepositoryIOMetrics | None = None,
    repository: str = "interpretation_correlation",
) -> None:
    """Backward-compatible atomic writer routed through the shared I/O layer."""

    AtomicJsonStore(repository=repository, metrics=metrics).write(path, payload)


@dataclass(frozen=True)
class PublishedInterpretationInput:
    well_id: str
    interpretation_id: str
    revision_id: str
    revision_name: str
    published_at: str
    intervals: tuple[InterpretationInterval, ...]
    state_token: str


@dataclass(frozen=True)
class CorrelationEndpoint:
    well_id: str
    interpretation_id: str
    revision_id: str
    interval_id: str
    depth: float
    label: str


@dataclass(frozen=True)
class CorrelationTie:
    id: str
    left: CorrelationEndpoint
    right: CorrelationEndpoint
    name: str
    note: str
    color: str = "#1F77B4"
    width: float = 2.0
    dash: str = "solid"
    visible: bool = True
    created_at: str = ""
    updated_at: str = ""


@dataclass(frozen=True)
class CorrelationWorkspace:
    id: str
    name: str
    description: str
    wells: tuple[str, ...]
    ties: tuple[CorrelationTie, ...]
    created_at: str
    updated_at: str

    @property
    def state_token(self) -> str:
        payload = asdict(self)
        return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def discover_published_interpretations(*, root: Path | str = DEFAULT_PROJECTS_ROOT, project_id: str) -> tuple[PublishedInterpretationInput, ...]:
    project = safe_project_id(project_id)
    project_dir = Path(root) / project
    result: list[PublishedInterpretationInput] = []
    for publication_path in sorted(project_dir.glob("wells/*/interpretations/*/.workflow/publication.json")):
        try:
            publication = json.loads(publication_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            continue
        if publication.get("status") != "published" or not publication.get("published_revision_id"):
            continue
        interpretation_dir = publication_path.parent.parent
        interpretation_id = interpretation_dir.name
        well_id = interpretation_dir.parent.parent.name
        revision_id = str(publication["published_revision_id"])
        revision_path = interpretation_dir / ".revisions" / f"{revision_id}.json"
        try:
            revision = json.loads(revision_path.read_text(encoding="utf-8"))
            metadata = revision["metadata"]
            files = revision["files"]
            rows = files.get("intervals.json", {}).get("intervals", [])
            intervals = tuple(sorted((_interval_from_dict(row) for row in rows), key=lambda item: (item.top, item.base)))
            result.append(PublishedInterpretationInput(
                well_id=safe_well_id(well_id), interpretation_id=interpretation_id,
                revision_id=revision_id, revision_name=str(metadata.get("name", revision_id)),
                published_at=str(publication.get("updated_at", "")), intervals=intervals,
                state_token=str(metadata.get("state_token", "")),
            ))
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            continue
    return tuple(sorted(result, key=lambda item: (item.well_id, item.interpretation_id)))


class CorrelationWorkspaceRepository:
    def __init__(
        self,
        *,
        root: Path | str = DEFAULT_PROJECTS_ROOT,
        project_id: str,
        io_metrics: RepositoryIOMetrics | None = None,
    ) -> None:
        self.root = Path(root)
        self.project_id = safe_project_id(project_id)
        self.directory = self.root / self.project_id / CORRELATION_DIR_NAME
        self.io_metrics = io_metrics
        self.store = AtomicJsonStore(repository="interpretation_correlation", metrics=io_metrics)

    def list(self) -> tuple[CorrelationWorkspace, ...]:
        result: list[CorrelationWorkspace] = []
        if not self.directory.exists():
            return ()
        for path in sorted(self.directory.glob("*/correlation.json")):
            try:
                result.append(self._parse(self.store.read(path, expected_schema=CORRELATION_SCHEMA)))
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                continue
        return tuple(sorted(result, key=lambda item: item.updated_at, reverse=True))

    def create(self, *, name: str, description: str = "", wells: tuple[str, ...] = ()) -> CorrelationWorkspace:
        now = _utc_now()
        workspace = CorrelationWorkspace(
            id=str(uuid4()), name=_clean(name, "Название", MAX_NAME, True),
            description=_clean(description, "Описание", MAX_NOTE),
            wells=self._normalize_wells(wells), ties=(), created_at=now, updated_at=now,
        )
        return self.save(workspace)

    def get(self, workspace_id: str) -> CorrelationWorkspace:
        clean_id = _uuid(workspace_id)
        path = self.directory / clean_id / "correlation.json"
        if not path.exists():
            raise KeyError(f"Корреляционный проект не найден: {clean_id}")
        return self._parse(self.store.read(path, expected_schema=CORRELATION_SCHEMA))

    def save(self, workspace: CorrelationWorkspace, *, expected_state_token: str = "", preserve_updated_at: bool = False) -> CorrelationWorkspace:
        if expected_state_token:
            current = self.get(workspace.id)
            if current.state_token != expected_state_token:
                raise ValueError("Корреляционный проект изменился после построения preview.")
        normalized = CorrelationWorkspace(
            id=_uuid(workspace.id), name=_clean(workspace.name, "Название", MAX_NAME, True),
            description=_clean(workspace.description, "Описание", MAX_NOTE),
            wells=self._normalize_wells(workspace.wells), ties=tuple(workspace.ties),
            created_at=workspace.created_at or _utc_now(),
            updated_at=(workspace.updated_at or _utc_now()) if preserve_updated_at else _utc_now(),
        )
        self.store.write(self.directory / normalized.id / "correlation.json", {
            "schema": CORRELATION_SCHEMA, "project_id": self.project_id, **asdict(normalized)
        })
        return normalized

    def delete(self, workspace_id: str) -> bool:
        import shutil
        path = self.directory / _uuid(workspace_id)
        if not path.exists():
            return False
        shutil.rmtree(path)
        return True

    def _parse(self, payload: Mapping[str, Any]) -> CorrelationWorkspace:
        if payload.get("schema") != CORRELATION_SCHEMA:
            raise ValueError("Неподдерживаемая схема корреляционного проекта.")
        ties = []
        for row in payload.get("ties", []):
            left = CorrelationEndpoint(**row["left"])
            right = CorrelationEndpoint(**row["right"])
            ties.append(CorrelationTie(
                id=_uuid(row.get("id")), left=left, right=right,
                name=str(row.get("name", "")), note=str(row.get("note", "")),
                color=self._normalize_color(row.get("color", "#1F77B4")),
                width=self._normalize_width(row.get("width", 2.0)),
                dash=self._normalize_dash(row.get("dash", "solid")),
                visible=bool(row.get("visible", True)),
                created_at=str(row.get("created_at", "")), updated_at=str(row.get("updated_at", "")),
            ))
        return CorrelationWorkspace(id=_uuid(payload.get("id")), name=str(payload.get("name", "")),
                                    description=str(payload.get("description", "")),
                                    wells=self._normalize_wells(tuple(payload.get("wells", ()))), ties=tuple(ties),
                                    created_at=str(payload.get("created_at", "")), updated_at=str(payload.get("updated_at", "")))

    @staticmethod
    def _normalize_wells(wells: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(safe_well_id(item) for item in wells if str(item).strip()))

    @staticmethod
    def _normalize_color(value: Any) -> str:
        color = str(value or "#1F77B4").strip().upper()
        if len(color) != 7 or not color.startswith("#"):
            raise ValueError("Цвет связи должен быть в формате #RRGGBB.")
        try:
            int(color[1:], 16)
        except ValueError as exc:
            raise ValueError("Цвет связи должен быть в формате #RRGGBB.") from exc
        return color

    @staticmethod
    def _normalize_width(value: Any) -> float:
        width = float(value)
        if not 0.5 <= width <= 8.0:
            raise ValueError("Толщина связи должна быть от 0.5 до 8.0.")
        return width

    @staticmethod
    def _normalize_dash(value: Any) -> str:
        dash = str(value or "solid").strip().lower()
        if dash not in TIE_DASHES:
            raise ValueError("Неподдерживаемый тип линии связи.")
        return dash


class CorrelationWorkspaceService:
    def __init__(
        self,
        *,
        root: Path | str = DEFAULT_PROJECTS_ROOT,
        project_id: str,
        workspace_id: str,
        io_metrics: RepositoryIOMetrics | None = None,
    ) -> None:
        self.root = Path(root)
        self.project_id = safe_project_id(project_id)
        self.repository = CorrelationWorkspaceRepository(
            root=root, project_id=project_id, io_metrics=io_metrics
        )
        self.workspace_id = _uuid(workspace_id)

    def add_tie(self, *, left: CorrelationEndpoint, right: CorrelationEndpoint, name: str = "", note: str = "",
                color: str = "#1F77B4", width: float = 2.0, dash: str = "solid", visible: bool = True,
                expected_state_token: str = "") -> CorrelationWorkspace:
        workspace = self.repository.get(self.workspace_id)
        self._validate_endpoints(left, right)
        now = _utc_now()
        tie = CorrelationTie(
            id=str(uuid4()), left=left, right=right,
            name=_clean(name, "Название связи", MAX_NAME) or f"{left.label} ↔ {right.label}",
            note=_clean(note, "Комментарий", MAX_NOTE),
            color=self.repository._normalize_color(color), width=self.repository._normalize_width(width),
            dash=self.repository._normalize_dash(dash), visible=bool(visible),
            created_at=now, updated_at=now,
        )
        updated = CorrelationWorkspace(id=workspace.id, name=workspace.name, description=workspace.description,
                                       wells=tuple((*workspace.wells, left.well_id, right.well_id)),
                                       ties=tuple((*workspace.ties, tie)), created_at=workspace.created_at, updated_at=workspace.updated_at)
        return self.repository.save(updated, expected_state_token=expected_state_token)

    def update_tie(self, tie_id: str, *, left_depth: float | None = None, right_depth: float | None = None,
                   name: str | None = None, note: str | None = None, color: str | None = None,
                   width: float | None = None, dash: str | None = None, visible: bool | None = None,
                   expected_state_token: str = "") -> CorrelationWorkspace:
        workspace = self.repository.get(self.workspace_id)
        clean_id = _uuid(tie_id)
        current = next((item for item in workspace.ties if item.id == clean_id), None)
        if current is None:
            raise KeyError("Корреляционная связь не найдена.")
        left = CorrelationEndpoint(**{**asdict(current.left), "depth": float(current.left.depth if left_depth is None else left_depth)})
        right = CorrelationEndpoint(**{**asdict(current.right), "depth": float(current.right.depth if right_depth is None else right_depth)})
        self._validate_endpoints(left, right)
        now = _utc_now()
        changed = CorrelationTie(
            id=current.id, left=left, right=right,
            name=current.name if name is None else (_clean(name, "Название связи", MAX_NAME) or f"{left.label} ↔ {right.label}"),
            note=current.note if note is None else _clean(note, "Комментарий", MAX_NOTE),
            color=current.color if color is None else self.repository._normalize_color(color),
            width=current.width if width is None else self.repository._normalize_width(width),
            dash=current.dash if dash is None else self.repository._normalize_dash(dash),
            visible=current.visible if visible is None else bool(visible),
            created_at=current.created_at, updated_at=now,
        )
        ties = tuple(changed if item.id == clean_id else item for item in workspace.ties)
        updated = CorrelationWorkspace(workspace.id, workspace.name, workspace.description, workspace.wells, ties, workspace.created_at, workspace.updated_at)
        return self.repository.save(updated, expected_state_token=expected_state_token)

    def delete_ties(self, tie_ids: tuple[str, ...], *, expected_state_token: str = "") -> CorrelationWorkspace:
        workspace = self.repository.get(self.workspace_id)
        selected = {_uuid(item) for item in tie_ids}
        ties = tuple(item for item in workspace.ties if item.id not in selected)
        if len(ties) == len(workspace.ties):
            raise KeyError("Корреляционные связи не найдены.")
        updated = CorrelationWorkspace(workspace.id, workspace.name, workspace.description, workspace.wells, ties, workspace.created_at, workspace.updated_at)
        return self.repository.save(updated, expected_state_token=expected_state_token)


    def add_ties(self, ties: tuple[CorrelationTie, ...], *, expected_state_token: str = "") -> CorrelationWorkspace:
        workspace = self.repository.get(self.workspace_id)
        if not ties:
            return workspace
        existing = {frozenset(((item.left.well_id, item.left.interval_id), (item.right.well_id, item.right.interval_id))) for item in workspace.ties}
        now = _utc_now()
        normalized: list[CorrelationTie] = []
        for item in ties:
            self._validate_endpoints(item.left, item.right)
            key = frozenset(((item.left.well_id, item.left.interval_id), (item.right.well_id, item.right.interval_id)))
            if key in existing:
                continue
            existing.add(key)
            normalized.append(CorrelationTie(
                id=_uuid(item.id), left=item.left, right=item.right,
                name=_clean(item.name, "Название связи", MAX_NAME) or f"{item.left.label} ↔ {item.right.label}",
                note=_clean(item.note, "Комментарий", MAX_NOTE),
                color=self.repository._normalize_color(item.color), width=self.repository._normalize_width(item.width),
                dash=self.repository._normalize_dash(item.dash), visible=bool(item.visible),
                created_at=item.created_at or now, updated_at=now,
            ))
        if not normalized:
            return workspace
        wells = tuple((*workspace.wells, *(endpoint.well_id for tie in normalized for endpoint in (tie.left, tie.right))))
        updated = CorrelationWorkspace(workspace.id, workspace.name, workspace.description, wells, tuple((*workspace.ties, *normalized)), workspace.created_at, workspace.updated_at)
        return self.repository.save(updated, expected_state_token=expected_state_token)

    def _validate_endpoints(self, left: CorrelationEndpoint, right: CorrelationEndpoint) -> None:
        if left.well_id == right.well_id:
            raise ValueError("Корреляционная связь должна соединять разные скважины.")
        inputs = {(item.well_id, item.interpretation_id, item.revision_id): item for item in discover_published_interpretations(root=self.root, project_id=self.project_id)}
        for endpoint in (left, right):
            source = inputs.get((endpoint.well_id, endpoint.interpretation_id, endpoint.revision_id))
            if source is None:
                raise ValueError("Источник корреляции больше не опубликован.")
            interval = next((item for item in source.intervals if item.id == endpoint.interval_id), None)
            if interval is None:
                raise ValueError("Интервал корреляции отсутствует в опубликованной ревизии.")
            if not interval.top <= float(endpoint.depth) <= interval.base:
                raise ValueError("Опорная глубина должна находиться внутри выбранного интервала.")

    def delete_tie(self, tie_id: str, *, expected_state_token: str = "") -> CorrelationWorkspace:
        workspace = self.repository.get(self.workspace_id)
        clean_id = _uuid(tie_id)
        ties = tuple(item for item in workspace.ties if item.id != clean_id)
        if len(ties) == len(workspace.ties):
            raise KeyError("Корреляционная связь не найдена.")
        updated = CorrelationWorkspace(id=workspace.id, name=workspace.name, description=workspace.description,
                                       wells=workspace.wells, ties=ties, created_at=workspace.created_at, updated_at=workspace.updated_at)
        return self.repository.save(updated, expected_state_token=expected_state_token)


def export_correlation_json(workspace: CorrelationWorkspace) -> bytes:
    return (json.dumps({"schema": CORRELATION_SCHEMA, **asdict(workspace)}, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def export_correlation_csv(workspace: CorrelationWorkspace) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=["tie_id", "name", "left_well", "left_depth", "left_label", "right_well", "right_depth", "right_label", "note"])
    writer.writeheader()
    for tie in workspace.ties:
        writer.writerow({"tie_id": tie.id, "name": tie.name, "left_well": tie.left.well_id, "left_depth": tie.left.depth,
                         "left_label": tie.left.label, "right_well": tie.right.well_id, "right_depth": tie.right.depth,
                         "right_label": tie.right.label, "note": tie.note})
    return ("\ufeff" + stream.getvalue()).encode("utf-8")
