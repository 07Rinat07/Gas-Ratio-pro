from pathlib import Path
import ast


def test_refresh_ui_does_not_call_itself():
    source = Path('app/streamlit_app.py').read_text(encoding='utf-8')
    tree = ast.parse(source)

    refresh_functions = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == '_refresh_ui'
    ]
    assert len(refresh_functions) == 1

    function = refresh_functions[0]
    for node in ast.walk(function):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id != '_refresh_ui'
