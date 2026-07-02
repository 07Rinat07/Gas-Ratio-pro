from __future__ import annotations

import sys
import time
from io import BytesIO
from pathlib import Path

import pandas as pd
import plotly.io as pio
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ai.assistant import LocalAssistant
from ai.factory import build_provider
from ai.health import check_ai_runtime_status
from ai.local_agent_setup import build_local_agent_next_commands
from ai.model_profiles import find_ai_model_profile, load_ai_model_profile_catalog
from ai.provider import OfflineDocumentationProvider
from ai.settings import load_ai_settings
from core.calculations import CH_WARNING, calculate_gas_ratios
from core.interpretation import INTERPRETATION_NOTE, add_interpretation, summarize_interpretation
from core.logging_config import configure_logging, safe_log_value
from core.models import CalculationConfig, STANDARD_FIELDS
from importers.csv_importer import load_csv_sheets
from importers.excel_importer import load_excel_sheets
from importers.header_detector import detect_header_row, prepare_dataframe_with_header
from importers.las_importer import load_las_sheets
from las_correlation import (
    CURVE_GROUP_LABELS,
    DEFAULT_GAS_GROUPS,
    DEFAULT_GIS_GROUPS,
    build_las_correlation_figure,
    prepare_las_correlation_wells,
)
from las_editor.depth_grid import resample_las_data
from mapping.mapper import apply_mapping, auto_map_columns
from palettes.config import load_palette_config
from palettes.depth_tracks import (
    build_depth_gas_tracks,
    build_depth_interpretation_track,
    build_depth_pixler_tracks,
    build_depth_ratio_tracks,
)
from palettes.pixler import build_pixler_palette
from palettes.ternary import build_ternary_palette
from reports.export_csv import export_csv_bytes
from wells.repository import DEFAULT_WELLS_ROOT, list_wells, read_well_file_bytes, save_well_version


SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xlsm", ".las"}
WELLS_STORAGE_ROOT = ROOT_DIR / DEFAULT_WELLS_ROOT
APP_LAUNCH_COMMAND = "python -m streamlit run app/streamlit_app.py"
APP_LAUNCH_SCRIPT = ".\\run_app.ps1"
AI_SUPPORT_CHAT_KEY = "local_ai_support_chat_messages"
AI_RESPONSE_MODE_KEY = "local_ai_response_mode"
UI_SCALE_KEY = "ui_scale"
LAS_EDITOR_SESSION_SHEETS_KEY = "las_editor_session_sheets"
LAS_EDITOR_SESSION_SUMMARY_KEY = "las_editor_session_summary"
INTERPRETATION_SESSION_DATA_KEY = "interpretation_session_data"
INTERPRETATION_SESSION_SOURCE_KEY = "interpretation_session_source"
APP_TABS = (
    "Работа с данными",
    "LAS-редактор",
    "LAS-корреляция",
    "Интерпретационные графики",
    "Инструкции и документация",
)
AI_SUPPORT_WELCOME_MESSAGE = (
    "Здравствуйте. Я локальный помощник по Gas Ratio Interpreter: формулам, "
    "импорту, предупреждениям, Ollama и выбранному интервалу."
)
AI_SUPPORT_QUICK_QUESTIONS: tuple[tuple[str, str], ...] = (
    ("Ollama Launch", "В Ollama открылось окно Launch. Что выбрать для проекта?"),
    ("Почему NaN?", "Почему Wh, Bh или BAR2 могут стать NaN?"),
    ("Колонки", "Что делать, если приложение не сопоставило колонки C1 и C2?"),
    ("Палетки", "Можно ли считать зоны Pixler и ternary подтвержденной методикой?"),
)
LAS_EDITOR_STEP_PRESETS: tuple[str, ...] = ("0.1", "0.2", "0.5", "1.0", "1.2", "2.0", "Другой")
LAS_EDITOR_FILL_STRATEGIES: tuple[tuple[str, str], ...] = (
    ("Оставить пусто", "empty"),
    ("Значение сверху", "top"),
    ("Значение снизу", "bottom"),
    ("Среднее сверху/снизу", "average"),
    ("Линейная интерполяция", "linear"),
)


DOCUMENTATION_TAB_DOCS: tuple[tuple[str, str], ...] = (
    ("Быстрый старт", "docs/setup.md"),
    ("Руководство пользователя", "docs/user_guide.md"),
    ("Формат входных данных", "docs/data_format.md"),
    ("План LAS-редактора", "docs/las_editor_plan.md"),
    ("План LAS-корреляции", "docs/las_correlation_plan.md"),
    ("Формулы", "docs/formulas.md"),
    ("Mud gas literature", "docs/mud_gas_analysis_literature.md"),
    ("Локальный AI-помощник", "docs/ai_usage.md"),
    ("Локальный AI-агент", "docs/local_ai_agent.md"),
    ("Troubleshooting", "docs/troubleshooting.md"),
)


