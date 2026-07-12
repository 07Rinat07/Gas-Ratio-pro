from __future__ import annotations

import pandas as pd

from core.project_database_table import (
    build_project_database_table_view,
    compact_path,
)


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Тип": "LAS", "Файл": "well-b.las", "Путь": "data/las/well-b.las", "Статус": "Доступен", "Размер, байт": 200, "SHA-256": "b" * 64},
            {"Тип": "CSV", "Файл": "sample.csv", "Путь": "data/csv/sample.csv", "Статус": "Предупреждение", "Размер, байт": 100, "SHA-256": "a" * 64},
            {"Тип": "LAS", "Файл": "well-a.las", "Путь": "data/las/well-a.las", "Статус": "Доступен", "Размер, байт": 150, "SHA-256": "c" * 64},
        ]
    )


def test_default_view_hides_technical_columns() -> None:
    view = build_project_database_table_view(_frame())
    assert "SHA-256" not in view.dataframe.columns
    assert "Путь" not in view.dataframe.columns
    assert view.total_rows == 3


def test_technical_mode_preserves_columns() -> None:
    view = build_project_database_table_view(_frame(), show_technical=True)
    assert "SHA-256" in view.dataframe.columns
    assert "Путь" in view.dataframe.columns


def test_filters_search_sort_and_pagination_are_composable() -> None:
    view = build_project_database_table_view(
        _frame(),
        search="well",
        selected_types=("LAS",),
        selected_statuses=("Доступен",),
        sort_column="Файл",
        ascending=True,
        page=1,
        page_size=1,
        show_technical=True,
    )
    assert view.filtered_rows == 2
    assert view.page_count == 2
    assert view.dataframe.iloc[0]["Файл"] == "well-a.las"


def test_page_is_clamped_after_filtering() -> None:
    view = build_project_database_table_view(
        _frame(),
        selected_types=("CSV",),
        page=99,
        page_size=10,
    )
    assert view.page == 1
    assert view.page_count == 1
    assert len(view.dataframe) == 1


def test_compact_path_preserves_start_and_end() -> None:
    source = "data/" + "nested/" * 20 + "important-file.las"
    compacted = compact_path(source, max_length=50)
    assert len(compacted) <= 50
    assert compacted.startswith("data/")
    assert compacted.endswith("important-file.las")
    assert "..." in compacted


def test_streamlit_project_database_uses_shared_table_renderer() -> None:
    source = open("app/streamlit_app.py", encoding="utf-8").read()
    assert "def _render_project_database_table(" in source
    assert "Технические данные" in source
    assert "Строк на странице" in source
    assert "project_database_files_" in source
    assert "project_database_versions_" in source
    assert "project_database_uuid_" in source
