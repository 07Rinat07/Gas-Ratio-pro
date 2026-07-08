from __future__ import annotations

import json

import pytest

from projects.repository import create_project
from projects.workspace_repository import (
    create_workspace,
    delete_workspace,
    list_workspaces,
    load_workspace,
    safe_workspace_id,
    update_workspace,
)
from services.workspace_service import WorkspaceService


def test_workspace_repository_crud_is_project_scoped(tmp_path):
    project = create_project(tmp_path, name="Demo Project", project_id="demo")

    workspace = create_workspace(
        tmp_path,
        project.id,
        name="LAS Workspace",
        kind="las",
        settings={"depth_unit": "m"},
        workspace_id="las-main",
    )
    loaded = load_workspace(tmp_path, project.id, "las-main")
    updated = update_workspace(tmp_path, project.id, "las-main", name="LAS Workspace 3.0", settings={"track": "GR"})

    assert workspace.project_id == "demo"
    assert loaded.name == "LAS Workspace"
    assert updated.name == "LAS Workspace 3.0"
    assert updated.settings == {"depth_unit": "m", "track": "GR"}
    assert list_workspaces(tmp_path, project.id)[0].id == "las-main"
    assert delete_workspace(tmp_path, project.id, "las-main") is True
    assert list_workspaces(tmp_path, project.id) == ()


def test_workspace_repository_rejects_invalid_ids_and_orphan_projects(tmp_path):
    with pytest.raises(ValueError):
        safe_workspace_id("bad/path")

    with pytest.raises(FileNotFoundError):
        create_workspace(tmp_path, "missing", name="Orphan")


def test_workspace_repository_ignores_corrupted_workspace_records(tmp_path):
    project = create_project(tmp_path, name="Demo", project_id="demo")
    broken_dir = tmp_path / project.id / "workspaces" / "broken"
    broken_dir.mkdir(parents=True)
    (broken_dir / "workspace.json").write_text("{broken", encoding="utf-8")

    assert list_workspaces(tmp_path, project.id) == ()


def test_workspace_service_wraps_repository_contract(tmp_path):
    project = create_project(tmp_path, name="Demo", project_id="demo")
    service = WorkspaceService(tmp_path)

    created = service.create_workspace(project.id, "Correlation", kind="correlation", workspace_id="corr")
    updated = service.update_workspace(project.id, "corr", description="Main correlation board")
    deleted = service.delete_workspace(project.id, "corr")

    assert created.project_exists is True
    assert created.workspace.kind == "correlation"
    assert updated.description == "Main correlation board"
    assert deleted.deleted is True


def test_workspace_service_preserves_json_storage_layout(tmp_path):
    project = create_project(tmp_path, name="Demo", project_id="demo")
    service = WorkspaceService(tmp_path)
    service.create_workspace(project.id, "Petrophysics", kind="petrophysics", workspace_id="petro")

    path = tmp_path / "demo" / "workspaces" / "petro" / "workspace.json"
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["id"] == "petro"
    assert payload["project_id"] == "demo"
    assert payload["kind"] == "petrophysics"
