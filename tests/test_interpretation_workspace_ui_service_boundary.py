from __future__ import annotations

import ast
from pathlib import Path


def test_interpretation_panel_does_not_import_persistence_repositories() -> None:
    source_path = Path("ui/interpretation_interval_panel.py")
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    forbidden = {
        "projects.interpretation_catalog",
        "projects.interpretation_revisions",
        "projects.interpretation_interval_types",
    }
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert imports.isdisjoint(forbidden)
    assert "InterpretationIntervalFilterPresetRepository" not in source
    assert "InterpretationCatalogRepository(" not in source
    assert "InterpretationRevisionRepository(" not in source
    assert "InterpretationIntervalTypeRepository(" not in source
    assert "application_service_container(state).interpretation_workspace" in source


def test_interpretation_panel_does_not_construct_coordination_services() -> None:
    source = Path("ui/interpretation_interval_panel.py").read_text(encoding="utf-8")
    forbidden_constructors = {
        "InterpretationIntervalManager(",
        "InterpretationIntervalPropertiesService(",
        "InterpretationIntervalBatchService(",
        "InterpretationIntervalTransferService(",
        "InterpretationIntervalMergeService(",
        "InterpretationPublicationService(",
    }

    for constructor in forbidden_constructors:
        assert constructor not in source

    assert "workspace_service.interval_manager(" in source
    assert "workspace_service.interval_properties(" in source
    assert "workspace_service.interval_batch(" in source
    assert "workspace_service.publication(" in source
    assert "workspace_service.interval_transfer(" in source
    assert "workspace_service.interval_merge(" in source


def test_interval_panel_does_not_receive_repository_gateways() -> None:
    source = Path("ui/interpretation_interval_panel.py").read_text(encoding="utf-8")
    forbidden = (
        ".catalog(",
        ".interval_types(",
        ".filter_presets(",
        ".revisions(",
        "catalog_repository",
        "type_repository",
        "preset_repository",
        "revision_repository",
    )
    assert all(token not in source for token in forbidden)