def _apply_app_style(scale: str = "large") -> None:
    scale_tokens = {
        "standard": {"base": "17px", "body": "1rem", "caption": "0.95rem", "button": "1rem", "h1": "2.35rem"},
        "large": {"base": "20px", "body": "1.13rem", "caption": "1.02rem", "button": "1.08rem", "h1": "2.75rem"},
        "xlarge": {"base": "22px", "body": "1.22rem", "caption": "1.08rem", "button": "1.16rem", "h1": "3.05rem"},
    }
    tokens = scale_tokens.get(scale, scale_tokens["large"])
    st.markdown(
        """
        <style>
        :root {
            --app-text: #f4f7fb;
            --app-muted: #c5ccd8;
            --app-panel: #171b24;
            --app-panel-strong: #202634;
            --app-border: #364154;
            --app-accent: #4ea1ff;
        }
        .stApp {
            color: var(--app-text);
            font-size: {tokens["base"]};
        }
        .block-container {
            max-width: 1440px;
            padding-top: 2.4rem;
            padding-bottom: 3rem;
        }
        h1 {
            font-size: {tokens["h1"]} !important;
            line-height: 1.12 !important;
            margin-bottom: 0.65rem !important;
        }
        h2, h3 {
            letter-spacing: 0 !important;
        }
        p, li, label, span, div[data-testid="stMarkdownContainer"] {
            font-size: {tokens["body"]} !important;
            line-height: 1.55;
        }
        div[data-testid="stCaptionContainer"], .stCaption {
            color: var(--app-muted) !important;
            font-size: {tokens["caption"]} !important;
            line-height: 1.45 !important;
        }
        button[kind="secondary"], div[data-testid="stButton"] button {
            min-height: 2.65rem;
            font-size: {tokens["button"]} !important;
            border-color: var(--app-border);
        }
        div[data-testid="stFileUploader"] section {
            background: var(--app-panel);
            border: 1px solid var(--app-border);
            border-radius: 8px;
            padding: 1rem;
        }
        div[data-testid="stChatMessage"] {
            background: var(--app-panel);
            border: 1px solid #242b38;
            border-radius: 8px;
            padding: 0.85rem 1rem;
            margin-bottom: 0.8rem;
        }
        div[data-testid="stChatMessage"] p {
            font-size: {tokens["body"]} !important;
            line-height: 1.58;
        }
        div[data-baseweb="textarea"] textarea {
            font-size: {tokens["body"]} !important;
            min-height: 3.3rem;
        }
        div[data-testid="stAlert"] {
            border-radius: 8px;
        }
        code, pre {
            font-size: 0.98rem !important;
        }
        section[data-testid="stSidebar"] {
            min-width: 250px !important;
        }
        section[data-testid="stSidebar"] * {
            font-size: {tokens["button"]} !important;
        }
        div[data-testid="stTabs"] button p {
            font-size: {tokens["button"]} !important;
            font-weight: 700 !important;
        }
        div[data-testid="stMetricValue"], div[data-testid="stMetricLabel"] {
            font-size: {tokens["body"]} !important;
        }
        </style>
        """
        .replace('{tokens["base"]}', tokens["base"])
        .replace('{tokens["body"]}', tokens["body"])
        .replace('{tokens["caption"]}', tokens["caption"])
        .replace('{tokens["button"]}', tokens["button"])
        .replace('{tokens["h1"]}', tokens["h1"]),
        unsafe_allow_html=True,
    )


def _select_ui_scale() -> str:
    selected = st.sidebar.radio(
        "Размер интерфейса",
        options=("Крупный", "Очень крупный", "Стандартный"),
        index=0,
        key=UI_SCALE_KEY,
        horizontal=False,
    )
    return {"Стандартный": "standard", "Крупный": "large", "Очень крупный": "xlarge"}[selected]


def _build_recommended_ai_setup_commands(profile_id: str = "balanced") -> tuple[str, ...]:
    catalog = load_ai_model_profile_catalog()
    profile = find_ai_model_profile(catalog, profile_id)
    if profile is None:
        return ()
    return build_local_agent_next_commands(profile)


def _load_raw_sheets(uploaded_file) -> dict[str, pd.DataFrame]:
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix == ".csv":
        return load_csv_sheets(uploaded_file)
    if suffix in {".xlsx", ".xlsm"}:
        return load_excel_sheets(uploaded_file)
    if suffix == ".las":
        return load_las_sheets(uploaded_file)
    raise ValueError(f"Формат {suffix} не поддерживается.")


def _load_uploaded_files_sheets(uploaded_files) -> dict[str, pd.DataFrame]:
    files = list(uploaded_files or [])
    if not files:
        return {}

    combined: dict[str, pd.DataFrame] = {}
    multiple_files = len(files) > 1
    for file_index, uploaded_file in enumerate(files, start=1):
        suffix = Path(uploaded_file.name).suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"Формат {suffix} не поддерживается.")

        file_sheets = _load_raw_sheets(uploaded_file)
        file_label = Path(uploaded_file.name).stem or f"file_{file_index}"
        for sheet_name, sheet_df in file_sheets.items():
            base_name = f"{file_label} / {sheet_name}" if multiple_files else str(sheet_name)
            unique_name = base_name
            duplicate_index = 2
            while unique_name in combined:
                unique_name = f"{base_name} ({duplicate_index})"
                duplicate_index += 1
            combined[unique_name] = sheet_df

    return combined


def _depth_values_for_graphs(df: pd.DataFrame) -> pd.Series:
    if df is None or df.empty or "depth" not in df.columns:
        return pd.Series(dtype=float)
    return pd.to_numeric(df["depth"], errors="coerce")


def _filter_by_depth_range(df: pd.DataFrame, top_depth: float, bottom_depth: float) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    depth = _depth_values_for_graphs(df)
    if depth.empty or depth.isna().all():
        return df.copy()
    top = min(float(top_depth), float(bottom_depth))
    bottom = max(float(top_depth), float(bottom_depth))
    return df.loc[(depth >= top) & (depth <= bottom)].copy()

def _store_interpretation_dataset(calculated_df: pd.DataFrame, source_label: str) -> None:
    st.session_state[INTERPRETATION_SESSION_DATA_KEY] = calculated_df
    st.session_state[INTERPRETATION_SESSION_SOURCE_KEY] = str(source_label)


def _plotly_figures_to_html(figures, title: str) -> bytes:
    parts = [
        "<!doctype html>",
        "<html><head><meta charset='utf-8'>",
        f"<title>{title}</title>",
        "<style>body{font-family:Arial,sans-serif;margin:24px;} .chart{page-break-inside:avoid;margin-bottom:28px;}</style>",
        "</head><body>",
        f"<h1>{title}</h1>",
    ]
    include_plotlyjs = True
    for figure in figures:
        parts.append("<div class='chart'>")
        parts.append(pio.to_html(figure, include_plotlyjs=include_plotlyjs, full_html=False))
        parts.append("</div>")
        include_plotlyjs = False
    parts.append("</body></html>")
    return "\n".join(parts).encode("utf-8")


