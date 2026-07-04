from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import pandas as pd

from importers.header_detector import detect_header_row, prepare_dataframe_with_header


CSV_ENCODINGS: tuple[str, ...] = ("utf-8-sig", "utf-8", "cp1251", "latin1")


def _to_bytes_buffer(file_or_path) -> BytesIO | str:
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

    raise TypeError("Unsupported CSV input type.")


def load_csv_raw(file_or_path) -> pd.DataFrame:
    source = _to_bytes_buffer(file_or_path)
    last_error: Exception | None = None

    for encoding in CSV_ENCODINGS:
        try:
            if isinstance(source, BytesIO):
                source.seek(0)
            return pd.read_csv(
                source,
                header=None,
                dtype=object,
                sep=None,
                engine="python",
                encoding=encoding,
            )
        except UnicodeDecodeError as exc:
            last_error = exc

    if last_error:
        raise last_error
    return pd.DataFrame()


def load_csv_sheets(file_or_path) -> dict[str, pd.DataFrame]:
    return {"CSV": load_csv_raw(file_or_path)}


def read_csv(file_or_path, header_row: int | None = None) -> pd.DataFrame:
    raw_df = load_csv_raw(file_or_path)
    if header_row is None:
        header_row = detect_header_row(raw_df).header_row
    return prepare_dataframe_with_header(raw_df, header_row)
