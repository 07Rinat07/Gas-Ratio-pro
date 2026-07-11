"""Streamlit runtime compatibility helpers.

Keeps UI-bound tabular data Arrow-safe and centralizes capture of Streamlit
runtime warnings in the existing application log.
"""
from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from core.logging_config import configure_logging

_STREAMLIT_LOGGERS = (
    "streamlit",
    "streamlit.runtime",
    "streamlit.dataframe_util",
    "streamlit.elements.arrow",
    "pyarrow",
)


def normalize_dataframe_for_streamlit(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a copy whose object columns have one Arrow-compatible type.

    Homogeneous object columns are preserved. Mixed object columns are rendered
    as strings because property/audit tables are presentation data rather than
    calculation inputs.
    """
    if not isinstance(frame, pd.DataFrame):
        raise TypeError("frame must be a pandas DataFrame")
    result = frame.copy()
    for column in result.columns:
        series = result[column]
        if series.dtype != object:
            continue
        non_null = [value for value in series.tolist() if not pd.isna(value)]
        value_types = {type(value) for value in non_null}
        if len(value_types) > 1:
            result[column] = series.map(lambda value: "" if pd.isna(value) else str(value))
    return result


def configure_streamlit_runtime_log_capture() -> logging.Logger:
    """Route Streamlit/PyArrow warnings to the existing rotating app.log."""
    app_logger = configure_logging()
    file_handlers = [h for h in app_logger.handlers if getattr(h, "_gas_ratio_file_handler", False)]
    for logger_name in _STREAMLIT_LOGGERS:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.WARNING)
        for handler in file_handlers:
            if handler not in logger.handlers:
                logger.addHandler(handler)
        logger.propagate = False
    logging.captureWarnings(True)
    warnings_logger = logging.getLogger("py.warnings")
    warnings_logger.setLevel(logging.WARNING)
    for handler in file_handlers:
        if handler not in warnings_logger.handlers:
            warnings_logger.addHandler(handler)
    warnings_logger.propagate = False
    return app_logger
