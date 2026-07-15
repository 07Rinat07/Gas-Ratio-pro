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
