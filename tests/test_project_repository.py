from __future__ import annotations

import pytest

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
