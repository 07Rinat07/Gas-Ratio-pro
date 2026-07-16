from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter

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
        drilling_dates = card.drilling_dates
        operator = card.operator
        field = card.field
        if coords.has_any:
            coordinate_label = "; ".join(label for label in (coords.projected_label, coords.geographic_label) if label)
            status_parts.append(f"координаты: {coordinate_label}")
        status_parts.extend(depth_reference.datum_labels)
        status_parts.extend(depth_reference.td_labels)
        if depth_reference.kb_above_gl_label:
            status_parts.append(depth_reference.kb_above_gl_label)
        status_parts.extend(drilling_dates.labels)
        status_parts.extend(operator.labels)
        status_parts.extend(field.labels)
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
        if depth_reference.gl_m is not None:
            metadata["gl_m"] = str(depth_reference.gl_m)
        if depth_reference.planned_td_m is not None:
            metadata["planned_td_m"] = str(depth_reference.planned_td_m)
        if depth_reference.actual_td_m is not None:
            metadata["actual_td_m"] = str(depth_reference.actual_td_m)
        if depth_reference.kb_above_gl_m is not None:
            metadata["kb_above_gl_m"] = str(depth_reference.kb_above_gl_m)
        if drilling_dates.spud_date is not None:
            metadata["spud_date"] = drilling_dates.spud_date
        if operator.operator is not None:
            metadata["operator"] = operator.operator
        if field.field is not None:
            metadata["field"] = field.field
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
    *,
    include_sections: set[str] | frozenset[str] | None = None,
    section_timings_ms: dict[str, float] | None = None,
) -> ProjectTreeNode:
    """Build a read-only Project Explorer tree for the selected project.

    The tree contains only project metadata and saved object cards. It does not
    read full calculation tables or LAS payloads, so rendering the sidebar stays
    safe for large projects.
    """

    root_path = Path(root)
    clean_project_id = safe_project_id(project_id)
    def _measure(section: str, operation):
        started = perf_counter()
        try:
            return operation()
        finally:
            if section_timings_ms is not None:
                section_timings_ms[section] = round((perf_counter() - started) * 1000.0, 3)

    project = _measure("project", lambda: load_project(root_path, clean_project_id))
    requested_sections = (
        frozenset({"custom", "wells", "calculations", "exports"})
        if include_sections is None
        else frozenset(str(item).strip() for item in include_sections)
    )
    # Custom folders may reference any object type, therefore their expansion
    # materializes the indexed source sections as one coherent metadata view.
    if "custom" in requested_sections:
        requested_sections = requested_sections | {"wells", "calculations", "exports"}

    indexed_nodes: dict[str, ProjectTreeNode] = {}
    well_cards = (
        _measure("well_cards", lambda: project_well_cards_by_id(root_path, clean_project_id))
        if "wells" in requested_sections else {}
    )
    well_children: list[ProjectTreeNode] = []
    grouped_wells = (
        _measure("wells", lambda: list_grouped_project_wells(root_path, clean_project_id))
        if "wells" in requested_sections else ()
    )
    for group, wells in grouped_wells:
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
        for record in (
            _measure("calculations", lambda: list_project_calculations(root_path, clean_project_id))
            if "calculations" in requested_sections else ()
        )
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
        for record in (
            _measure("exports", lambda: list_project_exports(root_path, clean_project_id))
            if "exports" in requested_sections else ()
        )
    )
    indexed_nodes.update((node.id, node) for node in export_children)

    custom_folder_children = tuple(
        _custom_folder_node(folder, indexed_nodes)
        for folder in (
            _measure("custom", lambda: list_project_folders(root_path, clean_project_id))
            if "custom" in requested_sections else ()
        )
    )

    def _deferred(folder_id: str, label: str) -> tuple[ProjectTreeNode, ...]:
        return (ProjectTreeNode(
            id=f"{folder_id}:deferred",
            label=label,
            kind="empty",
            status="загрузится при раскрытии",
            metadata={"deferred": 1},
        ),)

    custom_folders_folder = _folder_node(
        "folder:custom",
        "Папки",
        custom_folder_children or (
            _empty_node("folder:custom:empty", "Нет пользовательских папок")
            if "custom" in requested_sections else _deferred("folder:custom", "Раскройте ветку для загрузки")[0]
        ,),
    )
    wells_folder = _folder_node(
        "folder:wells",
        "Скважины",
        tuple(well_children) or (
            _empty_node("folder:wells:empty", "Нет сохраненных скважин")
            if "wells" in requested_sections else _deferred("folder:wells", "Раскройте ветку для загрузки")[0]
        ,),
    )
    calculations_folder = _folder_node(
        "folder:calculations",
        "Расчеты",
        calculation_children or (
            _empty_node("folder:calculations:empty", "Нет сохраненных расчетов")
            if "calculations" in requested_sections else _deferred("folder:calculations", "Раскройте ветку для загрузки")[0]
        ,),
    )
    exports_folder = _folder_node(
        "folder:exports",
        "Отчеты и экспорты",
        export_children or (
            _empty_node("folder:exports:empty", "Нет сохраненных экспортов")
            if "exports" in requested_sections else _deferred("folder:exports", "Раскройте ветку для загрузки")[0]
        ,),
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
    return _measure(
        "labels",
        lambda: _apply_project_labels(
            tree, project_explorer_labels_by_object(root_path, clean_project_id)
        ),
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
            "color_label": str(node.metadata.get("color_label", "")),
            "color_label_name": str(node.metadata.get("color_label_name", "")),
            "color_label_icon": str(node.metadata.get("color_label_icon", "")),
        }
        for level, node in flatten_project_tree(tree)
    )
