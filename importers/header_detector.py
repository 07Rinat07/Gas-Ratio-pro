from __future__ import annotations

import pandas as pd

from core.models import HeaderCandidate, HeaderDetectionResult
from mapping.mapper import detect_standard_field


def _is_empty_value(value: object) -> bool:
    if pd.isna(value):
        return True
    return str(value).strip() == ""


def _clean_column_name(value: object, index: int) -> str:
    if _is_empty_value(value):
        return f"column_{index + 1}"

    name = str(value).strip()
    if name.lower().startswith("unnamed"):
        return f"column_{index + 1}"
    return name


def _make_unique(names: list[str]) -> list[str]:
    counts: dict[str, int] = {}
    result: list[str] = []

    for name in names:
        if name not in counts:
            counts[name] = 0
            result.append(name)
            continue

        counts[name] += 1
        result.append(f"{name}_{counts[name]}")

    return result


def score_header_row(row: pd.Series) -> HeaderCandidate:
    recognized: list[str] = []
    non_empty_count = 0

    for value in row.tolist():
        if _is_empty_value(value):
            continue

        non_empty_count += 1
        standard_name = detect_standard_field(value)
        if standard_name:
            recognized.append(standard_name)

    unique_recognized = tuple(sorted(set(recognized)))
    score = len(unique_recognized) * 3 + len(recognized)

    if non_empty_count < 2:
        score -= 2

    return HeaderCandidate(
        row_index=int(row.name),
        score=score,
        recognized_columns=unique_recognized,
    )


def detect_header_row(raw_df: pd.DataFrame, max_scan_rows: int = 50) -> HeaderDetectionResult:
    if raw_df is None or raw_df.empty:
        return HeaderDetectionResult(header_row=0, score=0, candidates=())

    scan_limit = min(max_scan_rows, len(raw_df))
    candidates = tuple(
        sorted(
            (score_header_row(raw_df.iloc[index]) for index in range(scan_limit)),
            key=lambda candidate: candidate.score,
            reverse=True,
        )
    )

    best = candidates[0] if candidates else HeaderCandidate(row_index=0, score=0)
    header_row = best.row_index if best.score > 0 else 0

    return HeaderDetectionResult(
        header_row=header_row,
        score=best.score,
        candidates=candidates[:10],
    )


def prepare_dataframe_with_header(raw_df: pd.DataFrame, header_row: int) -> pd.DataFrame:
    if raw_df is None or raw_df.empty:
        return pd.DataFrame()

    safe_header_row = max(0, min(int(header_row), len(raw_df) - 1))
    raw_headers = raw_df.iloc[safe_header_row].tolist()
    columns = _make_unique(
        [_clean_column_name(value, index) for index, value in enumerate(raw_headers)]
    )

    data = raw_df.iloc[safe_header_row + 1 :].copy()
    data.columns = columns

    # Pandas 2.2+ warns about silent downcasting during replace().
    # This option keeps the normalization explicit and future-compatible while
    # preserving the existing behavior: whitespace-only strings are treated as
    # empty values only for cleanup decisions.
    with pd.option_context("future.no_silent_downcasting", True):
        normalized_empty = data.replace(r"^\s*$", pd.NA, regex=True)

    data = data.loc[~normalized_empty.isna().all(axis=1)].copy()

    empty_columns = [
        column for column in data.columns if normalized_empty[column].isna().all()
    ]
    if empty_columns:
        data = data.drop(columns=empty_columns)

    return data.reset_index(drop=True)
