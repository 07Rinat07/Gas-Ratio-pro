from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ai.assistant import LocalAssistant
from ai.factory import build_provider
from ai.settings import load_ai_settings
from core.calculations import CH_WARNING, calculate_gas_ratios
from core.interpretation import INTERPRETATION_NOTE, add_interpretation, summarize_interpretation
from core.logging_config import configure_logging, safe_log_value
from core.models import CalculationConfig, STANDARD_FIELDS
from importers.csv_importer import load_csv_sheets
from importers.excel_importer import load_excel_sheets
from importers.header_detector import detect_header_row, prepare_dataframe_with_header
from mapping.mapper import apply_mapping, auto_map_columns
from palettes.config import load_palette_config
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


def _render_ai_assistant(logger, selected_row: pd.Series | None = None) -> None:
    st.subheader("Локальный ИИ-помощник")

    try:
        ai_settings = load_ai_settings()
        provider = build_provider(ai_settings)
    except Exception:
        logger.exception("ai_settings_load_failed")
        st.error("Не удалось загрузить конфигурацию ИИ-помощника. Проверьте config/ai.json.")
        st.caption("Подробности записаны в logs/app.log.")
        return

    st.caption(
        "Помощник работает offline-first: `offline-docs` не требует интернета, "
        "а `ollama` обращается только к локальному серверу. Полная таблица не передается."
    )
    st.caption(f"AI provider: {ai_settings.provider}")

    question = st.text_area(
        "Вопрос по данным, формулам, предупреждениям или выбранному интервалу",
        placeholder="Например: почему Bh стал NaN или какие колонки нужны для расчета Wh?",
        key="local_ai_question",
        height=90,
    )

    if not st.button("Спросить помощника", key="local_ai_submit"):
        return

    if not question.strip():
        st.warning("Введите вопрос для локального помощника.")
        return

    assistant = LocalAssistant(provider=provider)
    interval_row = selected_row if ai_settings.privacy.send_selected_interval_only else None
    logger.info(
        "ai_question_received provider=%s chars=%d has_interval=%s",
        safe_log_value(ai_settings.provider),
        len(question),
        interval_row is not None,
    )
    answer = assistant.answer(question, interval_row=interval_row)
    logger.info(
        "ai_answer_generated provider=%s sources=%d",
        safe_log_value(answer.provider_name),
        len(answer.sources),
    )

    st.markdown(answer.answer)
    if answer.sources:
        st.caption("Источники: " + ", ".join(answer.sources))


