from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import pandas as pd

from importers.header_detector import detect_header_row, prepare_dataframe_with_header


def _to_excel_source(file_or_path) -> BytesIO | str:
    if isinstance(file_or_path, (str, Path)):
        return str(file_or_path)

    if hasattr(file_or_path, "getvalue"):
        return BytesIO(file_or_path.getvalue())

    if hasattr(file_or_path, "read"):
        stream: BinaryIO = file_or_path
        position = stream.tell() if hasattr(stream, "tell") else None
        data = stream.read()
        if position is not None and hasattr(stream, "seek"):
            stream.seek(position)
        return BytesIO(data)

    raise TypeError("Unsupported Excel input type.")


def load_excel_sheets(file_or_path) -> dict[str, pd.DataFrame]:
    source = _to_excel_source(file_or_path)
    excel_file = pd.ExcelFile(source, engine="openpyxl")
    return {
        sheet_name: pd.read_excel(
            excel_file,
            sheet_name=sheet_name,
            header=None,
            dtype=object,
        )
        for sheet_name in excel_file.sheet_names
    }


def read_excel_sheet(file_or_path, sheet_name: str, header_row: int | None = None) -> pd.DataFrame:
    sheets = load_excel_sheets(file_or_path)
    if sheet_name not in sheets:
        raise ValueError(f"Sheet not found: {sheet_name}")

    raw_df = sheets[sheet_name]
    if header_row is None:
        header_row = detect_header_row(raw_df).header_row
    return prepare_dataframe_with_header(raw_df, header_row)