def _find_default_depth_column(df: pd.DataFrame) -> str:
    mapping = auto_map_columns(df.columns).mapping
    if mapping.get("depth") in df.columns:
        return mapping["depth"]
    if len(df.columns) == 0:
        return ""
    return str(df.columns[0])


def _dataframe_to_raw_sheet(df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame([list(df.columns), *df.to_numpy().tolist()])


def _render_saved_wells_panel(logger) -> None:
    records = list_wells(WELLS_STORAGE_ROOT)
    with st.expander("Сохраненные скважины", expanded=bool(records)):
        if not records:
            st.caption("Пока нет сохраненных скважин. После правки LAS сохраните версию здесь, и она появится в списке.")
            return

        record_options = {f"{record.name} | {record.updated_at} | версий: {len(record.versions)}": record for record in records}
        selected_record_label = st.selectbox(
            "Скважина",
            options=list(record_options.keys()),
            key="saved_well_record_select",
        )
        selected_record = record_options[selected_record_label]
        versions = list(selected_record.versions)
        if not versions:
            st.warning("У выбранной скважины нет сохраненных версий данных.")
            return

        version_options = {
            f"{version.label} | {version.created_at}": version
            for version in reversed(versions)
        }
        selected_version_label = st.selectbox(
            "Версия данных",
            options=list(version_options.keys()),
            key="saved_well_version_select",
        )
        selected_version = version_options[selected_version_label]

        st.caption(
            f"Статус: {selected_record.status or 'draft'}; "
            f"площадь/куст: {selected_record.area or 'не указано'}; "
            f"id: {selected_record.id}"
        )
        if selected_record.comment:
            st.caption("Комментарий: " + selected_record.comment)

        csv_col, xlsx_col, las_col = st.columns(3)
        try:
            csv_col.download_button(
                "Скачать CSV",
                data=read_well_file_bytes(WELLS_STORAGE_ROOT, selected_record.id, selected_version.id, "csv"),
                file_name=f"{selected_record.id}_{selected_version.id}.csv",
                mime="text/csv",
                use_container_width=True,
            )
            xlsx_col.download_button(
                "Скачать XLSX",
                data=read_well_file_bytes(WELLS_STORAGE_ROOT, selected_record.id, selected_version.id, "xlsx"),
                file_name=f"{selected_record.id}_{selected_version.id}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
            las_col.download_button(
                "Скачать LAS",
                data=read_well_file_bytes(WELLS_STORAGE_ROOT, selected_record.id, selected_version.id, "las"),
                file_name=f"{selected_record.id}_{selected_version.id}.las",
                mime="text/plain",
                use_container_width=True,
            )
        except Exception:
            logger.exception("saved_well_download_failed well_id=%s version_id=%s", selected_record.id, selected_version.id)
            st.error("Не удалось подготовить выгрузку сохраненной скважины. Подробности записаны в logs/app.log.")

        if st.button("Использовать выбранную версию в расчетах", use_container_width=True):
            try:
                csv_bytes = read_well_file_bytes(WELLS_STORAGE_ROOT, selected_record.id, selected_version.id, "csv")
                prepared_df = pd.read_csv(BytesIO(csv_bytes))
                st.session_state[LAS_EDITOR_SESSION_SHEETS_KEY] = {
                    f"{selected_record.name} / {selected_version.label}": _dataframe_to_raw_sheet(prepared_df)
                }
                st.session_state[LAS_EDITOR_SESSION_SUMMARY_KEY] = (
                    f"{selected_record.name}, версия {selected_version.label}, строк: {len(prepared_df)}"
                )
            except Exception:
                logger.exception("saved_well_load_to_session_failed well_id=%s version_id=%s", selected_record.id, selected_version.id)
                st.error("Не удалось загрузить сохраненную версию в расчеты. Подробности записаны в logs/app.log.")
            else:
                st.success("Версия загружена в текущую сессию. Откройте вкладку `Работа с данными`.")


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


def _initial_ai_support_chat_messages() -> list[dict[str, object]]:
    return [{"role": "assistant", "content": AI_SUPPORT_WELCOME_MESSAGE, "sources": ()}]


def _build_ai_wait_message(provider_name: str) -> str:
    if provider_name == "ollama":
        return "Ollama готовит ответ. Локальная модель может отвечать 20-120 секунд, особенно на первом вопросе."
    return "ИИ-помощник готовит ответ."


def _append_ai_support_chat_message(
    messages: list[dict[str, object]],
    role: str,
    content: str,
    sources: tuple[str, ...] = (),
) -> None:
    messages.append({"role": role, "content": content, "sources": sources})


def _render_ai_support_chat_message(message: dict[str, object]) -> None:
    role = str(message.get("role", "assistant"))
    content = str(message.get("content", ""))
    raw_sources = message.get("sources", ())
    sources = tuple(str(source) for source in raw_sources) if isinstance(raw_sources, (tuple, list)) else ()

    with st.chat_message(role):
        st.markdown(content)
        if sources:
            st.caption("Источники: " + ", ".join(sources))


def _select_ai_response_provider(ai_settings, configured_provider):
    if ai_settings.provider != "ollama":
        return configured_provider, ai_settings.provider

    mode = st.radio(
        "Режим ответа чата",
        options=("Быстро: база знаний", "Ollama: локальная модель"),
        index=0,
        key=AI_RESPONSE_MODE_KEY,
        horizontal=True,
        help="Быстрый режим отвечает по проверенной локальной базе знаний. Ollama может отвечать долго на слабом компьютере.",
    )
    if mode.startswith("Ollama"):
        return configured_provider, "ollama"
    return OfflineDocumentationProvider(), "offline-docs"


def _render_ai_assistant(logger, selected_row: pd.Series | None = None) -> None:
    st.subheader("Чат поддержки (локальный ИИ)")

    try:
        ai_settings = load_ai_settings()
        configured_provider = build_provider(ai_settings)
    except Exception:
        logger.exception("ai_settings_load_failed")
        st.error("Не удалось загрузить конфигурацию ИИ-помощника. Проверьте AI config.")
        st.caption("Подробности записаны в logs/app.log.")
        return

    status = check_ai_runtime_status(ai_settings)
    provider, active_provider_name = _select_ai_response_provider(ai_settings, configured_provider)
    if ai_settings.provider == "ollama":
        st.caption(
            "Ollama в проекте - это этот чат. Отдельной кнопки Ollama нет: "
            "приложение отправляет вопросы на локальный сервер `localhost:11434`."
        )
    else:
        st.caption(
            "Помощник работает в режиме `offline-docs`: без интернета, без модели, "
            "по локальной документации проекта."
        )

    st.caption(f"AI provider: {ai_settings.provider}; режим ответа: {active_provider_name}")
    if status.ready and ai_settings.provider == "ollama":
        model_name = ai_settings.ollama.model or "не указана"
        st.success(f"Локальный ИИ подключен: Ollama, модель `{model_name}`. Пишите вопрос в поле чата ниже.")
    elif status.ready:
        st.success(status.message)
    else:
        st.warning(status.message)
    if status.available_models:
        st.caption("Локальные модели на этом компьютере: " + ", ".join(status.available_models))

    setup_commands = _build_recommended_ai_setup_commands()
    if setup_commands:
        install_note, *commands = setup_commands
        expander_title = "Проверка и запуск локального ИИ" if status.ready else "Подготовка локального ИИ"
        with st.expander(expander_title, expanded=not status.ready):
            if status.ready:
                st.caption("Ollama уже готов. Эти команды нужны для проверки, повторного запуска или настройки другой машины.")
            else:
                st.caption(install_note)
            st.code("\n".join(commands), language="powershell")

    if AI_SUPPORT_CHAT_KEY not in st.session_state:
        st.session_state[AI_SUPPORT_CHAT_KEY] = _initial_ai_support_chat_messages()
    messages = st.session_state[AI_SUPPORT_CHAT_KEY]

    left, right = st.columns([3, 1])
    left.caption("Быстрые вопросы")
    if right.button("Очистить чат", key="local_ai_clear_chat", use_container_width=True):
        st.session_state[AI_SUPPORT_CHAT_KEY] = _initial_ai_support_chat_messages()
        messages = st.session_state[AI_SUPPORT_CHAT_KEY]

    quick_question = ""
    quick_columns = st.columns(len(AI_SUPPORT_QUICK_QUESTIONS))
    for index, (label, prompt) in enumerate(AI_SUPPORT_QUICK_QUESTIONS):
        if quick_columns[index].button(label, key=f"local_ai_quick_{index}", use_container_width=True):
            quick_question = prompt

    for message in messages:
        _render_ai_support_chat_message(message)

    typed_question = st.chat_input(
        "Напишите вопрос по данным, формулам, Ollama или выбранному интервалу",
        key="local_ai_chat_input",
    )
    question = quick_question or typed_question or ""
    if not question.strip():
        return

    assistant = LocalAssistant(provider=provider)
    interval_row = selected_row if ai_settings.privacy.send_selected_interval_only else None
    logger.info(
        "ai_question_received provider=%s ready=%s chars=%d has_interval=%s",
        safe_log_value(active_provider_name),
        status.ready,
        len(question),
        interval_row is not None,
    )
    _append_ai_support_chat_message(messages, "user", question.strip())
    _render_ai_support_chat_message(messages[-1])

    try:
        started_at = time.perf_counter()
        with st.spinner(_build_ai_wait_message(active_provider_name)):
            answer = assistant.answer(question, interval_row=interval_row)
        elapsed_seconds = time.perf_counter() - started_at
    except Exception:
        logger.exception(
            "ai_answer_failed provider=%s ready=%s chars=%d has_interval=%s",
            safe_log_value(active_provider_name),
            status.ready,
            len(question),
            interval_row is not None,
        )
        st.error("ИИ-помощник не смог подготовить ответ. Подробности записаны в logs/app.log.")
        return

    logger.info(
        "ai_answer_generated provider=%s sources=%d seconds=%.1f",
        safe_log_value(answer.provider_name),
        len(answer.sources),
        elapsed_seconds,
    )

    _append_ai_support_chat_message(messages, "assistant", answer.answer, answer.sources)
    _render_ai_support_chat_message(messages[-1])
    st.caption(f"Ответ подготовлен за {elapsed_seconds:.1f} сек.")


def _read_documentation_markdown(relative_path: str) -> str:
    candidate = Path(relative_path)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"Unsafe documentation path: {relative_path}")

    path = ROOT_DIR / candidate
    return path.read_text(encoding="utf-8")


def _render_documentation_tab() -> None:
    st.subheader("Инструкции и документация")
    st.caption(
        "Эта вкладка нужна, чтобы новый пользователь мог развернуть проект, "
        "загрузить файл, понять предупреждения и проверить локальный AI без внешних инструкций."
    )

    quick_start, verification = st.columns(2)
    with quick_start:
        st.markdown("### Быстрый запуск")
        st.code(
            "cd C:\\OSPanel\\home\\gas-ratio-pro\n"
            f"{APP_LAUNCH_SCRIPT}\n"
            f"# или без скрипта:\n"
            f"{APP_LAUNCH_COMMAND}",
            language="powershell",
        )
        st.markdown(
            "1. Откройте локальный адрес Streamlit.\n"
            "2. Загрузите LAS (рекомендуется), CSV, XLSX или XLSM.\n"
            "3. Проверьте строку заголовков и mapping.\n"
            "4. Выберите интервал и смотрите расчеты, палетки и графики."
        )

    with verification:
        st.markdown("### Проверка готовности")
        st.code(
            "python -m pytest\n"
            "python scripts/preflight.py\n"
            "python scripts/evaluate_ai.py\n"
            "python scripts/ai_config.py status",
            language="powershell",
        )
        st.markdown(
            "Если включен Ollama, preflight должен показать, что локальная модель найдена. "
            "Если интернета нет или модель не нужна, provider `offline-docs` продолжает работать по локальным документам."
        )

    st.markdown("### Основной рабочий сценарий")
    st.markdown(
        "1. Загрузите LAS, CSV или Excel-файл и выберите набор данных.\n"
        "2. Проверьте первые строки и строку заголовков.\n"
        "3. Исправьте сопоставление колонок, если авто-mapping ошибся.\n"
        "4. Проверьте предупреждения и режим `Ch`.\n"
        "5. Выберите интервал, проверьте Pixler/ternary и depth-графики.\n"
        "6. Скачайте расчетную таблицу через `Экспорт CSV`, если результат нужен дальше."
    )

    st.markdown("### Чат поддержки")
    st.markdown(
        "Чат поддержки отвечает по локальной документации, Q/A-примерам, формулам, "
        "Ollama-настройке и выбранному интервалу. Полная таблица и сырые строки файла "
        "в чат не передаются. Если вопрос выходит за пределы базы знаний, помощник должен "
        "сказать, что нужно добавить методику или уточнить данные."
    )

    for index, (title, relative_path) in enumerate(DOCUMENTATION_TAB_DOCS):
        with st.expander(title, expanded=index == 0):
            st.markdown(_read_documentation_markdown(relative_path))

def _render_las_editor(logger) -> None:
    st.subheader("LAS-редактор")
    st.caption("Подготовка LAS перед расчетами: проверка глубины, смена шага, добавление строк и ручная правка.")
    _render_saved_wells_panel(logger)

    saved_summary = st.session_state.get(LAS_EDITOR_SESSION_SUMMARY_KEY)
    if saved_summary:
        st.success(f"В рабочую сессию сохранено: {saved_summary}")

    uploaded_file = st.file_uploader(
        "LAS-файл для редактора",
        type=["las"],
        key="las_editor_file_upload",
    )
    if uploaded_file is None:
        st.info("Загрузите LAS-файл, чтобы проверить глубины и подготовить данные перед расчетом.")
        return

    try:
        sheets = load_las_sheets(uploaded_file)
        raw_df = sheets["LAS"]
        detected_header = detect_header_row(raw_df)
        prepared_df = prepare_dataframe_with_header(raw_df, detected_header.header_row)
        logger.info(
            "las_editor_file_read rows=%d columns=%d header_row=%d",
            len(prepared_df),
            len(prepared_df.columns),
            detected_header.header_row,
        )
    except Exception:
        logger.exception("las_editor_file_read_failed")
        st.error("Не удалось прочитать LAS-файл в редакторе. Проверьте секции ~Curve и ~ASCII.")
        st.caption("Подробности записаны в logs/app.log.")
        return

    if prepared_df.empty:
        st.error("LAS прочитан, но после строки заголовков не осталось данных.")
        return

    st.markdown("### Исходные кривые")
    st.dataframe(prepared_df.head(20), use_container_width=True)

    column_names = [str(column) for column in prepared_df.columns]
    default_depth_column = _find_default_depth_column(prepared_df)
    default_depth_index = column_names.index(default_depth_column) if default_depth_column in column_names else 0

    depth_col, step_col, custom_step_col = st.columns(3)
    depth_column = depth_col.selectbox(
        "Кривая глубины",
        options=column_names,
        index=default_depth_index,
        key="las_editor_depth_column",
    )
    step_preset = step_col.selectbox(
        "Целевой шаг, м",
        options=LAS_EDITOR_STEP_PRESETS,
        index=1,
        key="las_editor_step_preset",
    )
    if step_preset == "Другой":
        target_step = custom_step_col.text_input(
            "Пользовательский шаг, м",
            value="0.2",
            key="las_editor_custom_step",
        )
    else:
        target_step = step_preset
        custom_step_col.metric("Выбранный шаг", target_step)

    fill_labels = [label for label, _value in LAS_EDITOR_FILL_STRATEGIES]
    fill_values = dict(LAS_EDITOR_FILL_STRATEGIES)
    fill_label = st.selectbox(
        "Заполнение добавленных строк",
        options=fill_labels,
        index=0,
        key="las_editor_fill_strategy",
    )
    fill_strategy = fill_values[fill_label]

    try:
        result = resample_las_data(
            prepared_df,
            depth_column=depth_column,
            target_step=target_step,
            fill_strategy=fill_strategy,
        )
    except Exception:
        logger.exception("las_editor_resample_failed")
        st.error("Не удалось построить сетку глубин. Проверьте колонку глубины и шаг.")
        st.caption("Подробности записаны в logs/app.log.")
        return

    diagnostics = result.diagnostics
    metrics = st.columns(5)
    metrics[0].metric("Строк", diagnostics.row_count)
    metrics[1].metric("Глубин", diagnostics.valid_depth_count)
    metrics[2].metric("Мин.", diagnostics.min_depth if diagnostics.min_depth is not None else "нет")
    metrics[3].metric("Макс.", diagnostics.max_depth if diagnostics.max_depth is not None else "нет")
    metrics[4].metric("Добавлено", len(result.added_depths))

    if result.warnings:
        for warning in result.warnings:
            st.warning(warning)
    else:
        st.success("Глубина выглядит ровной по выбранному шагу.")

    if result.added_depths:
        preview_depths = ", ".join(str(depth) for depth in result.added_depths[:40])
        if len(result.added_depths) > 40:
            preview_depths += ", ..."
        st.caption("Добавленные глубины: " + preview_depths)

    st.markdown("### Ручная правка перед расчетом")
    edited_df = st.data_editor(
        result.data,
        use_container_width=True,
        num_rows="dynamic",
        key="las_editor_data_editor",
    )

    save_col, export_col = st.columns(2)
    if save_col.button("Сохранить для расчетов", type="primary", use_container_width=True):
        st.session_state[LAS_EDITOR_SESSION_SHEETS_KEY] = {"LAS-редактор": _dataframe_to_raw_sheet(edited_df)}
        st.session_state[LAS_EDITOR_SESSION_SUMMARY_KEY] = (
            f"{len(edited_df)} строк, шаг {target_step}, заполнение: {fill_label}"
        )
        logger.info(
            "las_editor_saved_to_session rows=%d columns=%d added_depths=%d fill_strategy=%s",
            len(edited_df),
            len(edited_df.columns),
            len(result.added_depths),
            safe_log_value(fill_strategy),
        )
        st.success("Исправленные LAS-данные сохранены. Откройте вкладку `Работа с данными` и включите данные из редактора.")

    export_col.download_button(
        "Экспорт CSV",
        data=export_csv_bytes(edited_df),
        file_name="las_editor_prepared.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.markdown("### Сохранить скважину локально")
    records = list_wells(WELLS_STORAGE_ROOT)
    existing_options = ["Новая скважина"] + [f"{record.name} | {record.id}" for record in records]
    selected_existing = st.selectbox(
        "Куда сохранить",
        options=existing_options,
        key="las_editor_save_target",
    )
    selected_record = None
    if selected_existing != "Новая скважина":
        selected_record = records[existing_options.index(selected_existing) - 1]

    name_col, area_col, status_col = st.columns(3)
    default_name = selected_record.name if selected_record else Path(getattr(uploaded_file, "name", "well")).stem
    well_name = name_col.text_input("Название скважины", value=default_name, key="las_editor_well_name")
    well_area = area_col.text_input("Куст/площадь", value=selected_record.area if selected_record else "", key="las_editor_well_area")
    well_status = status_col.selectbox(
        "Статус",
        options=("draft", "checked", "approved"),
        index=("draft", "checked", "approved").index(selected_record.status) if selected_record and selected_record.status in ("draft", "checked", "approved") else 0,
        key="las_editor_well_status",
    )
    well_comment = st.text_area(
        "Комментарий",
        value=selected_record.comment if selected_record else "",
        key="las_editor_well_comment",
    )
    version_label = st.text_input(
        "Название версии",
        value=f"LAS editor step {target_step}",
        key="las_editor_version_label",
    )

    if st.button("Сохранить версию скважины", use_container_width=True):
        try:
            saved_record = save_well_version(
                edited_df,
                root=WELLS_STORAGE_ROOT,
                well_name=well_name,
                well_id=selected_record.id if selected_record else None,
                area=well_area,
                status=well_status,
                comment=well_comment,
                version_label=version_label,
                depth_column=depth_column,
                metadata={
                    "source": "las_editor",
                    "target_step": str(target_step),
                    "fill_strategy": fill_strategy,
                    "added_depth_count": len(result.added_depths),
                },
            )
        except Exception:
            logger.exception("well_version_save_failed")
            st.error("Не удалось сохранить скважину. Подробности записаны в logs/app.log.")
        else:
            logger.info("well_version_saved well_id=%s rows=%d", safe_log_value(saved_record.id), len(edited_df))
            st.success(f"Скважина сохранена локально: {saved_record.name} ({saved_record.id}).")


def _render_workspace(logger) -> None:
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

    editor_sheets = st.session_state.get(LAS_EDITOR_SESSION_SHEETS_KEY)
    use_editor_data = False
    if editor_sheets:
        summary = st.session_state.get(LAS_EDITOR_SESSION_SUMMARY_KEY, "данные подготовлены")
        st.info(f"Доступны данные из LAS-редактора: {summary}")
        use_editor_data = st.checkbox(
            "Использовать данные из LAS-редактора",
            value=True,
            key="workspace_use_las_editor_data",
        )

    if use_editor_data:
        suffix = ".las-editor"
        sheets = editor_sheets
        logger.info("editor_data_selected sheet_count=%d", len(sheets))
    else:
        uploaded_files = st.file_uploader(
            "Загрузка файлов",
            type=["csv", "xlsx", "xlsm", "las"],
            accept_multiple_files=True,
        )

        if not uploaded_files:
            st.info("Загрузите один или несколько LAS, CSV, XLSX или XLSM файлов с газовыми данными.")
            _render_ai_assistant(logger)
            return

        suffixes = sorted({Path(uploaded_file.name).suffix.lower() for uploaded_file in uploaded_files})
        unsupported_suffixes = [suffix for suffix in suffixes if suffix not in SUPPORTED_EXTENSIONS]
        if unsupported_suffixes:
            logger.warning("unsupported_file_extension extension=%s", safe_log_value(",".join(unsupported_suffixes)))
            st.error("Формат файла не поддерживается в v0.3.")
            return

        logger.info(
            "file_upload_received count=%d extensions=%s total_size=%s",
            len(uploaded_files),
            safe_log_value(",".join(suffixes)),
            safe_log_value(sum(int(getattr(uploaded_file, "size", 0) or 0) for uploaded_file in uploaded_files)),
        )

        try:
            sheets = _load_uploaded_files_sheets(uploaded_files)
            suffix = ",".join(suffixes)
            logger.info("file_read_success extensions=%s sheet_count=%d", safe_log_value(suffix), len(sheets))
        except Exception:
            logger.exception("file_read_failed extensions=%s", safe_log_value(",".join(suffixes)))
            st.error("Не удалось прочитать файл. Проверьте формат и доступность данных.")
            st.caption("Подробности записаны в logs/app.log.")
            return

    if not sheets:
        logger.warning("file_read_empty extension=%s", safe_log_value(suffix))
        st.error("Файл прочитан, но листы или строки данных не найдены.")
        return

    sheet_name = st.selectbox("Выбор набора данных", options=list(sheets.keys()))
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
    _store_interpretation_dataset(calculated_df, str(sheet_name))
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


def _select_x_range(label: str, key_prefix: str) -> tuple[float, float] | None:
    auto_scale = st.checkbox(f"Автомасштаб X: {label}", value=True, key=f"{key_prefix}_x_auto")
    if auto_scale:
        return None

    left, right = st.columns(2)
    min_value = left.number_input(
        f"X min: {label}",
        value=0.0,
        step=1.0,
        key=f"{key_prefix}_x_min",
    )
    max_value = right.number_input(
        f"X max: {label}",
        value=100.0,
        step=1.0,
        key=f"{key_prefix}_x_max",
    )
    if min_value == max_value:
        st.warning(f"Для {label} X min и X max совпадают. Используется автомасштаб.")
        return None
    return (min(float(min_value), float(max_value)), max(float(min_value), float(max_value)))


def _render_interpretation_graphs_tab(logger) -> None:
    st.subheader("Интерпретационные графики")
    calculated_df = st.session_state.get(INTERPRETATION_SESSION_DATA_KEY)
    if calculated_df is None or calculated_df.empty:
        st.info("Сначала выполните расчет во вкладке `Работа с данными`. После этого здесь появятся графики и таблица интерпретации.")
        return

    source_label = st.session_state.get(INTERPRETATION_SESSION_SOURCE_KEY, "текущий расчет")
    st.caption(f"Источник данных: {source_label}")

    depth = _depth_values_for_graphs(calculated_df)
    valid_depth = depth.dropna()
    if valid_depth.empty:
        st.warning("В расчетной таблице нет числовой глубины. Графики будут построены по техническому индексу.")
        filtered_df = calculated_df.copy()
        depth_range = None
    else:
        min_depth = float(valid_depth.min())
        max_depth = float(valid_depth.max())
        mode = st.radio(
            "Диапазон глубины",
            options=("Весь интервал", "Ручной интервал"),
            horizontal=True,
            key="interpretation_depth_range_mode",
        )
        if mode == "Ручной интервал":
            top_col, bottom_col = st.columns(2)
            top_depth = top_col.number_input("Верх, м", value=min_depth, step=0.1, key="interpretation_top_depth")
            bottom_depth = bottom_col.number_input("Низ, м", value=max_depth, step=0.1, key="interpretation_bottom_depth")
        else:
            top_depth = min_depth
            bottom_depth = max_depth
        depth_range = (min(float(top_depth), float(bottom_depth)), max(float(top_depth), float(bottom_depth)))
        filtered_df = _filter_by_depth_range(calculated_df, depth_range[0], depth_range[1])

    st.metric("Строк в выбранном интервале", len(filtered_df))
    if filtered_df.empty:
        st.error("В выбранном диапазоне глубин нет строк.")
        return

    height = st.slider("Высота графиков", min_value=420, max_value=1100, value=650, step=10, key="interpretation_chart_height")
    selected_tracks = st.multiselect(
        "Графики",
        options=("Интерпретация", "C1-C5", "Wh/Bh/Ch", "Pixler ratios"),
        default=("Интерпретация", "C1-C5", "Wh/Bh/Ch", "Pixler ratios"),
        key="interpretation_tracks",
    )

    with st.expander("Ручной масштаб X", expanded=False):
        gas_x_range = _select_x_range("C1-C5", "interpretation_gas")
        ratio_x_range = _select_x_range("Wh/Bh/Ch", "interpretation_ratio")
        pixler_x_range = _select_x_range("Pixler ratios", "interpretation_pixler")

    figures = []
    if "Интерпретация" in selected_tracks:
        figures.append(build_depth_interpretation_track(filtered_df, depth_range=depth_range, height=height))
    if "C1-C5" in selected_tracks:
        figures.append(build_depth_gas_tracks(filtered_df, depth_range=depth_range, x_range=gas_x_range, height=height))
    if "Wh/Bh/Ch" in selected_tracks:
        figures.append(build_depth_ratio_tracks(filtered_df, depth_range=depth_range, x_range=ratio_x_range, height=height))
    if "Pixler ratios" in selected_tracks:
        figures.append(build_depth_pixler_tracks(filtered_df, depth_range=depth_range, x_range=pixler_x_range, height=height))

    if not figures:
        st.warning("Выберите хотя бы один график.")
    for figure in figures:
        st.plotly_chart(figure, use_container_width=True)

    if figures:
        report_title = f"Gas Ratio Interpreter - {source_label}"
        st.download_button(
            "HTML для печати",
            data=_plotly_figures_to_html(figures, report_title),
            file_name="gas_ratio_depth_graphs.html",
            mime="text/html",
            use_container_width=True,
        )

    st.subheader("Сводка интерпретации")
    st.dataframe(summarize_interpretation(filtered_df), use_container_width=True)
    st.subheader("Таблица выбранного интервала")
    st.dataframe(filtered_df, use_container_width=True)
    st.download_button(
        "Экспорт выбранного интервала CSV",
        data=export_csv_bytes(filtered_df),
        file_name="gas_ratio_selected_interval.csv",
        mime="text/csv",
        use_container_width=True,
    )
    logger.info("interpretation_graphs_rendered rows=%d figure_count=%d", len(filtered_df), len(figures))


def _curve_group_label(group: str) -> str:
    return CURVE_GROUP_LABELS.get(group, group)


def _render_las_correlation_tab(logger) -> None:
    st.subheader("LAS-корреляция")
    st.caption("Загрузите несколько LAS, чтобы смотреть ГИС-кривые рядом с газами по общей глубине.")

    uploaded_files = st.file_uploader(
        "LAS-файлы для корреляции",
        type=["las"],
        accept_multiple_files=True,
        key="las_correlation_files",
    )
    if not uploaded_files:
        st.info("Загрузите два или больше LAS-файла для сравнения скважин. Один LAS тоже можно открыть для проверки треков.")
        return

    try:
        wells = prepare_las_correlation_wells(uploaded_files)
    except Exception:
        logger.exception("las_correlation_read_failed")
        st.error("Не удалось прочитать LAS-файлы для корреляции. Проверьте секции ~Curve и ~ASCII.")
        st.caption("Подробности записаны в logs/app.log.")
        return

    summary_rows = []
    for well in wells:
        summary_rows.append(
            {
                "Скважина": well.name,
                "Строк": well.row_count,
                "Depth curve": well.depth_column,
                "Мин. глубина": well.min_depth,
                "Макс. глубина": well.max_depth,
                "ГИС": sum(len(well.curve_groups.get(group, ())) for group in DEFAULT_GIS_GROUPS),
                "Газы": sum(len(well.curve_groups.get(group, ())) for group in DEFAULT_GAS_GROUPS),
                "Прочие": len(well.curve_groups.get("other", ())),
            }
        )
    st.dataframe(pd.DataFrame(summary_rows), use_container_width=True)

    all_well_names = [well.name for well in wells]
    selected_well_names = st.multiselect(
        "Скважины на графике",
        options=all_well_names,
        default=all_well_names,
        key="las_correlation_selected_wells",
    )
    selected_wells = [well for well in wells if well.name in selected_well_names]
    if not selected_wells:
        st.warning("Выберите хотя бы одну скважину.")
        return

    group_options = [
        group
        for group in CURVE_GROUP_LABELS
        if group not in {"depth", "lithology", "other"}
    ]
    left, right = st.columns(2)
    gis_groups = left.multiselect(
        "ГИС-группы слева",
        options=group_options,
        default=[group for group in DEFAULT_GIS_GROUPS if group in group_options],
        format_func=_curve_group_label,
        key="las_correlation_gis_groups",
    )
    gas_groups = right.multiselect(
        "Газовые группы справа",
        options=group_options,
        default=[group for group in DEFAULT_GAS_GROUPS if group in group_options],
        format_func=_curve_group_label,
        key="las_correlation_gas_groups",
    )

    valid_depths = [
        value
        for well in selected_wells
        for value in (well.min_depth, well.max_depth)
        if value is not None
    ]
    depth_range = None
    if valid_depths:
        min_depth = float(min(valid_depths))
        max_depth = float(max(valid_depths))
        range_mode = st.radio(
            "Диапазон глубины",
            options=("Общий весь интервал", "Ручной интервал"),
            horizontal=True,
            key="las_correlation_depth_range_mode",
        )
        if range_mode == "Ручной интервал":
            top_col, bottom_col = st.columns(2)
            top_depth = top_col.number_input("Верх, м", value=min_depth, step=0.1, key="las_correlation_top_depth")
            bottom_depth = bottom_col.number_input("Низ, м", value=max_depth, step=0.1, key="las_correlation_bottom_depth")
            depth_range = (min(float(top_depth), float(bottom_depth)), max(float(top_depth), float(bottom_depth)))

    height_per_well = st.slider(
        "Высота на скважину",
        min_value=320,
        max_value=750,
        value=430,
        step=10,
        key="las_correlation_height_per_well",
    )
    figure = build_las_correlation_figure(
        selected_wells,
        gis_groups=tuple(gis_groups),
        gas_groups=tuple(gas_groups),
        depth_range=depth_range,
        height_per_well=height_per_well,
    )
    st.plotly_chart(figure, use_container_width=True)
    st.download_button(
        "HTML для печати корреляции",
        data=_plotly_figures_to_html([figure], "Gas Ratio Interpreter - LAS correlation"),
        file_name="las_correlation.html",
        mime="text/html",
        use_container_width=True,
    )

    with st.expander("Кривые по скважинам", expanded=False):
        for well in selected_wells:
            st.markdown(f"#### {well.name}")
            if well.warnings:
                for warning in well.warnings:
                    st.warning(warning)
            group_rows = [
                {
                    "Группа": _curve_group_label(group),
                    "Кривые": ", ".join(columns),
                }
                for group, columns in well.curve_groups.items()
                if columns
            ]
            st.dataframe(pd.DataFrame(group_rows), use_container_width=True)

    logger.info("las_correlation_rendered wells=%d", len(selected_wells))

def main() -> None:
    st.set_page_config(page_title="Gas Ratio Interpreter v0.3", layout="wide")
    ui_scale = _select_ui_scale()
    _apply_app_style(ui_scale)
    st.title("Gas Ratio Interpreter v0.3")
    st.caption(INTERPRETATION_NOTE)

    logger = configure_logging()
    logger.info("streamlit_app_started")

    workspace_tab, las_editor_tab, correlation_tab, graphs_tab, docs_tab = st.tabs(list(APP_TABS))
    with workspace_tab:
        _render_workspace(logger)
    with las_editor_tab:
        _render_las_editor(logger)
    with correlation_tab:
        _render_las_correlation_tab(logger)
    with graphs_tab:
        _render_interpretation_graphs_tab(logger)
    with docs_tab:
        _render_documentation_tab()


if __name__ == "__main__":
    main()
