from __future__ import annotations

import logging

import pandas as pd

from core.streamlit_runtime_compat import (
    configure_streamlit_runtime_log_capture,
    normalize_dataframe_for_streamlit,
)
from projects.calculations import build_project_calculation_comparison_table


def test_mixed_object_column_is_string_normalized():
    source = pd.DataFrame({"Значения": ["alpha", 2, None]})
    result = normalize_dataframe_for_streamlit(source)
    assert result["Значения"].tolist() == ["alpha", "2", ""]
    assert source["Значения"].tolist() == ["alpha", 2, None]


def test_homogeneous_object_column_is_preserved():
    source = pd.DataFrame({"name": ["a", "b"]})
    result = normalize_dataframe_for_streamlit(source)
    assert result.equals(source)


def test_streamlit_runtime_loggers_receive_rotating_file_handler():
    configure_streamlit_runtime_log_capture()
    logger = logging.getLogger("streamlit.dataframe_util")
    assert any(getattr(handler, "_gas_ratio_file_handler", False) for handler in logger.handlers)


def test_project_calculation_comparison_values_are_arrow_safe_strings():
    class Comparison:
        left_source_label = "A"
        right_source_label = "B"
        left_rows = 10
        right_rows = 12
        row_delta = 2
        common_columns = ("depth",)
        added_columns = ()
        removed_columns = ()
        changed_columns = ("GR",)
        changed_cell_count = 3
        added_warnings = ()
        removed_warnings = ()
        common_warnings = ()
        has_differences = True
    table = build_project_calculation_comparison_table(Comparison())
    assert set(type(value) for value in table["Значения"].tolist()) == {str}
