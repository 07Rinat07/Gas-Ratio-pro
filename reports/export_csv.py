from __future__ import annotations

import pandas as pd


def export_csv_bytes(df: pd.DataFrame) -> bytes:
    if df is None or df.empty:
        return b""
    return df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
