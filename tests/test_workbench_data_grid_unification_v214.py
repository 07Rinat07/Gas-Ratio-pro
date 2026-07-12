from pathlib import Path

APP = Path('app/streamlit_app.py').read_text(encoding='utf-8')


def test_shared_workbench_data_grid_exists():
    assert 'def _render_workbench_data_grid(' in APP
    assert 'Render the shared Workbench Data Grid' in APP


def test_dataset_manager_uses_shared_grid():
    assert 'key_prefix=f"workbench_dataset_{project_id}_{section}"' in APP
    assert 'technical_columns=("Скважина ID", "Источник ID", "Архивировано")' in APP


def test_calculation_archive_uses_shared_grid():
    assert 'key_prefix=f"workbench_calculations_{project.id}"' in APP
    assert 'technical_columns=("Calculation ID",)' in APP


def test_export_catalog_uses_shared_grid():
    assert 'key_prefix=f"workbench_exports_{project.id}"' in APP
    assert 'technical_columns=("Export ID", "Источник")' in APP


def test_legacy_project_database_alias_is_preserved():
    assert 'def _render_project_database_table(*args, **kwargs)' in APP
    assert '_render_workbench_data_grid(*args, **kwargs)' in APP
