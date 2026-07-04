from __future__ import annotations

from io import BytesIO

import pandas as pd


def export_xlsx_bytes(df: pd.DataFrame, sheet_name: str = "calculations") -> bytes:
    if df is None or df.empty:
        return b""

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name[:31] or "calculations")
    return buffer.getvalue()
