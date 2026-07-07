from __future__ import annotations

import pytest

from app.streamlit_app import ACTIVE_PROJECT_ID_KEY, _project_selectbox_key
from projects import DEFAULT_PROJECT_ID, create_project, ensure_default_project, list_projects, load_project


def test_ensure_default_project_creates_project_manifest(tmp_path):
    project = ensure_default_project(tmp_path)
    loaded = load_project(tmp_path, DEFAULT_PROJECT_ID)

    assert project.id == DEFAULT_PROJECT_ID
    assert loaded.name == "Основной проект"
    assert (tmp_path / DEFAULT_PROJECT_ID / "project.json").exists()


def test_create_project_uses_unique_ids_and_lists_projects(tmp_path):
    first = create_project(tmp_path, name="Demo Project", description="A")
    second = create_project(tmp_path, name="Demo Project", description="B")
    projects = list_projects(tmp_path)

    assert first.id != second.id
    assert {project.id for project in projects} == {first.id, second.id}
    assert load_project(tmp_path, first.id).description == "A"


def test_create_project_rejects_unsafe_project_id(tmp_path):
    with pytest.raises(ValueError, match="Некорректный идентификатор проекта"):
        create_project(tmp_path, name="Bad", project_id="../bad")


def test_project_selectbox_key_is_decoupled_from_active_project_state():
    project_ids = ("default", "demo")

    assert _project_selectbox_key("default", project_ids) != ACTIVE_PROJECT_ID_KEY
    assert _project_selectbox_key("default", project_ids) != _project_selectbox_key("demo", project_ids)

from projects import delete_project


def test_delete_project_removes_project_directory(tmp_path):
    project = create_project(tmp_path, name="To Delete")

    assert delete_project(tmp_path, project.id) is True
    assert not (tmp_path / project.id).exists()
