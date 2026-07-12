from pathlib import Path

from projects.datasets import ProjectDatasetRecord, build_project_dataset_table

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app" / "streamlit_app.py"


def test_dataset_table_exposes_hidden_stable_identifier():
    record = ProjectDatasetRecord(
        id="dataset-1", kind="LAS", name="Well A", source_id="source-1",
        well_id="well-a", version_label="v1", original_file_name="well-a.las",
        saved_at="2026-07-12T00:00:00Z", status="ready", row_count=10, column_count=6,
    )
    table = build_project_dataset_table((record,))
    assert "Dataset ID" not in table.columns
    source = APP.read_text(encoding="utf-8")
    assert 'dataset_table.insert(0, "Dataset ID"' in source


def test_shared_grid_publishes_selection_to_properties_boundary():
    source = APP.read_text(encoding="utf-8")
    assert "WorkbenchSelectionService" in source
    assert "selection_target" in source
    assert "Подробности выбранной строки отображаются в панели Properties" in source
    assert 'selection_target="dataset"' in source
    assert 'selection_target="calculation"' in source
    assert 'selection_target="export"' in source


def test_duplicate_dataset_export_calculation_selectors_removed():
    source = APP.read_text(encoding="utf-8")
    assert '"Экспорт проекта",\n            options=' not in source
    assert '"Расчет проекта",\n            options=' not in source
