from __future__ import annotations

from typing import Any, Iterable
import pandas as pd
import streamlit as st

from .composite_v4 import build_composite_log_v4


def render_composite_log_v3(dataframe: pd.DataFrame, *, intervals: Iterable[Any] = (), height: int = 900) -> None:
    """Compatibility entry point. It now renders the canonical Composite Log v4."""
    try:
        result = build_composite_log_v4(
            dataframe,
            intervals=intervals,
            title="Engineering Composite Log v4",
            height=max(900, height),
            target_width=2380,
        )
    except ValueError as exc:
        st.info(str(exc))
        return
    st.components.v1.html(result.svg, height=result.height + 8, scrolling=True)
    if result.issues:
        st.caption("v4 diagnostics: " + ", ".join(result.issues))