def main() -> None:
    st.set_page_config(page_title="Gas Ratio Interpreter v0.3", layout="wide")
    st.title("Gas Ratio Interpreter v0.3")
    st.caption(INTERPRETATION_NOTE)

    logger = configure_logging()
    logger.info("streamlit_app_started")

    try:
        palette_config = load_palette_config()
    except Exception:
        logger.exception("palette_config_load_failed")
        st.error("Не удалось загрузить конфигурацию палеток. Проверьте config/palettes.json.")
        st.caption("Подробности записаны в logs/app.log.")
        return

    st.sidebar.subheader("Палетки")
    st.sidebar.caption(f"Config: {palette_config.version}")
    st.sidebar.info(palette_config.notice)

    uploaded_file = st.file_uploader(
        "Загрузка файла",
        type=["csv", "xlsx", "xlsm"],
    )

    if uploaded_file is None:
        st.info("Загрузите CSV, XLSX или XLSM файл с газовыми данными.")
        _render_ai_assistant(logger)
        return

    suffix = Path(uploaded_file.name).suffix.lower()
    logger.info(
        "file_upload_received extension=%s size=%s",
        safe_log_value(suffix),
        safe_log_value(getattr(uploaded_file, "size", "unknown")),
    )

    if suffix not in SUPPORTED_EXTENSIONS:
        logger.warning("unsupported_file_extension extension=%s", safe_log_value(suffix))
        st.error("Формат файла не поддерживается в v0.3.")
        return

    try:
        sheets = _load_raw_sheets(uploaded_file)
        logger.info("file_read_success extension=%s sheet_count=%d", safe_log_value(suffix), len(sheets))
    except Exception:
        logger.exception("file_read_failed extension=%s", safe_log_value(suffix))
        st.error("Не удалось прочитать файл. Проверьте формат и доступность данных.")
        st.caption("Подробности записаны в logs/app.log.")
        return

    if not sheets:
        logger.warning("file_read_empty extension=%s", safe_log_value(suffix))
        st.error("Файл прочитан, но листы или строки данных не найдены.")
        return

    sheet_name = st.selectbox("Выбор листа", options=list(sheets.keys()))
    raw_df = sheets[sheet_name]
    logger.info(
        "sheet_selected sheet=%s rows=%d columns=%d",
        safe_log_value(sheet_name),
        len(raw_df),
        len(raw_df.columns),
    )

    st.subheader("Предпросмотр первых 20 строк")
    st.dataframe(raw_df.head(20), use_container_width=True)

    if raw_df.empty:
        logger.warning("selected_sheet_empty sheet=%s", safe_log_value(sheet_name))
        st.error("Выбранный лист пустой.")
        return

    detected_header = detect_header_row(raw_df)
    logger.info(
        "header_detected sheet=%s row=%d score=%d",
        safe_log_value(sheet_name),
        detected_header.header_row,
        detected_header.score,
    )
    header_row = st.number_input(
        "Строка заголовков",
        min_value=0,
        max_value=max(0, len(raw_df) - 1),
        value=int(detected_header.header_row),
        step=1,
        help="Нумерация с 0. Можно исправить вручную, если автоопределение ошиблось.",
    )

    prepared_df = prepare_dataframe_with_header(raw_df, int(header_row))
    logger.info(
        "header_applied row=%d rows=%d columns=%d",
        int(header_row),
        len(prepared_df),
        len(prepared_df.columns),
    )
    if prepared_df.empty:
        logger.warning("prepared_dataframe_empty header_row=%d", int(header_row))
        st.error("После выбора строки заголовков не осталось строк данных.")
        return

    st.subheader("Сопоставление колонок")
    st.dataframe(prepared_df.head(20), use_container_width=True)

    mapping_result = auto_map_columns(prepared_df.columns)
    logger.info(
        "auto_mapping_completed mapped=%s unmapped_count=%d",
        safe_log_value(",".join(sorted(mapping_result.mapping.keys()))),
        len(mapping_result.unmapped_columns),
    )
    manual_mapping = _build_mapping_controls(prepared_df, mapping_result.mapping)

    prepared = apply_mapping(prepared_df, manual_mapping)
    logger.info(
        "manual_mapping_applied mapped=%s warning_count=%d",
        safe_log_value(",".join(sorted(manual_mapping.keys()))),
        len(prepared.warnings),
    )
    ch_mode = st.radio(
        "Режим Ch",
        options=["A", "reserved"],
        format_func=lambda value: "A: (C3 + ΣC4 + ΣC5) / (ΣC4 + ΣC5)" if value == "A" else "B: reserved, отключено",
        horizontal=True,
    )

    calculation = calculate_gas_ratios(prepared.data, CalculationConfig(ch_mode=ch_mode))
    calculated_df = add_interpretation(calculation.data)
    logger.info(
        "calculation_completed rows=%d ch_mode=%s warning_count=%d",
        len(calculated_df),
        safe_log_value(ch_mode),
        len(calculation.warnings),
    )

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
        logger.warning("calculated_dataframe_empty")
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
        logger.warning("interval_list_empty")
        st.error("Не найдено ни одного интервала для выбора.")
        return

    selected_index = st.selectbox(
        "Выбор интервала",
        options=interval_indices,
        format_func=lambda index: _interval_label(calculated_df, index),
    )
    if selected_index not in calculated_df.index:
        logger.warning("selected_interval_missing index=%s", safe_log_value(selected_index))
        st.error("Выбранный интервал не найден.")
        return

    selected_row = calculated_df.loc[selected_index]
    logger.info("interval_selected index=%s", safe_log_value(selected_index))

    _render_ai_assistant(logger, selected_row)

    st.subheader("Pixler + ternary")
    left, right = st.columns(2)
    left.plotly_chart(
        build_pixler_palette(selected_row, zones=palette_config.pixler_zones),
        use_container_width=True,
    )
    right.plotly_chart(
        build_ternary_palette(selected_row, regions=palette_config.ternary_regions),
        use_container_width=True,
    )

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