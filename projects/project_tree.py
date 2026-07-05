from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from projects.calculations import list_project_calculations
from projects.exports import list_project_exports
from projects.las_files import ProjectLasWellCard, list_project_las_wells
from projects.well_groups import list_grouped_project_wells
from projects.repository import DEFAULT_PROJECT_ID, DEFAULT_PROJECTS_ROOT, ProjectRecord, load_project, safe_project_id


@dataclass(frozen=True)
class ProjectTreeNode:
    """Compact project explorer node.

    The first implementation is intentionally read-only and metadata-only: it
    indexes persisted project objects without opening raw LAS/calculation rows.
    Later Project Explorer stages can add folders, tags and drag-and-drop on top
    of this stable node contract.
    """

    id: str
    label: str
    kind: str
    status: str = ""
    children: tuple["ProjectTreeNode", ...] = field(default_factory=tuple)
    metadata: dict[str, str | int] = field(default_factory=dict)

    @property
    def count(self) -> int:
        return len(self.children)

    @property
    def is_leaf(self) -> bool:
        return not self.children


def _folder_node(node_id: str, label: str, children: tuple[ProjectTreeNode, ...]) -> ProjectTreeNode:
    return ProjectTreeNode(
        id=node_id,
        label=label,
        kind="folder",
        status=f"{len(children)} объект(ов)",
        children=children,
        metadata={"count": len(children)},
    )


def _empty_node(node_id: str, label: str) -> ProjectTreeNode:
    return ProjectTreeNode(
        id=node_id,
        label=label,
        kind="empty",
        status="пока нет данных",
    )


def flatten_project_tree(node: ProjectTreeNode, level: int = 0) -> tuple[tuple[int, ProjectTreeNode], ...]:
    """Return a stable preorder representation for UI tables and tests."""

    rows: list[tuple[int, ProjectTreeNode]] = [(level, node)]
    for child in node.children:
        rows.extend(flatten_project_tree(child, level + 1))
    return tuple(rows)


def _well_node(well: ProjectLasWellCard) -> ProjectTreeNode:
    versions = tuple(
        ProjectTreeNode(
            id=f"las:{version.id}",
            label=version.version_label or version.original_file_name,
            kind="las_version",
            status=version.saved_at,
            metadata={
                "las_file_id": version.id,
                "file_name": version.original_file_name,
                "size_bytes": version.size_bytes,
            },
        )
        for version in well.versions
    )
    return ProjectTreeNode(
        id=f"well:{well.id}",
        label=well.name,
        kind="well",
        status=f"{len(versions)} LAS-версий",
        children=versions or (_empty_node(f"well:{well.id}:empty", "Нет LAS-версий"),),
        metadata={"well_id": well.id, "version_count": len(versions)},
    )


def build_project_tree(
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
) -> ProjectTreeNode:
    """Build a read-only Project Explorer tree for the selected project.

    The tree contains only project metadata and saved object cards. It does not
    read full calculation tables or LAS payloads, so rendering the sidebar stays
    safe for large projects.
    """

    root_path = Path(root)
    clean_project_id = safe_project_id(project_id)
    project = load_project(root_path, clean_project_id)

    well_children: list[ProjectTreeNode] = []
    for group, wells in list_grouped_project_wells(root_path, clean_project_id):
        group_well_nodes = tuple(_well_node(well) for well in wells)
        well_children.append(
            ProjectTreeNode(
                id=f"well_group:{group.id}",
                label=group.name,
                kind="well_group",
                status=f"{len(group_well_nodes)} скважин",
                children=group_well_nodes or (_empty_node(f"well_group:{group.id}:empty", "Нет скважин в группе"),),
                metadata={
                    "group_id": group.id,
                    "well_count": len(group_well_nodes),
                    "description": group.description,
                },
            )
        )

    calculation_children = tuple(
        ProjectTreeNode(
            id=f"calculation:{record.id}",
            label=record.source_label or record.id,
            kind="calculation",
            status=f"{record.row_count} строк; предупреждений: {record.warnings_count}",
            metadata={
                "calculation_id": record.id,
                "row_count": record.row_count,
                "warnings_count": record.warnings_count,
                "ch_mode": record.ch_mode,
            },
        )
        for record in list_project_calculations(root_path, clean_project_id)
    )

    export_children = tuple(
        ProjectTreeNode(
            id=f"export:{record.id}",
            label=record.label or record.file_name,
            kind="export",
            status=f"{record.kind or 'export'}; {record.file_name}",
            metadata={
                "export_id": record.id,
                "file_name": record.file_name,
                "size_bytes": record.size_bytes,
                "mime_type": record.mime_type,
            },
        )
        for record in list_project_exports(root_path, clean_project_id)
    )

    wells_folder = _folder_node(
        "folder:wells",
        "Скважины",
        tuple(well_children) or (_empty_node("folder:wells:empty", "Нет сохраненных скважин"),),
    )
    calculations_folder = _folder_node(
        "folder:calculations",
        "Расчеты",
        calculation_children or (_empty_node("folder:calculations:empty", "Нет сохраненных расчетов"),),
    )
    exports_folder = _folder_node(
        "folder:exports",
        "Отчеты и экспорты",
        export_children or (_empty_node("folder:exports:empty", "Нет сохраненных экспортов"),),
    )

    return ProjectTreeNode(
        id=f"project:{project.id}",
        label=project.name,
        kind="project",
        status=project.updated_at,
        children=(wells_folder, calculations_folder, exports_folder),
        metadata={
            "project_id": project.id,
            "description": project.description,
            "created_at": project.created_at,
            "updated_at": project.updated_at,
        },
    )


def project_tree_table_rows(tree: ProjectTreeNode) -> tuple[dict[str, str | int], ...]:
    """Convert a tree to simple rows suitable for Streamlit/dataframe previews."""

    return tuple(
        {
            "level": level,
            "kind": node.kind,
            "label": node.label,
            "status": node.status,
            "id": node.id,
        }
        for level, node in flatten_project_tree(tree)
    )
