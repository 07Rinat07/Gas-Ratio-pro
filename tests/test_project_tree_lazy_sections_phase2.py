from __future__ import annotations

import projects.project_tree as project_tree_module
from projects import create_project, flatten_project_tree


def test_root_only_project_tree_skips_heavy_section_repositories(tmp_path, monkeypatch) -> None:
    project = create_project(tmp_path, name="Lazy Project", project_id="lazy")

    def unexpected(*_args, **_kwargs):
        raise AssertionError("collapsed Project Explorer section was read eagerly")

    monkeypatch.setattr(project_tree_module, "project_well_cards_by_id", unexpected)
    monkeypatch.setattr(project_tree_module, "list_grouped_project_wells", unexpected)
    monkeypatch.setattr(project_tree_module, "list_project_calculations", unexpected)
    monkeypatch.setattr(project_tree_module, "list_project_exports", unexpected)
    monkeypatch.setattr(project_tree_module, "list_project_folders", unexpected)

    tree = project_tree_module.build_project_tree(
        tmp_path,
        project.id,
        include_sections=set(),
    )
    rows = [node for _level, node in flatten_project_tree(tree)]

    assert tree.label == "Lazy Project"
    assert {node.id for node in rows if node.metadata.get("deferred")} == {
        "folder:custom:deferred",
        "folder:wells:deferred",
        "folder:calculations:deferred",
        "folder:datasets:deferred",
        "folder:imports:deferred",
        "folder:exports:deferred",
    }


def test_expanding_one_section_reads_only_that_section(tmp_path, monkeypatch) -> None:
    project = create_project(tmp_path, name="Lazy Project", project_id="lazy")
    calls: list[str] = []

    monkeypatch.setattr(
        project_tree_module,
        "list_project_calculations",
        lambda *_args, **_kwargs: calls.append("calculations") or (),
    )

    def unexpected(*_args, **_kwargs):
        raise AssertionError("unrequested Project Explorer section was read")

    monkeypatch.setattr(project_tree_module, "project_well_cards_by_id", unexpected)
    monkeypatch.setattr(project_tree_module, "list_grouped_project_wells", unexpected)
    monkeypatch.setattr(project_tree_module, "list_project_exports", unexpected)
    monkeypatch.setattr(project_tree_module, "list_project_folders", unexpected)

    tree = project_tree_module.build_project_tree(
        tmp_path,
        project.id,
        include_sections={"calculations"},
    )
    by_id = {node.id: node for _level, node in flatten_project_tree(tree)}

    assert calls == ["calculations"]
    assert by_id["folder:calculations:empty"].status == "пока нет данных"
    assert by_id["folder:wells:deferred"].metadata["deferred"] == 1
