from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from projects.project_folders import ProjectFolder, assign_project_items_to_folder, list_project_folders
from projects.project_tree import ProjectTreeNode, build_project_tree, flatten_project_tree
from projects.repository import DEFAULT_PROJECT_ID, DEFAULT_PROJECTS_ROOT
from projects.well_groups import ProjectWellGroup, assign_project_wells_to_group, list_project_well_groups


@dataclass(frozen=True)
class ProjectExplorerMoveOption:
    """One metadata-only object that can be moved from Project Explorer controls.

    The option stores the stable ProjectTree node id, not raw LAS bytes or full
    calculation tables. UI code can use this as a safe replacement for true
    drag-and-drop where the frontend framework does not expose native draggable
    tree nodes.
    """

    id: str
    label: str
    kind: str
    target_type: str
    description: str = ""


@dataclass(frozen=True)
class ProjectExplorerMoveResult:
    """Result of one Project Explorer metadata move operation."""

    source_id: str
    target_id: str
    target_type: str
    message: str
    updated_folder: ProjectFolder | None = None
    updated_group: ProjectWellGroup | None = None


def _node_options(tree: ProjectTreeNode) -> tuple[ProjectExplorerMoveOption, ...]:
    options: list[ProjectExplorerMoveOption] = []
    for _level, node in flatten_project_tree(tree):
        if node.kind == "well":
            options.append(
                ProjectExplorerMoveOption(
                    id=node.id,
                    label=node.label,
                    kind=node.kind,
                    target_type="well_group_or_folder",
                    description="Скважину можно переместить в группу скважин или добавить в папку.",
                )
            )
        elif node.kind in {"las_version", "calculation", "export"}:
            options.append(
                ProjectExplorerMoveOption(
                    id=node.id,
                    label=node.label,
                    kind=node.kind,
                    target_type="folder",
                    description="Объект можно добавить в пользовательскую папку без копирования файла.",
                )
            )
    return tuple(options)


def list_project_explorer_move_options(
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
) -> tuple[ProjectExplorerMoveOption, ...]:
    """Return project objects that can be moved by Project Explorer controls."""

    return _node_options(build_project_tree(root, project_id))


def list_project_explorer_folder_targets(
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
) -> tuple[ProjectFolder, ...]:
    """Return saved folders that can receive Project Explorer object links."""

    return list_project_folders(root, project_id)


def list_project_explorer_well_group_targets(
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
) -> tuple[ProjectWellGroup, ...]:
    """Return saved well groups that can receive well objects."""

    return tuple(group for group in list_project_well_groups(root, project_id) if group.id != "ungrouped")


def move_project_explorer_item_to_folder(
    root: Path | str,
    project_id: str,
    item_id: str,
    folder_id: str,
) -> ProjectExplorerMoveResult:
    """Append a Project Explorer item reference to a saved custom folder.

    Existing folder order is preserved and duplicates are removed by the folder
    assignment service. The operation is metadata-only: it does not duplicate LAS
    files, exports or calculation snapshots.
    """

    clean_item_id = str(item_id).strip()
    folders = {folder.id: folder for folder in list_project_folders(root, project_id)}
    folder = folders.get(str(folder_id).strip())
    if folder is None:
        raise ValueError("Папка проекта не найдена.")

    updated = assign_project_items_to_folder(
        root=root,
        project_id=project_id,
        folder_id=folder.id,
        item_ids=(*folder.item_ids, clean_item_id),
    )
    return ProjectExplorerMoveResult(
        source_id=clean_item_id,
        target_id=updated.id,
        target_type="folder",
        message=f"Объект добавлен в папку: {updated.name}",
        updated_folder=updated,
    )


def move_project_explorer_well_to_group(
    root: Path | str,
    project_id: str,
    well_node_id: str,
    group_id: str,
) -> ProjectExplorerMoveResult:
    """Move one well from its current group into another saved well group."""

    clean_node_id = str(well_node_id).strip()
    if not clean_node_id.startswith("well:"):
        raise ValueError("В группу скважин можно перемещать только объект скважины.")
    well_id = clean_node_id.split(":", 1)[1]
    updated = assign_project_wells_to_group(
        root=root,
        project_id=project_id,
        group_id=str(group_id).strip(),
        well_ids=(well_id,),
    )
    return ProjectExplorerMoveResult(
        source_id=clean_node_id,
        target_id=updated.id,
        target_type="well_group",
        message=f"Скважина перемещена в группу: {updated.name}",
        updated_group=updated,
    )
