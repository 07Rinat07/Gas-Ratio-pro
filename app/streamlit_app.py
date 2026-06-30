from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.calculations import CH_WARNING, calculate_gas_ratios
from core.interpretation import INTERPRETATION_NOTE, add_interpretation, summarize_interpretation
from core.models import CalculationConfig, STANDARD_FIELDS
from importers.csv_importer import load_csv_sheets
from importers.excel_importer import load_excel_sheets
from importers.header_detector import detect_header_row, prepare_dataframe_with_header
from mapping.mapper import apply_mapping, auto_map_columns
from palettes.depth_tracks import (
    build_depth_gas_tracks,
    build_depth_pixler_tracks,
    build_depth_ratio_tracks,
)
from palettes.pixler import build_pixler_palette
from palettes.ternary import build_ternary_palette
from reports.export_csv import export_csv_bytes


SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xlsm"}


def _load_raw_sheets(uploaded_file) -> dict[str, pd.DataFrame]:
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix == ".csv":
        return load_csv_sheets(uploaded_file)
    if suffix in {".xlsx", ".xlsm"}:
        return load_excel_sheets(uploaded_file)
    raise ValueError(f"Формат {suffix} не поддерживается в v0.3.")


def _build_mapping_controls(df: pd.DataFrame, detected_mapping: dict[str, str]) -> dict[str, str]:
    options = [""] + [str(column) for column in df.columns]
    mapping: dict[str, str] = {}

    field_groups = [
        ("Интервал", ("well", "depth", "depth_from", "depth_to")),
        ("Газовые компоненты", ("c1", "c2", "c3", "ic4", "nc4", "ic5", "nc5")),
        ("Дополнительно", ("co2", "h2s", "rop", "lithology")),
    ]

    for group_name, fields in field_groups:
        st.caption(group_name)
        columns = st.columns(3)
        for index, field in enumerate(fields):
            default_value = detected_mapping.get(field, "")
            default_index = options.index(default_value) if default_value in options else 0
            selected = columns[index % 3].selectbox(
                field,
                options=options,
                index=default_index,
                key=f"mapping_{field}",
            )
            if selected:
                mapping[field] = selected

    unused_standard_fields = set(STANDARD_FIELDS) - set(mapping)
    if unused_standard_fields:
        st.caption("Поля без сопоставления будут пропущены; отсутствующие C1-C5 будут приняты как 0.")

    return mapping


def _interval_label(df: pd.DataFrame, index: int) -> str:
    row = df.iloc[index]
    depth = row.get("depth", index)
    if pd.isna(depth):
        depth = index
    interpretation = row.get("interpretation", "нет интерпретации")
    return f"{index}: depth={depth} | {interpretation}"


def main() -> None:
    st.set_page_config(page_title="Gas Ratio Interpreter v0.3", layout="wide")
    st.title("Gas Ratio Interpreter v0.3")
    st.caption(INTERPRETATION_NOTE)

    uploaded_file = st.file_uploader(
        "Загрузка файла",
        type=["csv", "xlsx", "xlsm"],
    )

    if uploaded_file is None:
        st.info("Загрузите CSV, XLSX или XLSM файл с газовыми данными.")
        return

    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        st.error("Формат файла не поддерживается в v0.3.")
        return

    try:
        sheets = _load_raw_sheets(uploaded_file)
    except Exception as exc:
        st.error("Не удалось прочитать файл. Проверьте формат и доступность данных.")
        st.caption(str(exc))
        return

    if not sheets:
        st.error("Файл прочитан, но листы или строки данных не найдены.")
        return

    sheet_name = st.selectbox("Выбор листа", options=list(sheets.keys()))
    raw_df = sheets[sheet_name]

    st.subheader("Предпросмотр первых 20 строк")
    st.dataframe(raw_df.head(20), use_container_width=True)

    if raw_df.empty:
        st.error("Выбранный лист пустой.")
        return

    detected_header = detect_header_row(raw_df)
    header_row = st.number_input(
        "Строка заголовков",
        min_value=0,
        max_value=max(0, len(raw_df) - 1),
        value=int(detected_header.header_row),
        step=1,
        help="Нумерация с 0. Можно исправить вручную, если автоопределение ошиблось.",
    )

    prepared_df = prepare_dataframe_with_header(raw_df, int(header_row))
    if prepared_df.empty:
        st.error("После выбора строки заголовков не осталось строк данных.")
        return

    st.subheader("Сопоставление колонок")
    st.dataframe(prepared_df.head(20), use_container_width=True)

    mapping_result = auto_map_columns(prepared_df.columns)
    manual_mapping = _build_mapping_controls(prepared_df, mapping_result.mapping)

    prepared = apply_mapping(prepared_df, manual_mapping)
    ch_mode = st.radio(
        "Режим Ch",
        options=["A", "reserved"],
        format_func=lambda value: "A: (C3 + ΣC4 + ΣC5) / (ΣC4 + ΣC5)" if value == "A" else "B: reserved, отключено",
        horizontal=True,
    )

    calculation = calculate_gas_ratios(prepared.data, CalculationConfig(ch_mode=ch_mode))
    calculated_df = add_interpretation(calculation.data)

    warnings = list(mapping_result.warnings) + list(prepared.warnings) + list(calculation.warnings)
    warnings = list(dict.fromkeys(warnings))

    st.subheader("Предупреждения")
    if warnings:
        for warning in warnings:
            st.warning(warning)
    else:
        st.success("Критичных предупреждений нет.")
    st.info(CH_WARNING)

    if calculated_df.empty:
        st.error("Нет расчетных данных для отображения.")
        return

    st.subheader("Сводка классификации")
    st.dataframe(summarize_interpretation(calculated_df), use_container_width=True)

    interval_indices = [
        int(index)
        for index in calculated_df.index
        if not pd.isna(index)
    ]
    if not interval_indices:
        st.error("Не найдено ни одного интервала для выбора.")
        return

    selected_index = st.selectbox(
        "Выбор интервала",
        options=interval_indices,
        format_func=lambda index: _interval_label(calculated_df, index),
    )
    if selected_index not in calculated_df.index:
        st.error("Выбранный интервал не найден.")
        return

    selected_row = calculated_df.loc[selected_index]

    st.subheader("Pixler + ternary")
    left, right = st.columns(2)
    left.plotly_chart(build_pixler_palette(selected_row), use_container_width=True)
    right.plotly_chart(build_ternary_palette(selected_row), use_container_width=True)

    st.subheader("Графики по глубине")
    tab_gas, tab_ratios, tab_pixler = st.tabs(["C1-C5", "Wh/Bh/Ch", "Pixler ratios"])
    tab_gas.plotly_chart(build_depth_gas_tracks(calculated_df), use_container_width=True)
    tab_ratios.plotly_chart(build_depth_ratio_tracks(calculated_df), use_container_width=True)
    tab_pixler.plotly_chart(build_depth_pixler_tracks(calculated_df), use_container_width=True)

    st.subheader("Расчетная таблица")
    st.dataframe(calculated_df, use_container_width=True)
    st.download_button(
        "Экспорт CSV",
        data=export_csv_bytes(calculated_df),
        file_name="gas_ratio_calculations.csv",
        mime="text/csv",
    )


if __name__ == "__main__":
    main()
