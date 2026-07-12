from __future__ import annotations

import ast
from pathlib import Path


def test_streamlit_app_imports_methodology_warning() -> None:
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    imported_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "core.calculations":
            imported_names.update(alias.name for alias in node.names)

    assert "CH_WARNING" in imported_names
    assert "METHODOLOGY_WARNING" in imported_names


def test_methodology_warning_is_defined_in_calculation_core() -> None:
    from core.calculations import METHODOLOGY_WARNING

    assert isinstance(METHODOLOGY_WARNING, str)
    assert METHODOLOGY_WARNING.strip()
