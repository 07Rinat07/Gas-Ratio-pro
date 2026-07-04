from __future__ import annotations

from collections import defaultdict

import pandas as pd

from core.models import GAS_COMPONENT_FIELDS, MappingResult, STANDARD_FIELDS, PreparedDataFrame
from mapping.curve_aliases import alias_lookup, normalized_curve_candidates


def detect_standard_field(column_name: object) -> str | None:
    lookup = alias_lookup()
    for candidate in normalized_curve_candidates(column_name):
        standard_name = lookup.get(candidate)
        if standard_name is not None:
            return standard_name
    return None


def auto_map_columns(columns) -> MappingResult:
    mapping: dict[str, str] = {}
    duplicate_matches: dict[str, list[str]] = defaultdict(list)
    unmapped_columns: list[str] = []

    for column in columns:
        source_name = str(column).strip()
        if not source_name or source_name.lower().startswith("unnamed"):
            continue

        standard_name = detect_standard_field(source_name)
        if standard_name is None:
            unmapped_columns.append(source_name)
            continue

        if standard_name in mapping:
            duplicate_matches[standard_name].append(source_name)
            continue

        mapping[standard_name] = source_name

    warnings = [
        f"Поле {field} найдено в нескольких колонках: {', '.join(values)}. Использована первая."
        for field, values in duplicate_matches.items()
    ]

    return MappingResult(
        mapping=mapping,
        unmapped_columns=tuple(unmapped_columns),
        duplicate_matches={key: tuple(value) for key, value in duplicate_matches.items()},
        warnings=tuple(warnings),
    )


def _is_numeric_like(series: pd.Series) -> bool:
    return pd.to_numeric(series, errors="coerce").notna().any()


def _safe_extra_column_name(source_name: object, existing_columns: set[str]) -> str | None:
    name = str(source_name).strip()
    if not name or name.lower().startswith("unnamed"):
        return None
    if name.lower() in {field.lower() for field in STANDARD_FIELDS}:
        return None

    candidate = name
    duplicate_index = 2
    while candidate in existing_columns:
        candidate = f"{name}_{duplicate_index}"
        duplicate_index += 1
    return candidate


def apply_mapping(
    df: pd.DataFrame,
    mapping: dict[str, str],
    missing_components_as_zero: bool = True,
) -> PreparedDataFrame:
    warnings: list[str] = []

    if df is None or df.empty:
        return PreparedDataFrame(data=pd.DataFrame(), warnings=("Нет данных для сопоставления.",))

    selected_columns: dict[str, pd.Series] = {}
    for standard_name, source_name in mapping.items():
        if standard_name not in STANDARD_FIELDS:
            continue
        if source_name not in df.columns:
            warnings.append(f"Колонка {source_name} не найдена и пропущена.")
            continue
        selected_columns[standard_name] = df[source_name]

    result = pd.DataFrame(selected_columns, index=df.index)

    used_source_columns = {str(source_name) for source_name in mapping.values()}
    existing_columns = {str(column) for column in result.columns}
    for source_name in df.columns:
        if str(source_name) in used_source_columns:
            continue
        series = df[source_name]
        if not isinstance(series, pd.Series) or not _is_numeric_like(series):
            continue
        extra_name = _safe_extra_column_name(source_name, existing_columns)
        if extra_name is None:
            continue
        result[extra_name] = series
        existing_columns.add(extra_name)

    if missing_components_as_zero:
        for component in GAS_COMPONENT_FIELDS:
            if component not in result.columns:
                result[component] = 0.0
                warnings.append(f"Компонент {component} отсутствует: добавлена колонка со значением 0.")

    return PreparedDataFrame(
        data=result.reset_index(drop=True),
        warnings=tuple(dict.fromkeys(warnings)),
    )
