from __future__ import annotations

from collections import defaultdict

import pandas as pd

from core.models import GAS_COMPONENT_FIELDS, MappingResult, STANDARD_FIELDS, PreparedDataFrame
from mapping.curve_aliases import alias_lookup, normalize_curve_name


def detect_standard_field(column_name: object) -> str | None:
    normalized = normalize_curve_name(column_name)
    if not normalized:
        return None
    return alias_lookup().get(normalized)


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

    if missing_components_as_zero:
        for component in GAS_COMPONENT_FIELDS:
            if component not in result.columns:
                result[component] = 0.0
                warnings.append(f"Компонент {component} отсутствует: добавлена колонка со значением 0.")

    return PreparedDataFrame(
        data=result.reset_index(drop=True),
        warnings=tuple(dict.fromkeys(warnings)),
    )
