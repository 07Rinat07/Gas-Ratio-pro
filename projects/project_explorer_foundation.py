from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Iterable

PROJECT_EXPLORER_SCHEMA = "gas-ratio-pro.project-explorer.v1"
OPERATION_JOURNAL_SCHEMA = "gas-ratio-pro.operation-journal.v1"


def utc_now() -> str:
    """Return an ISO UTC timestamp used by project explorer records."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class ProjectObjectType(str, Enum):
    PROJECT = "project"
    WELL = "well"
    LAS = "las"
    CURVE = "curve"
    INTERPRETATION = "interpretation"
    PLOT = "plot"
    CORRELATION = "correlation"
    REPORT = "report"
    SOURCE = "source"
    TEMPLATE = "template"
    MODEL = "model"
    CALCULATION = "calculation"
    SETTINGS = "settings"


class OperationStatus(str, Enum):
    PLANNED = "planned"
    PREVIEW = "preview"
    COMPLETED = "completed"
    FAILED = "failed"
    UNDONE = "undone"


@dataclass(frozen=True)
class ExplorerAction:
    """Action available for a selected object in Project Explorer."""

    action_id: str
    title: str
    description: str
    target_workspace: str
    requires_confirmation: bool = False
    creates_copy: bool = False
    destructive: bool = False


@dataclass(frozen=True)
class ProjectExplorerNode:
    """One tree node shown in the global Project Explorer."""

    node_id: str
    title: str
    object_type: ProjectObjectType
    object_id: str = ""
    parent_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    children: tuple["ProjectExplorerNode", ...] = ()

    def flatten(self) -> tuple["ProjectExplorerNode", ...]:
        """Return this node and all descendants in depth-first order."""
        nodes: list[ProjectExplorerNode] = [self]
        for child in self.children:
            nodes.extend(child.flatten())
        return tuple(nodes)


@dataclass(frozen=True)
class ProjectExplorerState:
    """Renderer-independent Project Explorer state."""

    schema: str
    project_id: str
    project_name: str
    root: ProjectExplorerNode
    selected_node_id: str = ""

    def all_nodes(self) -> tuple[ProjectExplorerNode, ...]:
        return self.root.flatten()

    def selected_node(self) -> ProjectExplorerNode | None:
        for node in self.all_nodes():
            if node.node_id == self.selected_node_id:
                return node
        return None


@dataclass(frozen=True)
class OperationJournalEntry:
    """Audit entry for user-visible operations.

    The journal is metadata-only. It records what the user requested, what was
    changed, whether a safe copy was produced and how the operation can be
    inspected later. Raw LAS data is intentionally not stored here.
    """

    operation_id: str
    operation_type: str
    title: str
    status: OperationStatus
    created_at: str
    source_object_id: str = ""
    result_object_id: str = ""
    creates_copy: bool = True
    can_undo: bool = False
    summary: str = ""
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class UndoRedoState:
    """Simple UI-ready Undo/Redo state for workspace toolbars."""

    can_undo: bool
    can_redo: bool
    undo_label: str = ""
    redo_label: str = ""


@dataclass(frozen=True)
class CurveQualityPreview:
    """Compact preview row for LAS curves in Project Explorer/Inspector."""

    curve: str
    unit: str = ""
    minimum: float | None = None
    maximum: float | None = None
    average: float | None = None
    null_count: int = 0
    quality: str = "unknown"
    visible: bool = True


def _safe_id(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in str(value).strip())
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("_") or "item"


def las_workspace_actions_for_node(node: ProjectExplorerNode | None) -> tuple[ExplorerAction, ...]:
    """Return contextual LAS actions for the selected Project Explorer node."""
    if node is None:
        return (
            ExplorerAction("create_las", "Создать LAS", "Создать новый LAS без заранее загруженного файла.", "las_workspace"),
            ExplorerAction("open_las", "Открыть LAS", "Загрузить существующий LAS-файл.", "las_workspace"),
        )

    if node.object_type == ProjectObjectType.WELL:
        return (
            ExplorerAction("create_las_for_well", "Создать LAS для скважины", "Создать новый LAS и привязать его к выбранной скважине.", "las_workspace"),
            ExplorerAction("append_las_to_well", "Добавить LAS", "Добавить существующий LAS к выбранной скважине.", "las_workspace"),
            ExplorerAction("multi_import", "Массовый импорт", "Импортировать несколько LAS-файлов в выбранную скважину.", "las_workspace"),
        )

    if node.object_type == ProjectObjectType.LAS:
        return (
            ExplorerAction("open_las_editor", "Открыть редактор", "Открыть LAS в профессиональном редакторе.", "las_workspace"),
            ExplorerAction("compare_las", "Сравнить LAS", "Сравнить выбранный LAS с другим файлом.", "las_workspace"),
            ExplorerAction("append_curves", "Вставить кривые", "Вставить ГИС/каротажные кривые из другого LAS.", "las_workspace", creates_copy=True),
            ExplorerAction("merge_las", "Срастить LAS", "Объединить несколько LAS-файлов одной скважины.", "las_workspace", requires_confirmation=True, creates_copy=True),
            ExplorerAction("depth_repair", "Исправить глубины", "Исправить убывающую/битую глубину с сохранением значений на исходных глубинах.", "las_workspace", requires_confirmation=True, creates_copy=True),
            ExplorerAction("export_las", "Экспорт", "Экспортировать LAS/CSV/XLSX/PDF/PNG и другие форматы.", "report_studio"),
        )

    if node.object_type == ProjectObjectType.CURVE:
        return (
            ExplorerAction("curve_statistics", "Статистика", "Показать статистику и качество выбранной кривой.", "las_workspace"),
            ExplorerAction("curve_preview", "Предпросмотр", "Показать мини-график и диапазон значений.", "plot_studio"),
        )

    return ()


def build_project_explorer_state(
    *,
    project_id: str,
    project_name: str,
    wells: Iterable[dict[str, Any]] = (),
    sources_count: int = 0,
    templates_count: int = 0,
    selected_node_id: str = "",
) -> ProjectExplorerState:
    """Build a Project Explorer tree from lightweight well/LAS metadata.

    wells item example:
    {"id": "well_001", "name": "Well-001", "las_files": [{"id": "las_1", "name": "main.las", "curves": ["DEPT", "GR"]}]}
    """
    well_nodes: list[ProjectExplorerNode] = []
    for well in wells:
        well_id = _safe_id(str(well.get("id") or well.get("name") or "well"))
        las_nodes: list[ProjectExplorerNode] = []
        for las in well.get("las_files", []) or []:
            las_id = _safe_id(str(las.get("id") or las.get("name") or "las"))
            curve_nodes = tuple(
                ProjectExplorerNode(
                    node_id=f"curve:{well_id}:{las_id}:{_safe_id(str(curve))}",
                    title=str(curve),
                    object_type=ProjectObjectType.CURVE,
                    object_id=str(curve),
                    parent_id=f"las:{well_id}:{las_id}",
                )
                for curve in (las.get("curves", []) or [])
            )
            las_nodes.append(
                ProjectExplorerNode(
                    node_id=f"las:{well_id}:{las_id}",
                    title=str(las.get("name") or las_id),
                    object_type=ProjectObjectType.LAS,
                    object_id=las_id,
                    parent_id=f"well:{well_id}",
                    metadata={"path": str(las.get("path", "")), "curve_count": len(curve_nodes)},
                    children=curve_nodes,
                )
            )
        well_nodes.append(
            ProjectExplorerNode(
                node_id=f"well:{well_id}",
                title=str(well.get("name") or well_id),
                object_type=ProjectObjectType.WELL,
                object_id=well_id,
                parent_id="project:root",
                metadata={"las_count": len(las_nodes)},
                children=tuple(las_nodes),
            )
        )

    root = ProjectExplorerNode(
        node_id="project:root",
        title=project_name.strip() or project_id,
        object_type=ProjectObjectType.PROJECT,
        object_id=project_id,
        children=(
            ProjectExplorerNode("folder:wells", "Скважины", ProjectObjectType.WELL, "wells", "project:root", children=tuple(well_nodes)),
            ProjectExplorerNode("folder:sources", f"Источники ({sources_count})", ProjectObjectType.SOURCE, "sources", "project:root"),
            ProjectExplorerNode("folder:templates", f"Шаблоны ({templates_count})", ProjectObjectType.TEMPLATE, "templates", "project:root"),
            ProjectExplorerNode("folder:reports", "Отчеты", ProjectObjectType.REPORT, "reports", "project:root"),
            ProjectExplorerNode("folder:settings", "Настройки", ProjectObjectType.SETTINGS, "settings", "project:root"),
        ),
    )
    return ProjectExplorerState(PROJECT_EXPLORER_SCHEMA, project_id, project_name, root, selected_node_id)


def explorer_table_rows(state: ProjectExplorerState) -> list[dict[str, Any]]:
    """Return flat rows that Streamlit/desktop UI can render in a tree table."""
    rows: list[dict[str, Any]] = []
    for node in state.all_nodes():
        depth = 0 if not node.parent_id else node.node_id.count(":")
        rows.append(
            {
                "node_id": node.node_id,
                "parent_id": node.parent_id,
                "title": node.title,
                "object_type": node.object_type.value,
                "object_id": node.object_id,
                "depth": depth,
                "metadata": node.metadata,
                "selected": node.node_id == state.selected_node_id,
            }
        )
    return rows


def build_operation_entry(
    *,
    operation_type: str,
    title: str,
    source_object_id: str = "",
    result_object_id: str = "",
    status: OperationStatus = OperationStatus.PREVIEW,
    creates_copy: bool = True,
    can_undo: bool = False,
    summary: str = "",
    details: dict[str, Any] | None = None,
) -> OperationJournalEntry:
    now = utc_now()
    op_id = f"op-{now.replace(':', '').replace('-', '').replace('T', '-').replace('Z', '')}-{_safe_id(operation_type)}"
    return OperationJournalEntry(
        operation_id=op_id,
        operation_type=operation_type.strip() or "operation",
        title=title.strip() or operation_type.strip() or "Operation",
        status=status,
        created_at=now,
        source_object_id=source_object_id,
        result_object_id=result_object_id,
        creates_copy=creates_copy,
        can_undo=can_undo,
        summary=summary,
        details=dict(details or {}),
    )


def operation_journal_rows(entries: Iterable[OperationJournalEntry]) -> list[dict[str, Any]]:
    return [
        {
            "operation_id": entry.operation_id,
            "operation_type": entry.operation_type,
            "title": entry.title,
            "status": entry.status.value,
            "created_at": entry.created_at,
            "source_object_id": entry.source_object_id,
            "result_object_id": entry.result_object_id,
            "creates_copy": entry.creates_copy,
            "can_undo": entry.can_undo,
            "summary": entry.summary,
        }
        for entry in entries
    ]


def undo_redo_state(entries: Iterable[OperationJournalEntry]) -> UndoRedoState:
    completed = [entry for entry in entries if entry.status == OperationStatus.COMPLETED and entry.can_undo]
    undone = [entry for entry in entries if entry.status == OperationStatus.UNDONE]
    return UndoRedoState(
        can_undo=bool(completed),
        can_redo=bool(undone),
        undo_label=completed[0].title if completed else "",
        redo_label=undone[0].title if undone else "",
    )
