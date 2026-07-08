from __future__ import annotations

import ast
from pathlib import Path


def test_project_manager_toolbar_helper_is_defined() -> None:
    """The Streamlit app uses the shared table toolbar caption helper.

    This regression test prevents runtime NameError when repository panels render.
    It parses the source without importing Streamlit.
    """

    source_path = Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))

    defined_functions = {
        node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    assert "_render_table_toolbar_caption" in defined_functions
