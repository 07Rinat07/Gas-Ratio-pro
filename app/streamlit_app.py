from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd
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


SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xlsm", ".las"}
APP_LAUNCH_COMMAND = "python -m streamlit run app/streamlit_app.py"
APP_LAUNCH_SCRIPT = ".\\run_app.ps1"
AI_SUPPORT_CHAT_KEY = "local_ai_support_chat_messages"
AI_RESPONSE_MODE_KEY = "local_ai_response_mode"
UI_SCALE_KEY = "ui_scale"
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


DOCUMENTATION_TAB_DOCS: tuple[tuple[str, str], ...] = (
    ("Быстрый старт", "docs/setup.md"),
    ("Руководство пользователя", "docs/user_guide.md"),
    ("Формат входных данных", "docs/data_format.md"),
    ("План LAS-редактора", "docs/las_editor_plan.md"),
    ("Формулы", "docs/formulas.md"),
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

    uploaded_file = st.file_uploader(
        "Загрузка файла",
        type=["csv", "xlsx", "xlsm", "las"],
    )

    if uploaded_file is None:
        st.info("Загрузите LAS, CSV, XLSX или XLSM файл с газовыми данными.")
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


def main() -> None:
    st.set_page_config(page_title="Gas Ratio Interpreter v0.3", layout="wide")
    ui_scale = _select_ui_scale()
    _apply_app_style(ui_scale)
    st.title("Gas Ratio Interpreter v0.3")
    st.caption(INTERPRETATION_NOTE)

    logger = configure_logging()
    logger.info("streamlit_app_started")

    workspace_tab, docs_tab = st.tabs(["Работа с данными", "Инструкции и документация"])
    with workspace_tab:
        _render_workspace(logger)
    with docs_tab:
        _render_documentation_tab()


if __name__ == "__main__":
    main()
