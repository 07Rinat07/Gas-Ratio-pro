from __future__ import annotations

from projects.recent_projects import (
    clear_recent_projects,
    list_recent_projects,
    recent_projects_table_rows,
    remove_recent_project,
    set_recent_project_flags,
    touch_recent_project,
)
from projects.repository import create_project


def test_recent_projects_history_is_separate_from_project_storage(tmp_path):
    root = tmp_path / "projects"
    project = create_project(root, name="Alpha")

    entry = touch_recent_project(root, project)
    assert entry.project_id == project.id
    assert list_recent_projects(root)[0].project_id == project.id

    assert remove_recent_project(root, project.id) is True
    assert list_recent_projects(root, include_missing=True) == ()
    assert (root / project.id / "project.json").exists()


def test_recent_projects_clear_history_does_not_delete_projects(tmp_path):
    root = tmp_path / "projects"
    first = create_project(root, name="First")
    second = create_project(root, name="Second")
    touch_recent_project(root, first)
    touch_recent_project(root, second)

    removed = clear_recent_projects(root)

    assert removed == 2
    assert list_recent_projects(root, include_missing=True) == ()
    assert (root / first.id / "project.json").exists()
    assert (root / second.id / "project.json").exists()


def test_recent_project_flags_and_table_rows(tmp_path):
    root = tmp_path / "projects"
    project = create_project(root, name="Pinned")
    touch_recent_project(root, project)

    updated = set_recent_project_flags(root, project.id, pinned=True, favorite=True)
    rows = recent_projects_table_rows(list_recent_projects(root))

    assert updated.pinned is True
    assert updated.favorite is True
    assert rows[0]["Закреплен"] == "да"
    assert rows[0]["Избранное"] == "да"
