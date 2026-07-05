from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from projects.calculations import list_project_calculations
from projects.exports import list_project_exports
from projects.las_files import ProjectLasWellCard, list_project_las_wells
from projects.project_folders import ProjectFolder, list_project_folders
from projects.project_labels import ProjectExplorerLabel, project_explorer_labels_by_object
from projects.well_cards import ProjectWellCard, project_well_cards_by_id
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



def _label_lookup_id(node: ProjectTreeNode) -> str:
    """Return the original object id used for inherited color labels."""

    item_id = node.metadata.get("item_id")
    if isinstance(item_id, str) and item_id:
        return item_id
    source_id = node.metadata.get("source_id")
    if isinstance(source_id, str) and source_id:
        return source_id
    return node.id


def _apply_project_labels(
    node: ProjectTreeNode,
    labels: dict[str, ProjectExplorerLabel],
) -> ProjectTreeNode:
    """Attach color label metadata to tree nodes without changing payloads."""

    children = tuple(_apply_project_labels(child, labels) for child in node.children)
    label = labels.get(_label_lookup_id(node))
    if label is None and children == node.children:
        return node

    metadata = dict(node.metadata)
    if label is not None:
        metadata.update(
            {
                "color_label": label.color,
                "color_label_name": label.color_name,
                "color_label_icon": label.icon,
                "color_label_note": label.note,
            }
        )
    return ProjectTreeNode(
        id=node.id,
        label=node.label,
        kind=node.kind,
        status=node.status,
        children=children,
        metadata=metadata,
    )

def flatten_project_tree(node: ProjectTreeNode, level: int = 0) -> tuple[tuple[int, ProjectTreeNode], ...]:
    """Return a stable preorder representation for UI tables and tests."""

    rows: list[tuple[int, ProjectTreeNode]] = [(level, node)]
    for child in node.children:
        rows.extend(flatten_project_tree(child, level + 1))
    return tuple(rows)


def _folder_item_node(folder: ProjectFolder, item_id: str, indexed_nodes: dict[str, ProjectTreeNode]) -> ProjectTreeNode:
    source = indexed_nodes.get(item_id)
    if source is None:
        return ProjectTreeNode(
            id=f"folder:{folder.id}:missing:{item_id}",
            label=item_id,
            kind="missing",
            status="объект не найден",
            metadata={"folder_id": folder.id, "item_id": item_id},
        )
    return ProjectTreeNode(
        id=f"folder:{folder.id}:item:{item_id}",
        label=source.label,
        kind="folder_item",
        status=source.status,
        metadata={
            "folder_id": folder.id,
            "item_id": item_id,
            "source_kind": source.kind,
            "source_id": source.id,
        },
    )


def _custom_folder_node(folder: ProjectFolder, indexed_nodes: dict[str, ProjectTreeNode]) -> ProjectTreeNode:
    children = tuple(_folder_item_node(folder, item_id, indexed_nodes) for item_id in folder.item_ids)
    return ProjectTreeNode(
        id=f"folder:custom:{folder.id}",
        label=folder.name,
        kind="custom_folder",
        status=f"{len(children)} объект(ов)",
        children=children or (_empty_node(f"folder:custom:{folder.id}:empty", "Нет объектов в папке"),),
        metadata={
            "folder_id": folder.id,
            "count": len(children),
            "description": folder.description,
        },
    )


def _well_node(well: ProjectLasWellCard, card: ProjectWellCard | None = None) -> ProjectTreeNode:
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
    status_parts = [f"{len(versions)} LAS-версий"]
    metadata: dict[str, str | int] = {"well_id": well.id, "version_count": len(versions)}
    if card is not None:
        status_parts.append(f"карточка: {card.status_label}")
        coords = card.coordinates
        depth_reference = card.depth_reference
        if coords.has_any:
            coordinate_label = "; ".join(label for label in (coords.projected_label, coords.geographic_label) if label)
            status_parts.append(f"координаты: {coordinate_label}")
        if depth_reference.has_kb:
            status_parts.append(depth_reference.kb_label)
        metadata.update(
            {
                "well_card_status": card.status,
                "well_card_status_label": card.status_label,
                "well_card_updated_at": card.updated_at,
            }
        )
        if coords.x is not None:
            metadata["coordinate_x"] = str(coords.x)
        if coords.y is not None:
            metadata["coordinate_y"] = str(coords.y)
        if coords.latitude is not None:
            metadata["latitude"] = str(coords.latitude)
        if coords.longitude is not None:
            metadata["longitude"] = str(coords.longitude)
        if depth_reference.kb_m is not None:
            metadata["kb_m"] = str(depth_reference.kb_m)
    return ProjectTreeNode(
        id=f"well:{well.id}",
        label=card.name if card is not None and card.name else well.name,
        kind="well",
        status="; ".join(status_parts),
        children=versions or (_empty_node(f"well:{well.id}:empty", "Нет LAS-версий"),),
        metadata=metadata,
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

    indexed_nodes: dict[str, ProjectTreeNode] = {}
    well_cards = project_well_cards_by_id(root_path, clean_project_id)
    well_children: list[ProjectTreeNode] = []
    for group, wells in list_grouped_project_wells(root_path, clean_project_id):
        group_well_nodes = tuple(_well_node(well, well_cards.get(well.id)) for well in wells)
        for well_node in group_well_nodes:
            indexed_nodes[well_node.id] = well_node
            for version_node in well_node.children:
                if version_node.kind == "las_version":
                    indexed_nodes[version_node.id] = version_node
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
    indexed_nodes.update((node.id, node) for node in calculation_children)

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
    indexed_nodes.update((node.id, node) for node in export_children)

    custom_folder_children = tuple(
        _custom_folder_node(folder, indexed_nodes)
        for folder in list_project_folders(root_path, clean_project_id)
    )

    custom_folders_folder = _folder_node(
        "folder:custom",
        "Папки",
        custom_folder_children or (_empty_node("folder:custom:empty", "Нет пользовательских папок"),),
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

    tree = ProjectTreeNode(
        id=f"project:{project.id}",
        label=project.name,
        kind="project",
        status=project.updated_at,
        children=(custom_folders_folder, wells_folder, calculations_folder, exports_folder),
        metadata={
            "project_id": project.id,
            "description": project.description,
            "created_at": project.created_at,
            "updated_at": project.updated_at,
        },
    )
    return _apply_project_labels(tree, project_explorer_labels_by_object(root_path, clean_project_id))


def project_tree_table_rows(tree: ProjectTreeNode) -> tuple[dict[str, str | int], ...]:
    """Convert a tree to simple rows suitable for Streamlit/dataframe previews."""

    return tuple(
        {
            "level": level,
            "kind": node.kind,
            "label": node.label,
            "status": node.status,
            "id": node.id,
            "color_label": str(node.metadata.get("color_label", "")),
            "color_label_name": str(node.metadata.get("color_label_name", "")),
            "color_label_icon": str(node.metadata.get("color_label_icon", "")),
        }
        for level, node in flatten_project_tree(tree)
    )
