from __future__ import annotations

import re
from pathlib import Path
from typing import BinaryIO

import pandas as pd

from importers.header_detector import detect_header_row, prepare_dataframe_with_header


LAS_ENCODINGS: tuple[str, ...] = ("utf-8-sig", "utf-8", "cp1251", "latin1")
ASCII_SECTION_NAMES = {"A", "ASCII"}
CURVE_SECTION_NAMES = {"C", "CURVE"}
WELL_SECTION_NAMES = {"W", "WELL"}


def _read_bytes(file_or_path) -> bytes:
    if isinstance(file_or_path, (str, Path)):
        return Path(file_or_path).read_bytes()

    if hasattr(file_or_path, "getvalue"):
        value = file_or_path.getvalue()
        return bytes(value)

    if hasattr(file_or_path, "read"):
        stream: BinaryIO = file_or_path
        position = stream.tell() if hasattr(stream, "tell") else None
        data = stream.read()
        if position is not None and hasattr(stream, "seek"):
            stream.seek(position)
        return data

    raise TypeError("Unsupported LAS input type.")


def _decode_las(data: bytes) -> str:
    last_error: UnicodeDecodeError | None = None
    for encoding in LAS_ENCODINGS:
        try:
            return data.decode(encoding)
        except UnicodeDecodeError as exc:
            last_error = exc

    if last_error:
        raise last_error
    return ""


def _section_name(line: str) -> str | None:
    stripped = line.strip()
    if not stripped.startswith("~"):
        return None
    raw_name = stripped[1:].split(maxsplit=1)[0].strip().upper()
    return raw_name.split(".", 1)[0]


def _remove_inline_comment(line: str) -> str:
    return line.split("#", 1)[0].strip()


def _parse_curve_mnemonic(line: str) -> str | None:
    clean_line = _remove_inline_comment(line)
    if not clean_line:
        return None

    left = clean_line.split(":", 1)[0].strip()
    if not left:
        return None

    mnemonic = left.split(".", 1)[0].strip() if "." in left else left.split(maxsplit=1)[0].strip()
    mnemonic = re.sub(r"[^0-9A-Za-zА-Яа-я_]+", "", mnemonic)
    return mnemonic or None


def _parse_null_value(line: str) -> float | None:
    clean_line = _remove_inline_comment(line)
    if not clean_line.strip().upper().startswith("NULL"):
        return None

    match = re.search(r"^\s*NULL(?:\s*\.[^\s]*)?\s+([-+]?\d+(?:[\.,]\d+)?)", clean_line, flags=re.IGNORECASE)
    if not match:
        return None

    try:
        return float(match.group(1).replace(",", "."))
    except ValueError:
        return None


def _parse_number(value: str, null_value: float | None) -> float | None:
    clean_value = value.strip().replace(",", ".")
    if not clean_value:
        return None

    try:
        number = float(clean_value)
    except ValueError:
        return None

    if null_value is not None and number == null_value:
        return None
    return number


def _parse_las_text(text: str) -> tuple[list[str], list[list[float | None]], float | None]:
    section = ""
    curves: list[str] = []
    rows: list[list[float | None]] = []
    null_value: float | None = None

    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        next_section = _section_name(stripped)
        if next_section is not None:
            section = next_section
            continue

        if section in WELL_SECTION_NAMES:
            parsed_null = _parse_null_value(stripped)
            if parsed_null is not None:
                null_value = parsed_null
            continue

        if section in CURVE_SECTION_NAMES:
            mnemonic = _parse_curve_mnemonic(stripped)
            if mnemonic:
                curves.append(mnemonic)
            continue

        if section in ASCII_SECTION_NAMES:
            clean_line = _remove_inline_comment(stripped)
            if not clean_line:
                continue
            values = [_parse_number(part, null_value) for part in clean_line.split()]
            if not values:
                continue
            if curves:
                if len(values) < len(curves):
                    values.extend([None] * (len(curves) - len(values)))
                values = values[: len(curves)]
            rows.append(values)

    if not curves:
        raise ValueError("LAS curve section (~Curve) was not found or does not contain curves.")
    if not rows:
        raise ValueError("LAS ASCII data section (~ASCII/~A) was not found or empty.")

    return curves, rows, null_value


def load_las_raw(file_or_path) -> pd.DataFrame:
    text = _decode_las(_read_bytes(file_or_path))
    curves, rows, _null_value = _parse_las_text(text)
    return pd.DataFrame([curves, *rows])


def load_las_sheets(file_or_path) -> dict[str, pd.DataFrame]:
    return {"LAS": load_las_raw(file_or_path)}


def read_las(file_or_path, header_row: int | None = None) -> pd.DataFrame:
    raw_df = load_las_raw(file_or_path)
    if header_row is None:
        header_row = detect_header_row(raw_df).header_row
    return prepare_dataframe_with_header(raw_df, header_row)
