from __future__ import annotations

import importlib
import sys
from datetime import datetime
from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.calculations import CH_WARNING, calculate_gas_ratios
from core.diagnostics import (
    build_mapping_diagnostics,
    build_ratio_nan_diagnostics,
    interval_ratio_diagnostic_messages,
    mapping_warning_messages,
    ratio_nan_warning_messages,
)
from core.interpretation import INTERPRETATION_NOTE, add_interpretation, summarize_interpretation
from core.logging_config import configure_logging, safe_log_value
from core.models import CalculationConfig, STANDARD_FIELDS
from importers.csv_importer import load_csv_sheets
from importers.excel_importer import load_excel_sheets
from importers.header_detector import detect_header_row, prepare_dataframe_with_header
from importers.las_importer import load_las_sheets
from las_correlation import (
    CURVE_GROUP_LABELS,
    DEFAULT_PROJECT_ID,
    DEFAULT_PROJECTS_ROOT,
    DEFAULT_GAS_GROUPS,
    DEFAULT_GIS_GROUPS,
    LasCorrelationSettings,
    apply_curve_group_overrides,
    build_las_correlation_figure,
    build_las_correlation_interval_table,
    build_las_curve_comparison_figure,
    curve_group_rows,
    curve_names_for_comparison,
    prepare_las_correlation_wells,
    load_project_correlation_settings,
    save_project_correlation_settings,
    settings_from_dict,
    settings_summary,
    settings_to_dict,
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
from palettes.well_log_tablet import (
    DEFAULT_TABLET_COLORS,
    TABLET_FILL_MODES,
    InterpretationMarker,
    InterpretationZone,
    build_interpretation_zone_table,
    build_marker_interpretation_table,
    build_well_log_tablet,
    default_tablet_columns,
    mud_gas_literature_markers,
    mud_gas_literature_tablet_columns,
    normalize_track_configs,
    numeric_tablet_columns,
    tablet_units_from_dataframe,
)
from palettes.pixler import build_pixler_palette
from palettes.ternary import build_ternary_palette
from projects import ProjectRecord, create_project, ensure_default_project, list_projects
from projects import calculations as project_calculations
from projects import exports as project_exports
from projects import graph_settings as project_graph_settings
from projects import las_files as project_las_files
from reports.export_csv import export_csv_bytes
from reports.export_html import HtmlReportMetadata, HtmlReportTable, build_plotly_html_report
from reports.interval_report import build_interval_print_report
from reports.export_las import export_las_bytes
from reports.export_xlsx import export_xlsx_bytes
from reports.export_static import (
    SUPPORTED_STATIC_EXPORT_FORMATS,
    StaticExportOptions,
    StaticExportUnavailableError,
    export_plotly_static_bytes,
)
from wells.repository import DEFAULT_WELLS_ROOT, list_wells, read_well_file_bytes, save_well_version

project_calculations = importlib.reload(project_calculations)
project_exports = importlib.reload(project_exports)
project_las_files = importlib.reload(project_las_files)
list_project_calculations = project_calculations.list_project_calculations
read_project_calculation_dataframe = project_calculations.read_project_calculation_dataframe
read_project_calculation_file_bytes = project_calculations.read_project_calculation_file_bytes
read_project_calculation_metadata = project_calculations.read_project_calculation_metadata
save_project_calculation = project_calculations.save_project_calculation
list_project_exports = project_exports.list_project_exports
read_project_export_file_bytes = project_exports.read_project_export_file_bytes
save_project_export = project_exports.save_project_export
DEFAULT_INTERPRETATION_TRACKS = project_graph_settings.DEFAULT_INTERPRETATION_TRACKS
InterpretationGraphSettings = project_graph_settings.InterpretationGraphSettings
load_project_interpretation_graph_settings = project_graph_settings.load_project_interpretation_graph_settings
save_project_interpretation_graph_settings = project_graph_settings.save_project_interpretation_graph_settings
export_project_las_files_zip = project_las_files.export_project_las_files_zip
list_project_las_files = project_las_files.list_project_las_files
list_project_las_wells = project_las_files.list_project_las_wells
read_project_las_file_bytes = project_las_files.read_project_las_file_bytes
read_project_las_file_dataframe = project_las_files.read_project_las_file_dataframe
save_project_las_file = project_las_files.save_project_las_file
set_project_las_file_archived = project_las_files.set_project_las_file_archived

SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xlsm", ".las"}
WELLS_STORAGE_ROOT = ROOT_DIR / DEFAULT_WELLS_ROOT
LAS_CORRELATION_PROJECTS_ROOT = ROOT_DIR / DEFAULT_PROJECTS_ROOT
APP_LAUNCH_COMMAND = "python -m streamlit run app/streamlit_app.py"
APP_LAUNCH_SCRIPT = ".\\run_app.ps1"
UI_SCALE_KEY = "ui_scale"
UI_LAYOUT_KEY = "ui_layout"
LAS_EDITOR_SESSION_SHEETS_KEY = "las_editor_session_sheets"
LAS_EDITOR_SESSION_SUMMARY_KEY = "las_editor_session_summary"
PROJECT_SESSION_SHEETS_KEY = "project_session_sheets"
PROJECT_SESSION_SUMMARY_KEY = "project_session_summary"
PROJECT_SESSION_PROJECT_ID_KEY = "project_session_project_id"
INTERPRETATION_SESSION_DATA_KEY = "interpretation_session_data"
INTERPRETATION_SESSION_SOURCE_KEY = "interpretation_session_source"
LAS_CORRELATION_SETTINGS_KEY = "las_correlation_settings"
ACTIVE_PROJECT_ID_KEY = "active_project_id"
PROJECT_SELECTBOX_KEY_PREFIX = "active_project_select"
APP_TABS = (
    "Старт",
    "Работа с данными",
    "LAS-редактор",
    "LAS-корреляция",
    "Интерпретационные графики",
    "Инструкции и документация",
)
LAS_EDITOR_STEP_PRESETS: tuple[str, ...] = ("0.1", "0.2", "0.5", "1.0", "1.2", "2.0", "Другой")
LAS_EDITOR_FILL_STRATEGIES: tuple[tuple[str, str], ...] = (
    ("Оставить пусто", "empty"),
    ("Значение сверху", "top"),
    ("Значение снизу", "bottom"),
    ("Среднее сверху/снизу", "average"),
    ("Линейная интерполяция", "linear"),
)
VIEW_MODE_BY_WELL = "По скважинам"
VIEW_MODE_BY_CURVE = "По кривой"
SUPPORTED_VIEW_MODES: tuple[str, ...] = (VIEW_MODE_BY_WELL, VIEW_MODE_BY_CURVE)
TABLET_TRACK_OPTION = "Планшет"
INTERPRETATION_TRACK_OPTIONS: tuple[str, ...] = tuple(dict.fromkeys((*DEFAULT_INTERPRETATION_TRACKS, TABLET_TRACK_OPTION)))

UI_LAYOUT_PROFILES: dict[str, dict[str, str]] = {
    "standard": {
        "label": "Обычный монитор",
        "max_width": "1200px",
        "columns": "2",
        "description": "Для ноутбуков и стандартных экранов: меньше горизонтальной прокрутки и компактные карточки.",
    },
    "wide": {
        "label": "Широкий экран",
        "max_width": "1680px",
        "columns": "3",
        "description": "Для широких мониторов: больше места под планшеты, корреляцию и таблицы интервала.",
    },
}




START_ACTIONS: tuple[dict[str, str], ...] = (
    {
        "title": "Загрузить данные",
        "target_tab": "Работа с данными",
        "description": "Импорт LAS, CSV, XLSX/XLSM, проверка заголовков, mapping, расчет коэффициентов и первичная интерпретация.",
        "when": "Когда есть файл с газовым каротажем или расчетная таблица.",
    },
    {
        "title": "Открыть LAS-редактор",
        "target_tab": "LAS-редактор",
        "description": "Проверка глубины, подготовка сетки, ручная правка LAS и сохранение подготовленной версии в проект.",
        "when": "Когда LAS нужно привести в порядок перед расчетами или корреляцией.",
    },
    {
        "title": "Открыть корреляцию",
        "target_tab": "LAS-корреляция",
        "description": "Сравнение нескольких скважин, группировка кривых, X-scale, интервал, печатный HTML и графический экспорт.",
        "when": "Когда нужно сопоставить несколько LAS по одному интервалу.",
    },
    {
        "title": "Открыть интерпретационные графики",
        "target_tab": "Интерпретационные графики",
        "description": "Планшет, маркеры, зоны интерпретации, interval report и экспорт PNG/PDF/SVG.",
        "when": "Когда расчет уже выполнен и нужно подготовить инженерный материал.",
    },
    {
        "title": "Открыть документацию",
        "target_tab": "Инструкции и документация",
        "description": "Формулы, troubleshooting, формат данных, методика mud gas analysis и план проекта.",
        "when": "Когда нужно проверить ограничения методики или понять предупреждение.",
    },
)

DOCUMENTATION_TAB_DOCS: tuple[tuple[str, str], ...] = (
    ("Быстрый старт", "docs/setup.md"),
    ("Руководство пользователя", "docs/user_guide.md"),
    ("Формат входных данных", "docs/data_format.md"),
    ("План LAS-редактора", "docs/las_editor_plan.md"),
    ("План LAS-корреляции", "docs/las_correlation_plan.md"),
    ("Формулы", "docs/formulas.md"),
    ("Mud gas literature", "docs/mud_gas_analysis_literature.md"),
    ("План проекта", "docs/project_plan.md"),
    ("Troubleshooting", "docs/troubleshooting.md"),
)


def _apply_app_style(scale: str = "large", layout: str = "wide") -> None:
    scale_tokens = {
        "standard": {"base": "17px", "body": "1rem", "caption": "0.95rem", "button": "1rem", "h1": "2.35rem"},
        "large": {"base": "20px", "body": "1.13rem", "caption": "1.02rem", "button": "1.08rem", "h1": "2.75rem"},
        "xlarge": {"base": "22px", "body": "1.22rem", "caption": "1.08rem", "button": "1.16rem", "h1": "3.05rem"},
    }
    tokens = scale_tokens.get(scale, scale_tokens["large"])
    layout_tokens = UI_LAYOUT_PROFILES.get(layout, UI_LAYOUT_PROFILES["wide"])
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
            max-width: {layout_tokens["max_width"]};
            padding-top: 2.4rem;
            padding-bottom: 3rem;
        }
        @media (max-width: 1280px) {
            .block-container {
                max-width: 1180px;
                padding-left: 1.1rem;
                padding-right: 1.1rem;
            }
            .workflow-card {
                min-height: 10rem;
            }
        }
        @media (max-width: 900px) {
            .block-container {
                padding-left: 0.75rem;
                padding-right: 0.75rem;
            }
            div[data-testid="stHorizontalBlock"] {
                gap: 0.75rem;
            }
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
        .workflow-card {
            background: var(--app-panel);
            border: 1px solid var(--app-border);
            border-radius: 12px;
            padding: 1rem 1.1rem;
            min-height: 12rem;
            margin-bottom: 0.9rem;
        }
        .workflow-card strong {
            display: block;
            font-size: 1.1rem;
            margin-bottom: 0.45rem;
        }
        .workflow-card small {
            color: var(--app-muted);
            display: block;
            margin-top: 0.7rem;
            line-height: 1.45;
        }
        .workflow-status {
            background: var(--app-panel-strong);
            border: 1px solid var(--app-border);
            border-radius: 10px;
            padding: 0.85rem 1rem;
        }
        .workflow-status + .workflow-status {
            margin-top: 0.65rem;
        }
        .workflow-status small {
            color: var(--app-muted);
            display: block;
            margin-top: 0.35rem;
        }
        div[data-testid="stDataFrame"] {
            border: 1px solid var(--app-border);
            border-radius: 8px;
            overflow: hidden;
        }
        div[data-testid="stDataFrame"] * {
            font-size: 0.96rem !important;
        }
        </style>
        """
        .replace('{tokens["base"]}', tokens["base"])
        .replace('{tokens["body"]}', tokens["body"])
        .replace('{tokens["caption"]}', tokens["caption"])
        .replace('{tokens["button"]}', tokens["button"])
        .replace('{tokens["h1"]}', tokens["h1"])
        .replace('{layout_tokens["max_width"]}', layout_tokens["max_width"]),
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


def _layout_profile_options() -> tuple[str, ...]:
    """Return layout labels in the order shown in the sidebar."""
    return tuple(profile["label"] for profile in UI_LAYOUT_PROFILES.values())


def _layout_profile_key(label: str) -> str:
    """Resolve a human-readable sidebar label to an internal layout key."""
    for key, profile in UI_LAYOUT_PROFILES.items():
        if profile["label"] == label:
            return key
    return "wide"


def _select_ui_layout() -> str:
    selected = st.sidebar.radio(
        "Режим экрана",
        options=_layout_profile_options(),
        index=1,
        key=UI_LAYOUT_KEY,
        horizontal=False,
        help="Обычный монитор ограничивает ширину рабочих блоков, широкий экран дает больше места под планшеты и таблицы.",
    )
    return _layout_profile_key(selected)


def _layout_profile_summary(layout: str) -> tuple[str, str, str]:
    """Expose the active layout profile for tests and UI status blocks."""
    profile = UI_LAYOUT_PROFILES.get(layout, UI_LAYOUT_PROFILES["wide"])
    return profile["label"], profile["max_width"], profile["description"]


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


def _plotly_figures_to_html(
    figures,
    title: str,
    *,
    subtitle: str = "",
    metadata_rows: tuple[tuple[str, str], ...] = (),
    notes: tuple[str, ...] = (),
    tables: tuple[HtmlReportTable, ...] = (),
) -> bytes:
    return build_plotly_html_report(
        figures,
        HtmlReportMetadata(
            title=title,
            subtitle=subtitle,
            rows=metadata_rows,
            notes=notes,
            tables=tables,
        ),
    )


def _dataframe_to_report_table(title: str, df: pd.DataFrame) -> HtmlReportTable | None:
    if df is None or df.empty:
        return None
    safe_df = df.copy()
    for column in safe_df.columns:
        if pd.api.types.is_float_dtype(safe_df[column]):
            safe_df[column] = safe_df[column].map(lambda value: "" if pd.isna(value) else f"{float(value):g}")
        else:
            safe_df[column] = safe_df[column].map(lambda value: "" if pd.isna(value) else str(value))
    return HtmlReportTable(
        title=title,
        headers=tuple(str(column) for column in safe_df.columns),
        rows=tuple(tuple(row) for row in safe_df.itertuples(index=False, name=None)),
    )


def _dataframe_shape_label(df: pd.DataFrame | None) -> str:
    """Return a short table size label for UI captions and smoke tests."""
    if df is None:
        return "нет данных"
    return f"строк: {len(df)}, колонок: {len(df.columns)}"


def _render_dataframe_panel(
    title: str,
    df: pd.DataFrame,
    *,
    max_preview_rows: int | None = None,
    expanded: bool = False,
    height: int = 360,
    help_text: str = "",
) -> None:
    """Render large tables inside a compact expandable panel.

    The application often works with wide LAS and calculation tables. Keeping
    these tables collapsed by default makes the workflow readable on ordinary
    monitors while still preserving quick access to the raw data.
    """
    with st.expander(title, expanded=expanded):
        st.caption(_dataframe_shape_label(df))
        if help_text:
            st.caption(help_text)
        display_df = df.head(max_preview_rows) if max_preview_rows else df
        st.dataframe(display_df, use_container_width=True, height=height)


def _range_label(value: tuple[float, float] | None, *, unit: str = "") -> str:
    if value is None:
        return "весь доступный интервал"
    suffix = f" {unit}" if unit else ""
    return f"{value[0]:g}-{value[1]:g}{suffix}"


def _group_labels(groups: tuple[str, ...]) -> str:
    labels = [_curve_group_label(group) for group in groups]
    return ", ".join(labels) if labels else "не выбрано"


def _las_correlation_report_rows(
    *,
    project: ProjectRecord,
    selected_wells,
    depth_range: tuple[float, float] | None,
    gis_groups: tuple[str, ...],
    gas_groups: tuple[str, ...],
    gis_x_range: tuple[float, float] | None,
    gas_x_range: tuple[float, float] | None,
    view_mode: str,
    comparison_curve: str,
) -> tuple[tuple[str, str], ...]:
    rows = [
        ("Проект", f"{project.name} ({project.id})"),
        ("Скважины", ", ".join(well.name for well in selected_wells)),
        ("Интервал глубины", _range_label(depth_range, unit="м")),
        ("Представление", view_mode),
        ("ГИС-группы", _group_labels(gis_groups)),
        ("Газовые группы", _group_labels(gas_groups)),
        ("X-scale ГИС", _range_label(gis_x_range)),
        ("X-scale газы", _range_label(gas_x_range)),
        ("Дата выгрузки", datetime.now().strftime("%Y-%m-%d %H:%M")),
    ]
    if view_mode == VIEW_MODE_BY_CURVE and comparison_curve:
        rows.insert(4, ("Кривая сравнения", comparison_curve))
    return tuple(rows)

def _static_export_mime(format_name: str) -> str:
    return {
        "png": "image/png",
        "pdf": "application/pdf",
        "svg": "image/svg+xml",
    }.get(format_name, "application/octet-stream")


def _render_static_export_controls(
    figure,
    *,
    base_file_name: str,
    default_height: int,
    key_prefix: str,
) -> None:
    with st.expander("PNG/PDF/SVG экспорт", expanded=False):
        st.caption(
            "Статический экспорт готовит отдельные файлы графика. "
            "Если движок экспорта не установлен, приложение покажет понятное предупреждение."
        )
        prepare_export = st.checkbox(
            "Подготовить PNG/PDF/SVG файлы",
            value=False,
            key=f"{key_prefix}_prepare_static_export",
        )
        width_col, height_col, scale_col = st.columns(3)
        export_width = width_col.number_input(
            "Ширина, px",
            min_value=600,
            max_value=4000,
            value=1600,
            step=100,
            key=f"{key_prefix}_static_width",
        )
        export_height = height_col.number_input(
            "Высота, px",
            min_value=600,
            max_value=6000,
            value=max(900, int(default_height)),
            step=100,
            key=f"{key_prefix}_static_height",
        )
        export_scale = scale_col.number_input(
            "Scale",
            min_value=0.5,
            max_value=4.0,
            value=2.0,
            step=0.5,
            key=f"{key_prefix}_static_scale",
        )
        if not prepare_export:
            return

        base_name = Path(base_file_name).stem or "las_correlation"
        columns = st.columns(len(SUPPORTED_STATIC_EXPORT_FORMATS))
        for index, format_name in enumerate(SUPPORTED_STATIC_EXPORT_FORMATS):
            try:
                data = export_plotly_static_bytes(
                    figure,
                    StaticExportOptions(
                        format=format_name,
                        width=int(export_width),
                        height=int(export_height),
                        scale=float(export_scale),
                    ),
                )
            except StaticExportUnavailableError as exc:
                st.warning(str(exc))
                break
            columns[index].download_button(
                format_name.upper(),
                data=data,
                file_name=f"{base_name}.{format_name}",
                mime=_static_export_mime(format_name),
                use_container_width=True,
                key=f"{key_prefix}_download_{format_name}",
            )


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


def _format_mapping_diagnostics_table(diagnostics: pd.DataFrame) -> pd.DataFrame:
    if diagnostics.empty:
        return diagnostics
    return diagnostics.rename(
        columns={
            "label": "Поле",
            "source_column": "Колонка файла",
            "status": "Статус",
            "effect": "Влияние",
            "action": "Что проверить",
        }
    )[["Поле", "Колонка файла", "Статус", "Влияние", "Что проверить"]]


def _render_mapping_diagnostics(
    mapping: dict[str, str],
    source_columns,
    messages: tuple[str, ...] | None = None,
) -> None:
    messages = messages if messages is not None else mapping_warning_messages(mapping, source_columns)
    diagnostics = build_mapping_diagnostics(mapping, source_columns)

    with st.expander("Диагностика mapping", expanded=bool(messages)):
        st.dataframe(_format_mapping_diagnostics_table(diagnostics), use_container_width=True)
        if messages:
            for message in messages:
                st.warning(message)
        else:
            st.success("Основные поля сопоставлены.")


def _format_ratio_nan_diagnostics_table(diagnostics: pd.DataFrame) -> pd.DataFrame:
    if diagnostics.empty:
        return diagnostics
    table = diagnostics.rename(
        columns={
            "label": "Коэффициент",
            "nan_count": "NaN строк",
            "row_count": "Всего строк",
            "causes": "Причина",
            "action": "Что проверить",
        }
    )
    return table[["Коэффициент", "NaN строк", "Всего строк", "Причина", "Что проверить"]]


def _render_ratio_nan_diagnostics(
    calculated_df: pd.DataFrame,
    ch_mode: str,
    messages: tuple[str, ...] | None = None,
) -> None:
    messages = messages if messages is not None else ratio_nan_warning_messages(calculated_df, ch_mode=ch_mode)
    diagnostics = build_ratio_nan_diagnostics(calculated_df, ch_mode=ch_mode)

    with st.expander("Диагностика расчетов", expanded=bool(messages)):
        st.dataframe(_format_ratio_nan_diagnostics_table(diagnostics), use_container_width=True)
        if messages:
            st.caption("Если значение NaN есть только в части строк, проверьте эти интервалы в расчетной таблице.")
        else:
            st.success("Wh, Bh, Ch, BAR2 и oil/inverse oil indicator рассчитаны во всех строках.")


def _render_formula_reference() -> None:
    with st.expander("Формулы коэффициентов", expanded=False):
        st.markdown(
            "`Wh = (C2 + C3 + iC4 + nC4 + iC5 + nC5) * 100 / (C1 + C2 + C3 + iC4 + nC4 + iC5 + nC5)`\n\n"
            "`Bh = (C1 + C2) / (C3 + iC4 + nC4 + iC5 + nC5)`\n\n"
            "`Ch = (C3 + iC4 + nC4 + iC5 + nC5) / (iC4 + nC4 + iC5 + nC5)` в режиме `A`\n\n"
            "`BAR2 = C1 / C2`\n\n"
            "`Oil indicator = (C3 + iC4 + nC4 + iC5 + nC5) / C1`\n\n"
            "`Inverse oil indicator = C1 / (C3 + iC4 + nC4 + iC5 + nC5)`\n\n"
            "`Pixler ratios = C1/C2, C1/C3, C1/(iC4+nC4), C1/(iC5+nC5)`\n\n"
            "Методический статус: справочные коэффициенты, требующие проверки по ГИС, литологии, фону газа и буровому контексту. См. `docs/formulas.md`."
        )


def _interval_label(df: pd.DataFrame, index: int) -> str:
    row = df.iloc[index]
    depth = row.get("depth", index)
    if pd.isna(depth):
        depth = index
    interpretation = row.get("interpretation", "нет интерпретации")
    return f"{index}: depth={depth} | {interpretation}"


def _format_interval_value(row: pd.Series, field: str) -> str:
    value = row.get(field)
    if pd.isna(value):
        return "нет данных"
    if isinstance(value, float):
        return f"{value:.4g}"
    return str(value)


def _selected_interval_rule_messages(row: pd.Series, ch_mode: str = "A") -> tuple[str, ...]:
    interpretation = str(row.get("interpretation", "Недостаточно данных"))
    messages = [
        f"Предварительная зона: {interpretation}.",
        (
            "Коэффициенты: "
            f"Wh={_format_interval_value(row, 'wh')}, "
            f"Bh={_format_interval_value(row, 'bh')}, "
            f"Ch={_format_interval_value(row, 'ch')}, "
            f"BAR2={_format_interval_value(row, 'bar2')}."
        ),
    ]

    interval_diagnostics = interval_ratio_diagnostic_messages(row, ch_mode=ch_mode)
    if interval_diagnostics:
        messages.extend(interval_diagnostics)

    if pd.isna(row.get("wh")) or pd.isna(row.get("bh")):
        messages.append("Wh/Bh неполные: проверьте C1-C5, нули в знаменателях и mapping колонок.")
    else:
        messages.append("Wh/Bh рассчитаны: используйте их как инженерную подсказку, а не как утвержденный диагноз.")

    messages.append("Обязательно сверяйте интервал с ГИС, литологией, фоном, СПО, наращиваниями и рециркуляцией.")
    return tuple(messages)


def _render_interval_rule_summary(selected_row: pd.Series, ch_mode: str = "A") -> None:
    st.subheader("Проверяемые подсказки по интервалу")
    for message in _selected_interval_rule_messages(selected_row, ch_mode=ch_mode):
        st.info(message)


def _render_start_guidance() -> None:
    st.markdown("### Справка")
    st.info(
        "Используйте вкладку `Инструкции и документация`, предупреждения workflow "
        "и проверяемые правила расчета."
    )
    st.markdown(
        "1. Начните с LAS-файла или демо `examples/sample_gas_data.las`.\n"
        "2. Если LAS требует подготовки, используйте `LAS-редактор`.\n"
        "3. Для нескольких скважин используйте `LAS-корреляция`.\n"
        "4. При ошибках откройте `docs/troubleshooting.md` или последние строки `logs/app.log`."
    )




def _workflow_status_detail_rows(active_project: ProjectRecord) -> tuple[tuple[str, str, str], ...]:
    """Build status rows with a concrete next action for each workflow stage."""
    rows: list[tuple[str, str, str]] = [
        ("Активный проект", f"{active_project.name} ({active_project.id})", "Проверьте, что выбран нужный проект перед импортом или сохранением."),
    ]

    editor_sheets = st.session_state.get(LAS_EDITOR_SESSION_SHEETS_KEY)
    if editor_sheets:
        rows.append((
            "LAS-редактор",
            st.session_state.get(LAS_EDITOR_SESSION_SUMMARY_KEY, "данные подготовлены"),
            "Можно передать подготовленную таблицу в расчет или сохранить версию в проект.",
        ))
    else:
        rows.append((
            "LAS-редактор",
            "подготовленные данные не загружены в текущую сессию",
            "Откройте LAS-редактор, если файл требует исправления глубины или NULL-значений.",
        ))

    project_sheets = st.session_state.get(PROJECT_SESSION_SHEETS_KEY)
    if project_sheets and st.session_state.get(PROJECT_SESSION_PROJECT_ID_KEY) == active_project.id:
        rows.append((
            "Проектные данные",
            st.session_state.get(PROJECT_SESSION_SUMMARY_KEY, "проектные данные загружены"),
            "Можно продолжить расчет или экспорт выбранных проектных версий.",
        ))
    else:
        rows.append((
            "Проектные данные",
            "не выбраны для текущего workflow",
            "Откройте сохраненный проект или загрузите новые данные во вкладке `Работа с данными`.",
        ))

    interpretation_df = st.session_state.get(INTERPRETATION_SESSION_DATA_KEY)
    if isinstance(interpretation_df, pd.DataFrame) and not interpretation_df.empty:
        source = st.session_state.get(INTERPRETATION_SESSION_SOURCE_KEY, "расчетная таблица")
        rows.append((
            "Интерпретационные графики",
            f"доступны данные: {source}, строк: {len(interpretation_df)}",
            "Можно открыть планшет, маркеры, зоны и interval report.",
        ))
    else:
        rows.append((
            "Интерпретационные графики",
            "сначала выполните расчет во вкладке `Работа с данными`",
            "После расчета данные автоматически появятся в интерпретационных графиках.",
        ))

    return tuple(rows)


def _workflow_status_rows(active_project: ProjectRecord) -> tuple[tuple[str, str], ...]:
    """Build compact status rows for tests and backward-compatible callers."""
    return tuple((label, status) for label, status, _action in _workflow_status_detail_rows(active_project))


def _start_action_titles() -> tuple[str, ...]:
    """Expose start-screen action titles for smoke tests and documentation checks."""
    return tuple(action["title"] for action in START_ACTIONS)


def _render_start_tab(active_project: ProjectRecord) -> None:
    st.subheader("Стартовый экран")
    st.caption(
        "Выберите рабочий сценарий. Streamlit не переключает вкладки программно, "
        "поэтому карточка показывает, какую вкладку открыть дальше."
    )

    st.markdown("### Что делать дальше")
    layout_value = str(st.session_state.get(UI_LAYOUT_KEY, UI_LAYOUT_PROFILES["wide"]["label"]))
    layout_key = layout_value if layout_value in UI_LAYOUT_PROFILES else _layout_profile_key(layout_value)
    column_count = int(UI_LAYOUT_PROFILES.get(layout_key, UI_LAYOUT_PROFILES["wide"])["columns"])
    action_columns = st.columns(column_count)
    for index, action in enumerate(START_ACTIONS):
        with action_columns[index % len(action_columns)]:
            st.markdown(
                "<div class='workflow-card'>"
                f"<strong>{action['title']}</strong>"
                f"<p>{action['description']}</p>"
                f"<small><b>Открыть вкладку:</b> {action['target_tab']}<br>"
                f"<b>Когда использовать:</b> {action['when']}</small>"
                "</div>",
                unsafe_allow_html=True,
            )

    st.markdown("### Текущее состояние")
    for label, value, next_action in _workflow_status_detail_rows(active_project):
        st.markdown(
            f"<div class='workflow-status'><b>{label}</b><br>{value}<small><b>Дальше:</b> {next_action}</small></div>",
            unsafe_allow_html=True,
        )

    layout_label, layout_width, layout_description = _layout_profile_summary(layout_key)
    with st.expander("Проверка экрана и компоновки", expanded=False):
        st.markdown(
            f"**Активный режим:** {layout_label} (`max-width: {layout_width}`).\n\n"
            f"{layout_description}\n\n"
            "Проверьте, что карточки не обрезаются, таблицы открываются без лишней горизонтальной прокрутки, "
            "а планшет и correlation-графики читаются на вашем рабочем мониторе."
        )

    with st.expander("Рекомендуемый порядок работы", expanded=False):
        st.markdown(
            "1. Создайте или выберите проект в левой панели.\n"
            "2. Если LAS проблемный, сначала откройте `LAS-редактор`.\n"
            "3. Для расчета коэффициентов откройте `Работа с данными`.\n"
            "4. Для нескольких скважин используйте `LAS-корреляция`.\n"
            "5. Для печати и обсуждения откройте `Интерпретационные графики`.\n"
            "6. При предупреждениях сверяйте формулы и ограничения во вкладке документации."
        )

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
        "загрузить файл, понять предупреждения и работать без внешних инструкций."
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
            "1. Запустите проект командой `./run_app.ps1` или `python -m streamlit run app/streamlit_app.py`.\n"
            "2. Откройте в браузере `http://localhost:8501`.\n"
            "3. Загрузите LAS (рекомендуется), CSV, XLSX или XLSM.\n"
            "4. Проверьте строку заголовков и mapping.\n"
            "5. Выберите интервал и смотрите расчеты, палетки и графики."
        )

    with verification:
        st.markdown("### Проверка готовности")
        st.code(
            "python -m pytest\n"
            "python scripts/preflight.py",
            language="powershell",
        )
        st.markdown(
            "Preflight проверяет Python, зависимости, ключевые файлы, конфиг палеток "
            "и доступность папки логов."
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

    st.markdown("### Подсказки и диагностика")
    st.markdown(
        "Проект опирается на проверяемые правила, документацию, предупреждения и логи. "
        "Если нужен новый тип подсказки, добавляем явное правило, тест и описание в документацию."
    )
    for index, (title, relative_path) in enumerate(DOCUMENTATION_TAB_DOCS):
        with st.expander(title, expanded=index == 0):
            st.markdown(_read_documentation_markdown(relative_path))


def _render_las_editor(logger, active_project: ProjectRecord) -> None:
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

    st.markdown("### Сохранить подготовленный LAS в проект")
    st.caption(f"Активный проект: {active_project.name} ({active_project.id})")
    if st.button("Сохранить подготовленный LAS в активный проект", use_container_width=True, key="las_editor_save_to_project"):
        if not well_name.strip():
            st.warning("Введите название скважины перед сохранением в проект.")
        else:
            try:
                las_bytes = export_las_bytes(edited_df, well_name=well_name, depth_column=depth_column)
                saved_las = save_project_las_file(
                    las_bytes,
                    root=LAS_CORRELATION_PROJECTS_ROOT,
                    project_id=active_project.id,
                    file_name=f"{well_name.strip()}_{version_label.strip() or 'prepared'}.las",
                    well_name=well_name,
                    version_label=version_label.strip() or "Подготовленный LAS",
                )
            except Exception:
                logger.exception("project_las_prepared_save_failed project_id=%s", safe_log_value(active_project.id))
                st.error("Не удалось сохранить подготовленный LAS в проект. Подробности записаны в logs/app.log.")
            else:
                logger.info(
                    "project_las_prepared_saved project_id=%s las_file_id=%s rows=%d",
                    safe_log_value(active_project.id),
                    safe_log_value(saved_las.id),
                    len(edited_df),
                )
                st.success(f"Подготовленный LAS сохранен в проект: {saved_las.name} / {saved_las.version_label}.")


def _render_workspace(logger, active_project: ProjectRecord) -> None:
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

    _render_project_workspace_loader(active_project, logger)
    _render_project_calculations_panel(active_project, logger)
    _render_project_exports_panel(active_project, logger)

    editor_sheets = st.session_state.get(LAS_EDITOR_SESSION_SHEETS_KEY)
    project_sheets = st.session_state.get(PROJECT_SESSION_SHEETS_KEY)
    if st.session_state.get(PROJECT_SESSION_PROJECT_ID_KEY) != active_project.id:
        project_sheets = None

    source_options = []
    if project_sheets:
        source_options.append("Проект")
        summary = st.session_state.get(PROJECT_SESSION_SUMMARY_KEY, "проектные данные загружены")
        st.info(f"Доступны данные активного проекта: {summary}")
    if editor_sheets:
        source_options.append("LAS-редактор")
        summary = st.session_state.get(LAS_EDITOR_SESSION_SUMMARY_KEY, "данные подготовлены")
        st.info(f"Доступны данные из LAS-редактора: {summary}")
    source_options.append("Файлы")

    selected_source = st.radio(
        "Источник данных",
        options=source_options,
        horizontal=True,
        key="workspace_data_source",
    )

    if selected_source == "Проект" and project_sheets:
        suffix = ".project"
        sheets = project_sheets
        logger.info("project_data_selected project_id=%s sheet_count=%d", safe_log_value(active_project.id), len(sheets))
    elif selected_source == "LAS-редактор" and editor_sheets:
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
            _render_start_guidance()
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

    _render_dataframe_panel(
        "Предпросмотр исходных строк",
        raw_df,
        max_preview_rows=20,
        expanded=True,
        height=320,
        help_text="Первые строки файла до выбора строки заголовков.",
    )

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
    _render_dataframe_panel(
        "Подготовленная таблица после выбора заголовков",
        prepared_df,
        max_preview_rows=20,
        expanded=False,
        height=320,
        help_text="Проверьте, что названия колонок распознаны корректно перед mapping.",
    )

    mapping_result = auto_map_columns(prepared_df.columns)
    logger.info(
        "auto_mapping_completed mapped=%s unmapped_count=%d",
        safe_log_value(",".join(sorted(mapping_result.mapping.keys()))),
        len(mapping_result.unmapped_columns),
    )
    manual_mapping = _build_mapping_controls(prepared_df, mapping_result.mapping)
    mapping_messages = mapping_warning_messages(manual_mapping, prepared_df.columns)
    _render_mapping_diagnostics(manual_mapping, prepared_df.columns, mapping_messages)

    prepared = apply_mapping(prepared_df, manual_mapping)
    logger.info(
        "manual_mapping_applied mapped=%s warning_count=%d",
        safe_log_value(",".join(sorted(manual_mapping.keys()))),
        len(prepared.warnings),
    )
    _render_formula_reference()
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

    nan_messages = ratio_nan_warning_messages(calculated_df, ch_mode=ch_mode)
    warnings = (
        list(mapping_result.warnings)
        + list(prepared.warnings)
        + list(calculation.warnings)
        + list(mapping_messages)
        + list(nan_messages)
    )
    warnings = list(dict.fromkeys(warnings))

    with st.expander("Предупреждения и проверки", expanded=bool(warnings)):
        if warnings:
            for warning in warnings:
                st.warning(warning)
        else:
            st.success("Критичных предупреждений нет.")
        st.info(CH_WARNING)
    _render_ratio_nan_diagnostics(calculated_df, ch_mode, nan_messages)

    if calculated_df.empty:
        logger.warning("calculated_dataframe_empty")
        st.error("Нет расчетных данных для отображения.")
        return

    st.subheader("Сводка классификации")
    st.dataframe(summarize_interpretation(calculated_df), use_container_width=True, height=220)

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
    _render_interval_rule_summary(selected_row, ch_mode=ch_mode)

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
    _render_dataframe_panel(
        "Полная расчетная таблица",
        calculated_df,
        expanded=False,
        height=460,
        help_text="Полная таблица остается доступной, но не перегружает основной экран.",
    )
    st.download_button(
        "Экспорт CSV",
        data=export_csv_bytes(calculated_df),
        file_name="gas_ratio_calculations.csv",
        mime="text/csv",
    )
    _render_project_calculation_saver(
        project=active_project,
        calculated_df=calculated_df,
        selected_source=selected_source,
        sheet_name=str(sheet_name),
        mapping=manual_mapping,
        ch_mode=ch_mode,
        warnings=tuple(warnings),
        header_row=int(header_row),
        logger=logger,
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


def _filter_interpretation_tracks(tracks: tuple[str, ...]) -> tuple[str, ...]:
    selected = tuple(track for track in tracks if track in INTERPRETATION_TRACK_OPTIONS)
    return selected or INTERPRETATION_TRACK_OPTIONS


def _set_interpretation_x_range_state(key_prefix: str, x_range: tuple[float, float] | None) -> None:
    st.session_state[f"{key_prefix}_x_auto"] = x_range is None
    if x_range is not None:
        st.session_state[f"{key_prefix}_x_min"] = float(x_range[0])
        st.session_state[f"{key_prefix}_x_max"] = float(x_range[1])


def _safe_widget_key(value: object) -> str:
    token = "".join(char if char.isalnum() else "_" for char in str(value)).strip("_")
    return token[:80] or "value"


def _tablet_x_range_key(column: str) -> str:
    return f"interpretation_tablet_{_safe_widget_key(column)}"


def _set_tablet_x_range_state(column: str, x_range: tuple[float, float] | None) -> None:
    key_prefix = _tablet_x_range_key(column)
    st.session_state[f"{key_prefix}_x_auto"] = x_range is None
    if x_range is not None:
        st.session_state[f"{key_prefix}_x_min"] = float(x_range[0])
        st.session_state[f"{key_prefix}_x_max"] = float(x_range[1])


def _valid_tablet_columns(df: pd.DataFrame, columns: tuple[str, ...]) -> tuple[str, ...]:
    available = set(numeric_tablet_columns(df))
    return tuple(column for column in columns if column in available)


def _tablet_columns_default(df: pd.DataFrame, saved_columns: tuple[str, ...] = ()) -> tuple[str, ...]:
    saved = _valid_tablet_columns(df, saved_columns)
    if saved:
        return saved
    return default_tablet_columns(df)


def _select_tablet_x_ranges(df: pd.DataFrame, columns: tuple[str, ...]) -> dict[str, tuple[float, float]]:
    x_ranges: dict[str, tuple[float, float]] = {}
    if not columns:
        return x_ranges

    with st.expander("Ручной масштаб X по параметрам планшета", expanded=False):
        for column in columns:
            values = pd.to_numeric(df[column], errors="coerce").dropna() if column in df.columns else pd.Series(dtype=float)
            if values.empty:
                default_min, default_max = 0.0, 100.0
            else:
                default_min, default_max = float(values.min()), float(values.max())
                if default_min == default_max:
                    default_max = default_min + 1.0

            key_prefix = _tablet_x_range_key(column)
            auto_scale = st.checkbox(f"Автомасштаб X: {column}", value=True, key=f"{key_prefix}_x_auto")
            if auto_scale:
                continue

            min_col, max_col = st.columns(2)
            min_value = min_col.number_input(
                f"X min: {column}",
                value=default_min,
                step=1.0,
                key=f"{key_prefix}_x_min",
            )
            max_value = max_col.number_input(
                f"X max: {column}",
                value=default_max,
                step=1.0,
                key=f"{key_prefix}_x_max",
            )
            if min_value == max_value:
                st.warning(f"Для {column} X min и X max совпадают. Используется автомасштаб.")
                continue
            x_ranges[column] = (min(float(min_value), float(max_value)), max(float(min_value), float(max_value)))
    return x_ranges


def _render_tablet_marker_controls(depth_range: tuple[float, float] | None, df: pd.DataFrame) -> tuple[InterpretationMarker, ...]:
    depth = _depth_values_for_graphs(df).dropna()
    if depth_range is not None:
        default_top, default_bottom = depth_range
    elif not depth.empty:
        default_top, default_bottom = float(depth.min()), float(depth.max())
    else:
        default_top, default_bottom = 0.0, float(max(len(df) - 1, 0))

    with st.expander("Маркеры интерпретации планшета", expanded=False):
        marker_count = st.number_input(
            "Количество маркеров",
            min_value=0,
            max_value=8,
            value=0,
            step=1,
            key="interpretation_tablet_marker_count",
        )
        markers: list[InterpretationMarker] = []
        span = max(default_bottom - default_top, 0.0)
        for index in range(int(marker_count)):
            label_default = chr(ord("a") + index)
            depth_default = default_top + (span * (index + 1) / (int(marker_count) + 1)) if marker_count else default_top
            label_col, depth_col, note_col = st.columns((1, 1, 3))
            label = label_col.text_input(
                f"Метка {index + 1}",
                value=label_default,
                key=f"interpretation_tablet_marker_{index}_label",
            )
            marker_depth = depth_col.number_input(
                f"Глубина {index + 1}",
                value=float(depth_default),
                step=0.1,
                key=f"interpretation_tablet_marker_{index}_depth",
            )
            note = note_col.text_input(
                f"Комментарий {index + 1}",
                value="",
                key=f"interpretation_tablet_marker_{index}_note",
            )
            markers.append(InterpretationMarker(label=(label.strip() or label_default), depth=float(marker_depth), note=note.strip()))
    return tuple(markers)



def _render_tablet_zone_controls(depth_range: tuple[float, float] | None, df: pd.DataFrame) -> tuple[InterpretationZone, ...]:
    depth = _depth_values_for_graphs(df).dropna()
    if depth_range is not None:
        default_top, default_bottom = depth_range
    elif not depth.empty:
        default_top, default_bottom = float(depth.min()), float(depth.max())
    else:
        default_top, default_bottom = 0.0, float(max(len(df) - 1, 0))

    with st.expander("Интерпретационные зоны планшета", expanded=False):
        zone_count = st.number_input(
            "Количество зон",
            min_value=0,
            max_value=12,
            value=0,
            step=1,
            key="interpretation_tablet_zone_count",
        )
        zones: list[InterpretationZone] = []
        span = max(default_bottom - default_top, 0.0)
        for index in range(int(zone_count)):
            zone_top_default = default_top + (span * index / max(int(zone_count), 1))
            zone_bottom_default = default_top + (span * (index + 1) / max(int(zone_count), 1))
            label_col, top_col, bottom_col, color_col = st.columns((1.4, 1, 1, 1))
            label = label_col.text_input(
                f"Зона {index + 1}",
                value=f"Zone {index + 1}",
                key=f"interpretation_tablet_zone_{index}_label",
            )
            top_depth = top_col.number_input(
                f"Верх зоны {index + 1}",
                value=float(zone_top_default),
                step=0.1,
                key=f"interpretation_tablet_zone_{index}_top",
            )
            bottom_depth = bottom_col.number_input(
                f"Низ зоны {index + 1}",
                value=float(zone_bottom_default),
                step=0.1,
                key=f"interpretation_tablet_zone_{index}_bottom",
            )
            color = color_col.color_picker(
                f"Цвет зоны {index + 1}",
                value="#ffd966",
                key=f"interpretation_tablet_zone_{index}_color",
            )
            note = st.text_input(
                f"Комментарий зоны {index + 1}",
                value="",
                key=f"interpretation_tablet_zone_{index}_note",
            )
            if float(top_depth) == float(bottom_depth):
                st.warning(f"Зона {index + 1}: верх и низ совпадают, зона не будет построена.")
                continue
            zones.append(
                InterpretationZone(
                    label=label.strip() or f"Zone {index + 1}",
                    top_depth=float(top_depth),
                    bottom_depth=float(bottom_depth),
                    color=str(color),
                    note=note.strip(),
                )
            )
    return tuple(zones)

def _render_tablet_controls(
    filtered_df: pd.DataFrame,
    depth_range: tuple[float, float] | None,
) -> tuple[tuple[str, ...], dict[str, tuple[float, float]], dict[str, str], dict[str, str], tuple[InterpretationMarker, ...], tuple[InterpretationZone, ...], bool]:
    available_columns = numeric_tablet_columns(filtered_df)
    if not available_columns:
        st.warning("В выбранном интервале нет числовых параметров для планшета.")
        return (), {}, {}, {}, (), (), False

    current_state = tuple(st.session_state.get("interpretation_tablet_columns", ()))
    valid_state = _valid_tablet_columns(filtered_df, current_state)
    if current_state and valid_state != current_state:
        st.session_state["interpretation_tablet_columns"] = list(valid_state)

    literature_columns = mud_gas_literature_tablet_columns(filtered_df)
    if literature_columns:
        preset_col, marker_col = st.columns(2)
        if preset_col.button(
            "Применить preset Mud gas analysis",
            help="Выбирает доступные GR/total gas/C1-C5/Wh-Bh-Ch/Pixler/ГИС-треки в порядке из литературного обзора.",
            use_container_width=True,
            key="interpretation_tablet_apply_mud_gas_preset",
        ):
            st.session_state["interpretation_tablet_columns"] = list(literature_columns)
            st.rerun()
        if marker_col.button(
            "Добавить mud-gas маркеры",
            help="Ставит безопасные справочные маркеры по total-gas/Wh/Pixler/oil-indicator экстремумам. Это не автоматическая классификация.",
            use_container_width=True,
            key="interpretation_tablet_apply_mud_gas_markers",
        ):
            suggested_markers = mud_gas_literature_markers(filtered_df)
            st.session_state["interpretation_tablet_marker_count"] = len(suggested_markers)
            for index, marker in enumerate(suggested_markers):
                st.session_state[f"interpretation_tablet_marker_{index}_label"] = marker.label
                st.session_state[f"interpretation_tablet_marker_{index}_depth"] = float(marker.depth)
                st.session_state[f"interpretation_tablet_marker_{index}_note"] = marker.note
            st.rerun()
        st.caption(
            "Mud gas preset использует только найденные в данных колонки; отсутствующие C-компоненты, ratios или ГИС-кривые не подставляются искусственно."
        )

    selected_columns = tuple(
        st.multiselect(
            "Параметры планшета",
            options=available_columns,
            default=list(_tablet_columns_default(filtered_df, valid_state)),
            key="interpretation_tablet_columns",
            help="Можно выбрать любые числовые LAS/Excel/CSV/расчетные колонки. Глубина всегда идет вниз по возрастанию.",
        )
    )
    if not selected_columns:
        st.warning("Выберите хотя бы один числовой параметр для планшета.")
        return (), {}, {}, {}, (), (), False

    tablet_fill = st.checkbox(
        "Заливка всех кривых до нуля (legacy)",
        value=False,
        key="interpretation_tablet_fill",
        help="Совместимый общий режим. Для точной настройки используйте индивидуальные режимы заливки ниже.",
    )
    tablet_x_ranges = _select_tablet_x_ranges(filtered_df, selected_columns)
    tablet_colors: dict[str, str] = {}
    tablet_fill_modes: dict[str, str] = {}
    fill_mode_labels = {
        "none": "Линия без заливки",
        "to_zero": "Заливка до 0",
        "to_left": "Заливка до левой границы шкалы",
        "to_right": "Заливка до правой границы шкалы",
    }
    with st.expander("Цвета и заливка треков планшета", expanded=False):
        for index, column in enumerate(selected_columns):
            color_col, fill_col = st.columns((1, 1.4))
            default_color = DEFAULT_TABLET_COLORS[index % len(DEFAULT_TABLET_COLORS)]
            tablet_colors[column] = color_col.color_picker(
                f"Цвет: {column}",
                value=default_color,
                key=f"interpretation_tablet_{_safe_widget_key(column)}_color",
            )
            default_mode = st.session_state.get(f"interpretation_tablet_{_safe_widget_key(column)}_fill_mode")
            if default_mode not in TABLET_FILL_MODES:
                default_mode = "to_zero" if tablet_fill else "none"
            tablet_fill_modes[column] = fill_col.selectbox(
                f"Заливка: {column}",
                options=("none", "to_zero", "to_left", "to_right"),
                index=("none", "to_zero", "to_left", "to_right").index(str(default_mode)),
                format_func=lambda mode: fill_mode_labels.get(str(mode), str(mode)),
                key=f"interpretation_tablet_{_safe_widget_key(column)}_fill_mode",
            )
    markers = _render_tablet_marker_controls(depth_range, filtered_df)
    zones = _render_tablet_zone_controls(depth_range, filtered_df)
    return selected_columns, tablet_x_ranges, tablet_colors, tablet_fill_modes, markers, zones, bool(tablet_fill)


def _apply_interpretation_graph_settings_to_session(settings: InterpretationGraphSettings) -> None:
    st.session_state["interpretation_tracks"] = list(_filter_interpretation_tracks(settings.selected_tracks))
    st.session_state["interpretation_chart_height"] = int(settings.height)
    if settings.depth_range is None:
        st.session_state["interpretation_depth_range_mode"] = "Весь интервал"
    else:
        st.session_state["interpretation_depth_range_mode"] = "Ручной интервал"
        st.session_state["interpretation_top_depth"] = float(settings.depth_range[0])
        st.session_state["interpretation_bottom_depth"] = float(settings.depth_range[1])

    _set_interpretation_x_range_state("interpretation_gas", settings.gas_x_range)
    _set_interpretation_x_range_state("interpretation_ratio", settings.ratio_x_range)
    _set_interpretation_x_range_state("interpretation_pixler", settings.pixler_x_range)
    st.session_state["interpretation_tablet_columns"] = list(settings.tablet_tracks)
    st.session_state["interpretation_tablet_fill"] = bool(settings.tablet_fill)
    for column, color in settings.tablet_colors.items():
        st.session_state[f"interpretation_tablet_{_safe_widget_key(column)}_color"] = str(color)
    for column, mode in settings.tablet_fill_modes.items():
        st.session_state[f"interpretation_tablet_{_safe_widget_key(column)}_fill_mode"] = str(mode)
    for column, x_range in settings.tablet_x_ranges.items():
        _set_tablet_x_range_state(column, x_range)
    st.session_state["interpretation_tablet_marker_count"] = len(settings.tablet_markers)
    for index, marker in enumerate(settings.tablet_markers):
        st.session_state[f"interpretation_tablet_marker_{index}_label"] = str(marker.get("label") or chr(ord("a") + index))
        st.session_state[f"interpretation_tablet_marker_{index}_depth"] = float(marker.get("depth", 0.0))
        st.session_state[f"interpretation_tablet_marker_{index}_note"] = str(marker.get("note") or "")
    st.session_state["interpretation_tablet_zone_count"] = len(settings.tablet_zones)
    for index, zone in enumerate(settings.tablet_zones):
        st.session_state[f"interpretation_tablet_zone_{index}_label"] = str(zone.get("label") or f"Zone {index + 1}")
        st.session_state[f"interpretation_tablet_zone_{index}_top"] = float(zone.get("top_depth", 0.0))
        st.session_state[f"interpretation_tablet_zone_{index}_bottom"] = float(zone.get("bottom_depth", 0.0))
        st.session_state[f"interpretation_tablet_zone_{index}_color"] = str(zone.get("color") or "#ffd966")
        st.session_state[f"interpretation_tablet_zone_{index}_note"] = str(zone.get("note") or "")


def _interpretation_graph_settings_summary(settings: InterpretationGraphSettings) -> tuple[str, ...]:
    depth_label = "весь интервал" if settings.depth_range is None else _range_label(settings.depth_range, unit="м")
    tablet_label = ", ".join(settings.tablet_tracks) if settings.tablet_tracks else "не настроен"
    return (
        f"Треки: {', '.join(settings.selected_tracks)}",
        f"Диапазон глубины: {depth_label}",
        f"Высота: {settings.height}px",
        f"X C1-C5: {_range_label(settings.gas_x_range)}",
        f"X Wh/Bh/Ch: {_range_label(settings.ratio_x_range)}",
        f"X Pixler: {_range_label(settings.pixler_x_range)}",
        f"Планшет: {tablet_label}",
        f"Маркеры планшета: {len(settings.tablet_markers)}",
        f"Зоны планшета: {len(settings.tablet_zones)}",
    )


def _load_project_interpretation_graph_settings(project: ProjectRecord, logger) -> InterpretationGraphSettings | None:
    try:
        return load_project_interpretation_graph_settings(
            root=LAS_CORRELATION_PROJECTS_ROOT,
            project_id=project.id,
        )
    except Exception:
        logger.exception("interpretation_graph_settings_load_failed project_id=%s", safe_log_value(project.id))
        st.warning("Не удалось прочитать настройки интерпретационных графиков проекта.")
        return None


def _render_interpretation_graph_settings_loader(project: ProjectRecord, logger) -> None:
    project_settings = _load_project_interpretation_graph_settings(project, logger)
    if project_settings is None:
        return

    with st.expander("Сохраненные настройки графиков проекта", expanded=False):
        for line in _interpretation_graph_settings_summary(project_settings):
            st.caption(line)
        if st.button("Загрузить настройки графиков проекта", use_container_width=True, key=f"load_interpretation_graph_settings_{project.id}"):
            _apply_interpretation_graph_settings_to_session(project_settings)
            st.rerun()


def _render_interpretation_graph_settings_saver(
    project: ProjectRecord,
    settings: InterpretationGraphSettings,
    logger,
) -> None:
    with st.expander("Текущие настройки графиков", expanded=False):
        for line in _interpretation_graph_settings_summary(settings):
            st.caption(line)
        if st.button("Сохранить настройки графиков в проект", use_container_width=True, key=f"save_interpretation_graph_settings_{project.id}"):
            try:
                save_project_interpretation_graph_settings(
                    settings,
                    root=LAS_CORRELATION_PROJECTS_ROOT,
                    project_id=project.id,
                )
            except Exception:
                logger.exception("interpretation_graph_settings_save_failed project_id=%s", safe_log_value(project.id))
                st.error("Не удалось сохранить настройки графиков в проект. Подробности записаны в logs/app.log.")
            else:
                st.success("Настройки интерпретационных графиков сохранены в проект.")


def _render_interpretation_graphs_tab(logger, active_project: ProjectRecord) -> None:
    st.subheader("Интерпретационные графики")
    calculated_df = st.session_state.get(INTERPRETATION_SESSION_DATA_KEY)
    if calculated_df is None or calculated_df.empty:
        st.info("Сначала выполните расчет во вкладке `Работа с данными`. После этого здесь появятся графики и таблица интерпретации.")
        return

    source_label = st.session_state.get(INTERPRETATION_SESSION_SOURCE_KEY, "текущий расчет")
    st.caption(f"Источник данных: {source_label}")
    st.caption(f"Активный проект: {active_project.name} ({active_project.id})")
    _render_interpretation_graph_settings_loader(active_project, logger)

    depth = _depth_values_for_graphs(calculated_df)
    valid_depth = depth.dropna()
    if valid_depth.empty:
        st.warning("В расчетной таблице нет числовой глубины. Графики будут построены по техническому индексу.")
        filtered_df = calculated_df.copy()
        depth_range = None
        saved_depth_range = None
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
        saved_depth_range = depth_range if mode == "Ручной интервал" else None
        filtered_df = _filter_by_depth_range(calculated_df, depth_range[0], depth_range[1])

    st.metric("Строк в выбранном интервале", len(filtered_df))
    if filtered_df.empty:
        st.error("В выбранном диапазоне глубин нет строк.")
        return

    height = st.slider("Высота графиков", min_value=420, max_value=1100, value=650, step=10, key="interpretation_chart_height")
    selected_tracks = st.multiselect(
        "Графики",
        options=INTERPRETATION_TRACK_OPTIONS,
        default=INTERPRETATION_TRACK_OPTIONS,
        key="interpretation_tracks",
    )

    with st.expander("Ручной масштаб X", expanded=False):
        gas_x_range = _select_x_range("C1-C5", "interpretation_gas")
        ratio_x_range = _select_x_range("Wh/Bh/Ch", "interpretation_ratio")
        pixler_x_range = _select_x_range("Pixler ratios", "interpretation_pixler")

    tablet_columns: tuple[str, ...] = ()
    tablet_x_ranges: dict[str, tuple[float, float]] = {}
    tablet_colors: dict[str, str] = {}
    tablet_fill_modes: dict[str, str] = {}
    tablet_markers: tuple[InterpretationMarker, ...] = ()
    tablet_zones: tuple[InterpretationZone, ...] = ()
    tablet_fill = False
    if TABLET_TRACK_OPTION in selected_tracks:
        st.subheader("Планшетные параметры")
        tablet_columns, tablet_x_ranges, tablet_colors, tablet_fill_modes, tablet_markers, tablet_zones, tablet_fill = _render_tablet_controls(filtered_df, depth_range)

    current_settings = InterpretationGraphSettings(
        selected_tracks=tuple(selected_tracks),
        height=int(height),
        depth_range=saved_depth_range,
        gas_x_range=gas_x_range,
        ratio_x_range=ratio_x_range,
        pixler_x_range=pixler_x_range,
        tablet_tracks=tablet_columns,
        tablet_x_ranges=tablet_x_ranges,
        tablet_colors=tablet_colors,
        tablet_fill_modes=tablet_fill_modes,
        tablet_markers=tuple({"label": marker.label, "depth": marker.depth, "note": marker.note} for marker in tablet_markers),
        tablet_zones=tuple(
            {
                "label": zone.label,
                "top_depth": min(zone.top_depth, zone.bottom_depth),
                "bottom_depth": max(zone.top_depth, zone.bottom_depth),
                "color": zone.color,
                "note": zone.note,
            }
            for zone in tablet_zones
        ),
        tablet_fill=tablet_fill,
    )
    _render_interpretation_graph_settings_saver(active_project, current_settings, logger)

    figures = []
    tablet_figure = None
    if "Интерпретация" in selected_tracks:
        figures.append(build_depth_interpretation_track(filtered_df, depth_range=depth_range, height=height))
    if "C1-C5" in selected_tracks:
        figures.append(build_depth_gas_tracks(filtered_df, depth_range=depth_range, x_range=gas_x_range, height=height))
    if "Wh/Bh/Ch" in selected_tracks:
        figures.append(build_depth_ratio_tracks(filtered_df, depth_range=depth_range, x_range=ratio_x_range, height=height))
    if "Pixler ratios" in selected_tracks:
        figures.append(build_depth_pixler_tracks(filtered_df, depth_range=depth_range, x_range=pixler_x_range, height=height))
    if TABLET_TRACK_OPTION in selected_tracks and tablet_columns:
        tablet_tracks = normalize_track_configs(
            tablet_columns,
            x_ranges=tablet_x_ranges,
            units=tablet_units_from_dataframe(filtered_df),
            colors=tablet_colors,
            fill=tablet_fill,
            fill_modes=tablet_fill_modes,
        )
        tablet_figure = build_well_log_tablet(
            filtered_df,
            tablet_tracks,
            depth_range=depth_range,
            markers=tablet_markers,
            zones=tablet_zones,
            height=max(int(height), 760),
        )
        figures.append(tablet_figure)

    if not figures:
        st.warning("Выберите хотя бы один график.")
    for figure in figures:
        st.plotly_chart(figure, use_container_width=True)
    if tablet_figure is not None:
        _render_static_export_controls(
            tablet_figure,
            base_file_name="gas_ratio_well_log_tablet",
            default_height=max(int(height), 760),
            key_prefix="interpretation_tablet",
        )

    if TABLET_TRACK_OPTION in selected_tracks and tablet_markers and tablet_columns:
        marker_table = build_marker_interpretation_table(filtered_df, tablet_markers, columns=tablet_columns)
        if not marker_table.empty:
            st.subheader("Таблица маркеров планшета")
            st.dataframe(marker_table, use_container_width=True)

    if TABLET_TRACK_OPTION in selected_tracks and tablet_zones:
        zone_table = build_interpretation_zone_table(tablet_zones)
        if not zone_table.empty:
            st.subheader("Таблица интерпретационных зон планшета")
            st.dataframe(zone_table, use_container_width=True)

    if figures:
        report_title = f"Gas Ratio Interpreter - {source_label}"
        report_tables: list[HtmlReportTable] = []
        if TABLET_TRACK_OPTION in selected_tracks and tablet_markers and tablet_columns:
            marker_table = build_marker_interpretation_table(filtered_df, tablet_markers, columns=tablet_columns)
            marker_report_table = _dataframe_to_report_table("Таблица маркеров планшета", marker_table)
            if marker_report_table is not None:
                report_tables.append(marker_report_table)
        if TABLET_TRACK_OPTION in selected_tracks and tablet_zones:
            zone_report_table = _dataframe_to_report_table("Таблица интерпретационных зон планшета", build_interpretation_zone_table(tablet_zones))
            if zone_report_table is not None:
                report_tables.append(zone_report_table)
        html_bytes = _plotly_figures_to_html(
            figures,
            report_title,
            subtitle="Интерпретационные графики и планшет выбранного интервала",
            metadata_rows=(
                ("Источник данных", str(source_label)),
                ("Активный проект", f"{active_project.name} ({active_project.id})"),
                ("Диапазон глубины", _range_label(depth_range, unit="м")),
                ("Строк в интервале", str(len(filtered_df))),
                ("Планшетные параметры", ", ".join(tablet_columns) if tablet_columns else "не выбраны"),
            ),
            notes=(INTERPRETATION_NOTE,),
            tables=tuple(report_tables),
        )
        interval_report_bytes = build_interval_print_report(
            figures,
            title=f"Gas Ratio Interval Report - {source_label}",
            source_label=str(source_label),
            project_label=f"{active_project.name} ({active_project.id})",
            depth_label=_range_label(depth_range, unit="м"),
            interval_df=filtered_df,
            tablet_columns=tablet_columns,
            extra_tables=tuple(report_tables),
            notes=(INTERPRETATION_NOTE,),
        )
        html_download_col, interval_report_col, html_save_col = st.columns(3)
        html_download_col.download_button(
            "HTML графиков",
            data=html_bytes,
            file_name="gas_ratio_depth_graphs.html",
            mime="text/html",
            use_container_width=True,
        )
        interval_report_col.download_button(
            "Печатный отчет интервала",
            data=interval_report_bytes,
            file_name="gas_ratio_interval_report.html",
            mime="text/html",
            use_container_width=True,
        )
        if html_save_col.button("Сохранить отчет в проект", use_container_width=True, key=f"save_interpretation_html_export_{active_project.id}"):
            _save_project_export_with_feedback(
                project=active_project,
                data=interval_report_bytes,
                label=f"Печатный отчет интервала: {source_label}",
                file_name="gas_ratio_interval_report.html",
                mime_type="text/html",
                kind="interpretation_interval_report_html",
                source=str(source_label),
                metadata={
                    "rows": len(filtered_df),
                    "figure_count": len(figures),
                    "settings": project_graph_settings.settings_to_dict(current_settings),
                },
                logger=logger,
            )

    st.subheader("Сводка интерпретации")
    st.dataframe(summarize_interpretation(filtered_df), use_container_width=True)
    st.subheader("Таблица выбранного интервала")
    st.dataframe(filtered_df, use_container_width=True)
    interval_csv_bytes = export_csv_bytes(filtered_df)
    interval_download_col, interval_save_col = st.columns(2)
    interval_download_col.download_button(
        "Экспорт выбранного интервала CSV",
        data=interval_csv_bytes,
        file_name="gas_ratio_selected_interval.csv",
        mime="text/csv",
        use_container_width=True,
    )
    if interval_save_col.button("Сохранить CSV в проект", use_container_width=True, key=f"save_interpretation_interval_csv_{active_project.id}"):
        _save_project_export_with_feedback(
            project=active_project,
            data=interval_csv_bytes,
            label=f"Интервал интерпретации: {source_label}",
            file_name="gas_ratio_selected_interval.csv",
            mime_type="text/csv",
            kind="interpretation_interval_csv",
            source=str(source_label),
            metadata={
                "rows": len(filtered_df),
                "settings": project_graph_settings.settings_to_dict(current_settings),
            },
            logger=logger,
        )
    logger.info("interpretation_graphs_rendered rows=%d figure_count=%d", len(filtered_df), len(figures))


def _curve_group_label(group: str) -> str:
    return CURVE_GROUP_LABELS.get(group, group)


def _curve_group_option_label(group: str) -> str:
    return f"{_curve_group_label(group)} ({group})"


def _format_curve_group_rows(well) -> pd.DataFrame:
    rows = pd.DataFrame(curve_group_rows(well))
    if rows.empty:
        return rows
    return rows.rename(
        columns={
            "curve": "Кривая",
            "group": "Группа",
            "group_label": "Название группы",
            "is_depth": "Depth curve",
        }
    )[["Кривая", "Группа", "Название группы", "Depth curve"]]


def _render_curve_group_override_controls(wells):
    selected_wells = list(wells)
    if not selected_wells:
        return tuple(), {}

    use_manual_groups = st.checkbox(
        "Ручное назначение групп кривых",
        value=False,
        key="las_correlation_manual_curve_groups",
    )
    if not use_manual_groups:
        return tuple(selected_wells), {}

    group_options = tuple(CURVE_GROUP_LABELS.keys())
    overridden_wells = []
    all_overrides: dict[str, dict[str, str]] = {}
    with st.expander("Ручное назначение кривых", expanded=True):
        st.caption("Используйте этот блок, если LAS содержит нестандартные мнемоники или авто-группа выбрана неверно.")
        for well in selected_wells:
            st.markdown(f"#### {well.name}")
            rows = curve_group_rows(well)
            st.dataframe(_format_curve_group_rows(well), use_container_width=True)

            current_group_by_curve = {row["curve"]: row["group"] for row in rows}
            overrides: dict[str, str] = {}
            columns = st.columns(3)
            for index, curve in enumerate(str(column) for column in well.data.columns):
                current_group = current_group_by_curve.get(curve, "other")
                default_index = group_options.index(current_group) if current_group in group_options else group_options.index("other")
                selected_group = columns[index % 3].selectbox(
                    curve,
                    options=group_options,
                    index=default_index,
                    format_func=_curve_group_option_label,
                    key=f"las_correlation_group_override_{well.name}_{curve}",
                )
                if selected_group != current_group:
                    overrides[curve] = selected_group

            if overrides:
                all_overrides[well.name] = overrides
            overridden_wells.append(apply_curve_group_overrides(well, overrides))

    return tuple(overridden_wells), all_overrides


def _filter_group_selection(groups, allowed_groups: tuple[str, ...], fallback: tuple[str, ...]) -> tuple[str, ...]:
    selected = tuple(group for group in groups if group in allowed_groups)
    return selected or tuple(group for group in fallback if group in allowed_groups)


def _set_las_correlation_x_range_state(key_prefix: str, x_range: tuple[float, float] | None) -> None:
    st.session_state[f"{key_prefix}_x_auto"] = x_range is None
    if x_range is not None:
        st.session_state[f"{key_prefix}_x_min"] = float(x_range[0])
        st.session_state[f"{key_prefix}_x_max"] = float(x_range[1])


def _curve_belongs_to_groups(wells, curve_name: str, groups: tuple[str, ...]) -> bool:
    return any(curve_name in well.curve_groups.get(group, ()) for well in wells for group in groups)


def _comparison_x_range_for_curve(
    wells,
    curve_name: str,
    gis_groups: tuple[str, ...],
    gas_groups: tuple[str, ...],
    gis_x_range: tuple[float, float] | None,
    gas_x_range: tuple[float, float] | None,
) -> tuple[float, float] | None:
    if _curve_belongs_to_groups(wells, curve_name, gis_groups):
        return gis_x_range
    if _curve_belongs_to_groups(wells, curve_name, gas_groups):
        return gas_x_range
    return None


def _apply_las_correlation_settings_to_session(settings: LasCorrelationSettings, wells, group_options: tuple[str, ...]) -> None:
    available_well_names = tuple(well.name for well in wells)
    selected_wells = tuple(name for name in settings.selected_well_names if name in available_well_names) or available_well_names
    st.session_state["las_correlation_selected_wells"] = list(selected_wells)
    st.session_state["las_correlation_gis_groups"] = list(_filter_group_selection(settings.gis_groups, group_options, DEFAULT_GIS_GROUPS))
    st.session_state["las_correlation_gas_groups"] = list(_filter_group_selection(settings.gas_groups, group_options, DEFAULT_GAS_GROUPS))
    st.session_state["las_correlation_height_per_well"] = int(settings.height_per_well)
    st.session_state["las_correlation_view_mode"] = (
        settings.view_mode if settings.view_mode in SUPPORTED_VIEW_MODES else VIEW_MODE_BY_WELL
    )
    if settings.comparison_curve:
        st.session_state["las_correlation_comparison_curve"] = settings.comparison_curve

    if settings.depth_range is None:
        st.session_state["las_correlation_depth_range_mode"] = "Общий весь интервал"
    else:
        st.session_state["las_correlation_depth_range_mode"] = "Ручной интервал"
        st.session_state["las_correlation_top_depth"] = float(settings.depth_range[0])
        st.session_state["las_correlation_bottom_depth"] = float(settings.depth_range[1])

    _set_las_correlation_x_range_state("las_correlation_gis", settings.gis_x_range)
    _set_las_correlation_x_range_state("las_correlation_gas", settings.gas_x_range)

    use_manual_groups = bool(settings.curve_group_overrides)
    st.session_state["las_correlation_manual_curve_groups"] = use_manual_groups
    if not use_manual_groups:
        return

    for well in wells:
        overrides = settings.curve_group_overrides.get(well.name, {})
        for row in curve_group_rows(well):
            curve = row["curve"]
            group = overrides.get(curve, row["group"])
            if group not in CURVE_GROUP_LABELS:
                group = "other"
            st.session_state[f"las_correlation_group_override_{well.name}_{curve}"] = group


class _NamedLasBytesIO(BytesIO):
    def __init__(self, data: bytes, name: str) -> None:
        super().__init__(data)
        self.name = name


def _project_settings_session_key(project_id: str) -> str:
    return f"{LAS_CORRELATION_SETTINGS_KEY}:{project_id}"


def _project_option_label(project: ProjectRecord) -> str:
    return f"{project.name} ({project.id})"


def _load_project_records_for_ui(logger) -> tuple[ProjectRecord, ...]:
    try:
        default_project = ensure_default_project(LAS_CORRELATION_PROJECTS_ROOT)
        projects = list_projects(LAS_CORRELATION_PROJECTS_ROOT)
        return projects or (default_project,)
    except Exception:
        logger.exception("project_records_load_failed")
        st.warning("Не удалось загрузить список проектов. Используется основной проект.")
        return (ProjectRecord(id=DEFAULT_PROJECT_ID, name="Основной проект"),)


def _project_selectbox_key(current_project_id: str, project_ids: tuple[str, ...], key_prefix: str = "global") -> str:
    return f"{PROJECT_SELECTBOX_KEY_PREFIX}_{key_prefix}_{current_project_id}_{len(project_ids)}"


def _render_project_selector(logger, *, key_prefix: str = "global", expanded: bool = False) -> ProjectRecord:
    projects = _load_project_records_for_ui(logger)
    projects_by_id = {project.id: project for project in projects}
    project_ids = tuple(projects_by_id)
    current_project_id = st.session_state.get(ACTIVE_PROJECT_ID_KEY)
    if current_project_id not in projects_by_id:
        current_project_id = DEFAULT_PROJECT_ID if DEFAULT_PROJECT_ID in projects_by_id else projects[0].id
        st.session_state[ACTIVE_PROJECT_ID_KEY] = current_project_id

    with st.expander("Проект", expanded=expanded):
        selected_project_id = st.selectbox(
            "Активный проект",
            options=project_ids,
            index=project_ids.index(current_project_id),
            format_func=lambda project_id: _project_option_label(projects_by_id[project_id]),
            key=_project_selectbox_key(current_project_id, project_ids, key_prefix=key_prefix),
        )
        st.session_state[ACTIVE_PROJECT_ID_KEY] = selected_project_id
        active_project = projects_by_id[selected_project_id]
        st.caption(f"Папка проекта: data/projects/{active_project.id}/")

        with st.form(f"{key_prefix}_create_project_form", clear_on_submit=True):
            new_project_name = st.text_input("Название нового проекта")
            new_project_description = st.text_input("Комментарий")
            submitted = st.form_submit_button("Создать проект")
            if submitted:
                if not new_project_name.strip():
                    st.warning("Введите название проекта.")
                else:
                    try:
                        project = create_project(
                            root=LAS_CORRELATION_PROJECTS_ROOT,
                            name=new_project_name,
                            description=new_project_description,
                        )
                        st.session_state[ACTIVE_PROJECT_ID_KEY] = project.id
                        logger.info("project_created id=%s", safe_log_value(project.id))
                        st.success("Проект создан.")
                        st.rerun()
                    except Exception:
                        logger.exception("project_create_failed")
                        st.error("Не удалось создать проект.")

    return active_project


def _render_las_correlation_project_selector(logger) -> ProjectRecord:
    return _render_project_selector(logger, key_prefix="las_correlation", expanded=True)


def _load_project_las_correlation_settings(project_id: str) -> LasCorrelationSettings | None:
    try:
        return load_project_correlation_settings(
            root=LAS_CORRELATION_PROJECTS_ROOT,
            project_id=project_id,
        )
    except Exception:
        st.warning("Не удалось прочитать настройки проекта. Проверьте файл настроек.")
        return None


def _project_las_option_label(record: ProjectLasFile) -> str:
    status = " | архив" if record.archived_at else ""
    return f"{record.name} | {record.version_label} | {record.saved_at} | {record.original_file_name}{status}"


def _project_las_records_table(well_cards: tuple[ProjectLasWellCard, ...]) -> pd.DataFrame:
    rows = []
    for card in well_cards:
        for version in card.versions:
            rows.append(
                {
                    "Скважина": card.name,
                    "Версия": version.version_label,
                    "Статус": "архив" if version.archived_at else "активна",
                    "Файл": version.original_file_name,
                    "Размер, KB": round(version.size_bytes / 1024, 1),
                    "Сохранено": version.saved_at,
                    "Архивировано": version.archived_at,
                    "Well ID": card.id,
                    "Version ID": version.id,
                }
            )
    return pd.DataFrame(rows)


def _project_las_records_to_raw_sheets(project: ProjectRecord, records: tuple[ProjectLasFile, ...]) -> dict[str, pd.DataFrame]:
    sheets: dict[str, pd.DataFrame] = {}
    for record in records:
        dataframe = read_project_las_file_dataframe(LAS_CORRELATION_PROJECTS_ROOT, project.id, record.id)
        sheet_name = f"{record.name} / {record.version_label}"
        if sheet_name in sheets:
            sheet_name = f"{sheet_name} / {record.id}"
        sheets[sheet_name] = _dataframe_to_raw_sheet(dataframe)
    return sheets


def _render_project_las_zip_download(
    project: ProjectRecord,
    selected_ids: tuple[str, ...],
    *,
    key: str,
    logger,
) -> None:
    if not selected_ids:
        return

    try:
        zip_bytes = export_project_las_files_zip(
            LAS_CORRELATION_PROJECTS_ROOT,
            project.id,
            selected_ids,
        )
    except Exception:
        logger.exception("project_las_export_failed project_id=%s", safe_log_value(project.id))
        st.error("Не удалось подготовить выгрузку проектных LAS. Подробности записаны в logs/app.log.")
        return

    st.download_button(
        "Выгрузить LAS/XLSX/CSV (ZIP)",
        data=zip_bytes,
        file_name=f"{project.id}_las_versions.zip",
        mime="application/zip",
        use_container_width=True,
        key=key,
    )


def _render_project_workspace_loader(project: ProjectRecord, logger) -> None:
    active_well_cards = list_project_las_wells(LAS_CORRELATION_PROJECTS_ROOT, project.id)
    active_records = tuple(version for card in active_well_cards for version in card.versions)

    with st.expander("Данные активного проекта", expanded=bool(active_records)):
        st.caption(f"Открыт проект: {project.name} ({project.id})")
        if not active_records:
            st.caption("В активном проекте пока нет активных LAS-версий.")
            return

        st.dataframe(_project_las_records_table(active_well_cards), use_container_width=True, height=240)
        records_by_id = {record.id: record for record in active_records}
        latest_version_ids = tuple(card.versions[0].id for card in active_well_cards if card.versions)
        selected_ids = tuple(
            st.multiselect(
                "Версии для рабочего workflow",
                options=tuple(records_by_id),
                default=latest_version_ids,
                format_func=lambda record_id: _project_las_option_label(records_by_id[record_id]),
                key=f"workspace_project_las_versions_{project.id}",
            )
        )

        open_col, export_col = st.columns(2)
        if open_col.button("Открыть выбранные версии", use_container_width=True, key=f"workspace_open_project_{project.id}"):
            if not selected_ids:
                st.warning("Выберите хотя бы одну LAS-версию проекта.")
            else:
                try:
                    selected_records = tuple(records_by_id[record_id] for record_id in selected_ids)
                    sheets = _project_las_records_to_raw_sheets(project, selected_records)
                except Exception:
                    logger.exception("project_las_open_failed project_id=%s", safe_log_value(project.id))
                    st.error("Не удалось открыть выбранные LAS-версии проекта. Подробности записаны в logs/app.log.")
                else:
                    st.session_state[PROJECT_SESSION_SHEETS_KEY] = sheets
                    st.session_state[PROJECT_SESSION_PROJECT_ID_KEY] = project.id
                    st.session_state[PROJECT_SESSION_SUMMARY_KEY] = (
                        f"{project.name}: версий {len(selected_records)}, листов {len(sheets)}"
                    )
                    logger.info(
                        "project_las_opened project_id=%s version_count=%d sheet_count=%d",
                        safe_log_value(project.id),
                        len(selected_records),
                        len(sheets),
                    )
                    st.success("Выбранные версии проекта загружены в рабочий workflow.")

        with export_col:
            _render_project_las_zip_download(
                project,
                selected_ids,
                key=f"workspace_project_las_export_{project.id}",
                logger=logger,
            )


def _project_export_option_label(record) -> str:
    return f"{record.label} | {record.saved_at} | {record.file_name}"


def _project_exports_table(records: tuple[object, ...]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Название": record.label,
                "Тип": record.kind,
                "Файл": record.file_name,
                "Источник": record.source,
                "Размер, KB": round(record.size_bytes / 1024, 1),
                "Сохранено": record.saved_at,
                "Export ID": record.id,
            }
            for record in records
        ]
    )


def _render_project_exports_panel(project: ProjectRecord, logger) -> None:
    records = list_project_exports(LAS_CORRELATION_PROJECTS_ROOT, project.id)
    with st.expander("Сохраненные экспорты проекта", expanded=bool(records)):
        if not records:
            st.caption("В активном проекте пока нет сохраненных экспортов.")
            return

        st.dataframe(_project_exports_table(records), use_container_width=True, height=220)
        records_by_id = {record.id: record for record in records}
        selected_id = st.selectbox(
            "Экспорт проекта",
            options=tuple(records_by_id),
            format_func=lambda record_id: _project_export_option_label(records_by_id[record_id]),
            key=f"project_export_select_{project.id}",
        )
        selected_record = records_by_id[selected_id]
        try:
            data = read_project_export_file_bytes(LAS_CORRELATION_PROJECTS_ROOT, project.id, selected_id)
        except Exception:
            logger.exception(
                "project_export_download_failed project_id=%s export_id=%s",
                safe_log_value(project.id),
                safe_log_value(selected_id),
            )
            st.error("Не удалось подготовить сохраненный экспорт. Подробности записаны в logs/app.log.")
            return

        st.download_button(
            "Скачать экспорт",
            data=data,
            file_name=selected_record.file_name,
            mime=selected_record.mime_type,
            use_container_width=True,
            key=f"project_export_download_{project.id}_{selected_id}",
        )
        if selected_record.metadata:
            with st.expander("Metadata экспорта", expanded=False):
                st.json(selected_record.metadata)


def _save_project_export_with_feedback(
    *,
    project: ProjectRecord,
    data: bytes,
    label: str,
    file_name: str,
    mime_type: str,
    kind: str,
    source: str,
    metadata: dict[str, object],
    logger,
) -> None:
    try:
        record = save_project_export(
            data,
            root=LAS_CORRELATION_PROJECTS_ROOT,
            project_id=project.id,
            label=label,
            file_name=file_name,
            mime_type=mime_type,
            kind=kind,
            source=source,
            metadata=metadata,
        )
    except Exception:
        logger.exception("project_export_save_failed project_id=%s kind=%s", safe_log_value(project.id), safe_log_value(kind))
        st.error("Не удалось сохранить экспорт в проект. Подробности записаны в logs/app.log.")
    else:
        logger.info(
            "project_export_saved project_id=%s export_id=%s size=%d",
            safe_log_value(project.id),
            safe_log_value(record.id),
            record.size_bytes,
        )
        st.success(f"Экспорт сохранен в проект: {record.label}.")


def _project_calculation_option_label(record) -> str:
    warning_label = f" | предупреждений: {record.warnings_count}" if record.warnings_count else ""
    return f"{record.source_label} | {record.saved_at} | строк: {record.row_count}{warning_label}"


def _project_calculations_table(records: tuple[object, ...]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Источник": record.source_label,
                "Набор данных": record.sheet_name,
                "Строк": record.row_count,
                "Ch": record.ch_mode,
                "Предупреждений": record.warnings_count,
                "Сохранено": record.saved_at,
                "Calculation ID": record.id,
            }
            for record in records
        ]
    )


def _render_project_calculation_metadata(project: ProjectRecord, calculation_id: str, logger) -> None:
    try:
        metadata = read_project_calculation_metadata(LAS_CORRELATION_PROJECTS_ROOT, project.id, calculation_id)
    except Exception:
        logger.exception(
            "project_calculation_metadata_read_failed project_id=%s calculation_id=%s",
            safe_log_value(project.id),
            safe_log_value(calculation_id),
        )
        st.warning("Не удалось прочитать metadata сохраненного расчета.")
        return

    mapping = metadata.get("mapping", {})
    warnings = metadata.get("warnings", [])
    with st.expander("Mapping и предупреждения расчета", expanded=False):
        st.caption(f"Ch: {metadata.get('ch_mode', '') or 'не указан'}; строка заголовков: {metadata.get('header_row')}")
        st.caption("Mapping")
        st.json(mapping)
        if warnings:
            st.caption("Предупреждения")
            for warning in warnings:
                st.warning(str(warning))
        else:
            st.success("Сохраненный расчет не содержит предупреждений.")


def _render_project_calculations_panel(project: ProjectRecord, logger) -> None:
    records = list_project_calculations(LAS_CORRELATION_PROJECTS_ROOT, project.id)
    with st.expander("Сохраненные расчеты проекта", expanded=bool(records)):
        if not records:
            st.caption("В активном проекте пока нет сохраненных расчетов.")
            return

        st.dataframe(_project_calculations_table(records), use_container_width=True, height=220)
        records_by_id = {record.id: record for record in records}
        selected_id = st.selectbox(
            "Расчет проекта",
            options=tuple(records_by_id),
            format_func=lambda record_id: _project_calculation_option_label(records_by_id[record_id]),
            key=f"project_calculation_select_{project.id}",
        )
        selected_record = records_by_id[selected_id]
        _render_project_calculation_metadata(project, selected_id, logger)

        csv_col, xlsx_col, open_col = st.columns(3)
        try:
            csv_col.download_button(
                "Скачать CSV",
                data=read_project_calculation_file_bytes(
                    LAS_CORRELATION_PROJECTS_ROOT, project.id, selected_id, "csv"
                ),
                file_name=f"{selected_record.id}.csv",
                mime="text/csv",
                use_container_width=True,
                key=f"project_calculation_csv_{project.id}_{selected_id}",
            )
            xlsx_col.download_button(
                "Скачать XLSX",
                data=read_project_calculation_file_bytes(
                    LAS_CORRELATION_PROJECTS_ROOT, project.id, selected_id, "xlsx"
                ),
                file_name=f"{selected_record.id}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key=f"project_calculation_xlsx_{project.id}_{selected_id}",
            )
        except Exception:
            logger.exception(
                "project_calculation_download_failed project_id=%s calculation_id=%s",
                safe_log_value(project.id),
                safe_log_value(selected_id),
            )
            st.error("Не удалось подготовить выгрузку сохраненного расчета. Подробности записаны в logs/app.log.")

        if open_col.button(
            "Открыть в графиках",
            use_container_width=True,
            key=f"project_calculation_open_{project.id}_{selected_id}",
        ):
            try:
                calculation_df = read_project_calculation_dataframe(
                    LAS_CORRELATION_PROJECTS_ROOT, project.id, selected_id
                )
                _store_interpretation_dataset(
                    calculation_df,
                    f"{project.name} / {selected_record.source_label}",
                )
            except Exception:
                logger.exception(
                    "project_calculation_open_failed project_id=%s calculation_id=%s",
                    safe_log_value(project.id),
                    safe_log_value(selected_id),
                )
                st.error("Не удалось открыть сохраненный расчет. Подробности записаны в logs/app.log.")
            else:
                st.success("Сохраненный расчет открыт во вкладке `Интерпретационные графики`.")


def _render_project_calculation_saver(
    *,
    project: ProjectRecord,
    calculated_df: pd.DataFrame,
    selected_source: str,
    sheet_name: str,
    mapping: dict[str, str],
    ch_mode: str,
    warnings: tuple[str, ...] | list[str],
    header_row: int,
    logger,
) -> None:
    with st.expander("Сохранить расчет в проект", expanded=False):
        st.caption(f"Активный проект: {project.name} ({project.id})")
        default_label = f"{selected_source}: {sheet_name}"
        calculation_label = st.text_input(
            "Название расчета",
            value=default_label,
            key=f"project_calculation_label_{project.id}",
        )
        if st.button("Сохранить расчетный snapshot", use_container_width=True, key=f"save_calculation_{project.id}"):
            try:
                record = save_project_calculation(
                    calculated_df,
                    root=LAS_CORRELATION_PROJECTS_ROOT,
                    project_id=project.id,
                    source_label=calculation_label,
                    sheet_name=str(sheet_name),
                    mapping=mapping,
                    ch_mode=ch_mode,
                    warnings=tuple(warnings),
                    header_row=int(header_row),
                )
            except Exception:
                logger.exception("project_calculation_save_failed project_id=%s", safe_log_value(project.id))
                st.error("Не удалось сохранить расчет в проект. Подробности записаны в logs/app.log.")
            else:
                logger.info(
                    "project_calculation_saved project_id=%s calculation_id=%s rows=%d",
                    safe_log_value(project.id),
                    safe_log_value(record.id),
                    len(calculated_df),
                )
                st.success(f"Расчет сохранен в проект: {record.source_label}.")


def _render_project_las_files_panel(
    project: ProjectRecord,
    uploaded_files: tuple[object, ...],
    logger,
) -> tuple[object, ...]:
    active_well_cards = list_project_las_wells(LAS_CORRELATION_PROJECTS_ROOT, project.id)
    active_records = tuple(version for card in active_well_cards for version in card.versions)
    all_records = list_project_las_files(LAS_CORRELATION_PROJECTS_ROOT, project.id, include_archived=True)
    archived_records = tuple(record for record in all_records if record.archived_at)
    selected_records: tuple[ProjectLasFile, ...] = ()

    with st.expander("LAS-файлы проекта", expanded=bool(active_records or archived_records)):
        if uploaded_files:
            st.caption("Сохраните загруженные LAS в активный проект, чтобы открыть их после перезапуска приложения.")
            if st.button("Сохранить загруженные LAS в проект", use_container_width=True, key="save_uploaded_las_to_project"):
                try:
                    saved_count = 0
                    for uploaded_file in uploaded_files:
                        original_name = Path(str(getattr(uploaded_file, "name", "source.las"))).name
                        save_project_las_file(
                            data=bytes(uploaded_file.getvalue()),
                            root=LAS_CORRELATION_PROJECTS_ROOT,
                            project_id=project.id,
                            file_name=original_name,
                            well_name=Path(original_name).stem,
                            version_label="Загруженный LAS",
                        )
                        saved_count += 1
                    logger.info(
                        "project_las_files_saved project_id=%s count=%d",
                        safe_log_value(project.id),
                        saved_count,
                    )
                    st.success(f"LAS-файлы сохранены в проект: {saved_count}.")
                    st.rerun()
                except Exception:
                    logger.exception("project_las_files_save_failed project_id=%s", safe_log_value(project.id))
                    st.error("Не удалось сохранить LAS-файлы в проект. Подробности записаны в logs/app.log.")

        if not active_records and not archived_records:
            st.caption("В активном проекте пока нет сохраненных LAS-файлов.")
            return ()

        show_archived = False
        if archived_records:
            show_archived = st.checkbox(
                "Показать архивные версии",
                value=False,
                key=f"project_las_show_archived_{project.id}",
            )
        display_well_cards = list_project_las_wells(
            LAS_CORRELATION_PROJECTS_ROOT,
            project.id,
            include_archived=show_archived,
        )
        st.dataframe(_project_las_records_table(display_well_cards), use_container_width=True, height=260)

        if active_records:
            archive_options = {record.id: record for record in active_records}
            archive_col, archive_button_col = st.columns([3, 1])
            archive_id = archive_col.selectbox(
                "Версия для архива",
                options=tuple(archive_options),
                format_func=lambda record_id: _project_las_option_label(archive_options[record_id]),
                key=f"project_las_archive_select_{project.id}",
            )
            if archive_button_col.button("В архив", use_container_width=True, key=f"project_las_archive_button_{project.id}"):
                try:
                    set_project_las_file_archived(
                        LAS_CORRELATION_PROJECTS_ROOT,
                        project.id,
                        archive_id,
                        archived=True,
                    )
                    logger.info(
                        "project_las_file_archived project_id=%s las_file_id=%s",
                        safe_log_value(project.id),
                        safe_log_value(archive_id),
                    )
                    st.success("Версия LAS перенесена в архив.")
                    st.rerun()
                except Exception:
                    logger.exception("project_las_file_archive_failed project_id=%s", safe_log_value(project.id))
                    st.error("Не удалось архивировать версию LAS. Подробности записаны в logs/app.log.")

        if show_archived and archived_records:
            restore_options = {record.id: record for record in archived_records}
            restore_col, restore_button_col = st.columns([3, 1])
            restore_id = restore_col.selectbox(
                "Версия для восстановления",
                options=tuple(restore_options),
                format_func=lambda record_id: _project_las_option_label(restore_options[record_id]),
                key=f"project_las_restore_select_{project.id}",
            )
            if restore_button_col.button("Вернуть", use_container_width=True, key=f"project_las_restore_button_{project.id}"):
                try:
                    set_project_las_file_archived(
                        LAS_CORRELATION_PROJECTS_ROOT,
                        project.id,
                        restore_id,
                        archived=False,
                    )
                    logger.info(
                        "project_las_file_restored project_id=%s las_file_id=%s",
                        safe_log_value(project.id),
                        safe_log_value(restore_id),
                    )
                    st.success("Версия LAS возвращена из архива.")
                    st.rerun()
                except Exception:
                    logger.exception("project_las_file_restore_failed project_id=%s", safe_log_value(project.id))
                    st.error("Не удалось вернуть версию LAS из архива. Подробности записаны в logs/app.log.")

        records_by_id = {record.id: record for record in active_records}
        latest_version_ids = tuple(card.versions[0].id for card in active_well_cards if card.versions)
        default_ids = latest_version_ids if not uploaded_files else ()
        selected_ids = st.multiselect(
            "Добавить сохраненные версии LAS из проекта в корреляцию",
            options=tuple(records_by_id),
            default=default_ids,
            format_func=lambda record_id: _project_las_option_label(records_by_id[record_id]),
            key=f"project_las_files_{project.id}",
        )
        selected_records = tuple(records_by_id[record_id] for record_id in selected_ids)
        _render_project_las_zip_download(
            project,
            tuple(selected_ids),
            key=f"project_las_export_{project.id}",
            logger=logger,
        )

    sources: list[object] = []
    for record in selected_records:
        try:
            data = read_project_las_file_bytes(LAS_CORRELATION_PROJECTS_ROOT, project.id, record.id)
            sources.append(_NamedLasBytesIO(data, f"{record.name}_{record.version_label}.las"))
        except Exception:
            logger.exception(
                "project_las_file_read_failed project_id=%s las_file_id=%s",
                safe_log_value(project.id),
                safe_log_value(record.id),
            )
            st.error(f"Не удалось прочитать LAS из проекта: {record.name}, версия {record.version_label}.")
    return tuple(sources)


def _render_las_correlation_settings_loader(wells, group_options: tuple[str, ...], project_id: str) -> None:
    session_key = _project_settings_session_key(project_id)
    session_payload = st.session_state.get(session_key)
    session_settings = settings_from_dict(session_payload) if session_payload else None
    project_settings = _load_project_las_correlation_settings(project_id)

    if session_settings is None and project_settings is None:
        return

    with st.expander("Сохраненные настройки корреляции", expanded=False):
        if project_settings is not None:
            st.markdown("**Проект**")
            for line in settings_summary(project_settings):
                st.caption(line)
            if st.button("Загрузить настройки проекта", use_container_width=True, key="las_correlation_load_project_settings"):
                _apply_las_correlation_settings_to_session(project_settings, wells, group_options)
                st.session_state[session_key] = settings_to_dict(project_settings)
                st.rerun()

        if session_settings is not None:
            st.markdown("**Текущая сессия**")
            for line in settings_summary(session_settings):
                st.caption(line)
            apply_col, clear_col = st.columns(2)
            if apply_col.button("Применить настройки сессии", use_container_width=True, key="las_correlation_apply_saved_settings"):
                _apply_las_correlation_settings_to_session(session_settings, wells, group_options)
                st.rerun()
            if clear_col.button("Очистить настройки сессии", use_container_width=True, key="las_correlation_clear_saved_settings"):
                st.session_state.pop(session_key, None)
                st.rerun()


def _render_las_correlation_settings_saver(settings: LasCorrelationSettings, project_id: str) -> None:
    with st.expander("Текущие настройки корреляции", expanded=False):
        for line in settings_summary(settings):
            st.caption(line)
        project_col, session_col = st.columns(2)
        if project_col.button("Сохранить в проект", use_container_width=True, key="las_correlation_save_project_settings"):
            try:
                save_project_correlation_settings(
                    settings,
                    root=LAS_CORRELATION_PROJECTS_ROOT,
                    project_id=project_id,
                )
                st.session_state[_project_settings_session_key(project_id)] = settings_to_dict(settings)
                st.success("Настройки корреляции сохранены в проект.")
            except Exception:
                st.error("Не удалось сохранить настройки проекта.")
        if session_col.button("Сохранить в сессию", use_container_width=True, key="las_correlation_save_current_settings"):
            st.session_state[_project_settings_session_key(project_id)] = settings_to_dict(settings)
            st.success("Настройки корреляции сохранены в текущей сессии.")


def _render_las_correlation_interval_table(
    wells,
    *,
    groups: tuple[str, ...],
    depth_range: tuple[float, float] | None,
    project_id: str,
) -> None:
    interval_table = build_las_correlation_interval_table(
        wells,
        groups=groups,
        depth_range=depth_range,
    )
    with st.expander("Таблица выбранного интервала", expanded=False):
        st.caption("Таблица содержит выбранные скважины, глубину и кривые из групп, показанных на correlation-графике.")
        st.metric("Строк в таблице", len(interval_table))
        if interval_table.empty:
            st.warning("В выбранном интервале нет строк LAS для выбранных скважин и групп кривых.")
            return
        st.dataframe(interval_table, use_container_width=True, height=420)
        csv_col, xlsx_col, las_col = st.columns(3)
        csv_col.download_button(
            "Экспорт CSV",
            data=export_csv_bytes(interval_table),
            file_name=f"las_correlation_interval_{project_id}.csv",
            mime="text/csv",
            use_container_width=True,
        )
        xlsx_col.download_button(
            "Экспорт XLSX",
            data=export_xlsx_bytes(interval_table, sheet_name="interval"),
            file_name=f"las_correlation_interval_{project_id}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
        las_col.download_button(
            "Экспорт LAS",
            data=export_las_bytes(interval_table, well_name=project_id, depth_column="depth"),
            file_name=f"las_correlation_interval_{project_id}.las",
            mime="text/plain",
            use_container_width=True,
        )


def _render_las_correlation_tab(logger, active_project: ProjectRecord) -> None:
    st.subheader("LAS-корреляция")
    st.caption("Загрузите несколько LAS, чтобы смотреть ГИС-кривые рядом с газами по общей глубине.")
    st.caption(f"Активный проект: {active_project.name} ({active_project.id})")

    uploaded_files = tuple(
        st.file_uploader(
            "LAS-файлы для корреляции",
            type=["las"],
            accept_multiple_files=True,
            key="las_correlation_files",
        )
        or ()
    )
    project_las_sources = _render_project_las_files_panel(active_project, uploaded_files, logger)
    las_sources = (*project_las_sources, *uploaded_files)
    if not las_sources:
        st.info("Загрузите LAS-файлы или выберите сохраненные LAS активного проекта.")
        return

    try:
        wells = prepare_las_correlation_wells(las_sources)
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

    group_options = [
        group
        for group in CURVE_GROUP_LABELS
        if group not in {"depth", "lithology", "other"}
    ]
    _render_las_correlation_settings_loader(wells, tuple(group_options), active_project.id)

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

    selected_wells, curve_group_overrides = _render_curve_group_override_controls(selected_wells)

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

    with st.expander("Ручной масштаб X", expanded=False):
        gis_x_range = _select_x_range("LAS-корреляция: ГИС слева", "las_correlation_gis")
        gas_x_range = _select_x_range("LAS-корреляция: газы справа", "las_correlation_gas")

    height_per_well = st.slider(
        "Высота на скважину",
        min_value=320,
        max_value=750,
        value=430,
        step=10,
        key="las_correlation_height_per_well",
    )
    selected_groups = tuple(dict.fromkeys((*gis_groups, *gas_groups)))
    view_mode = st.radio(
        "Представление графика",
        options=SUPPORTED_VIEW_MODES,
        horizontal=True,
        key="las_correlation_view_mode",
    )
    comparison_curve = ""
    if view_mode == VIEW_MODE_BY_CURVE:
        comparison_curve_options = curve_names_for_comparison(selected_wells, groups=selected_groups)
        if not comparison_curve_options:
            st.warning("Нет числовых кривых для сравнения в выбранных группах.")
        else:
            saved_curve = st.session_state.get("las_correlation_comparison_curve")
            if saved_curve not in comparison_curve_options:
                st.session_state["las_correlation_comparison_curve"] = comparison_curve_options[0]
            comparison_curve = st.selectbox(
                "Кривая для сравнения",
                options=comparison_curve_options,
                key="las_correlation_comparison_curve",
            )

    current_settings = LasCorrelationSettings(
        selected_well_names=tuple(well.name for well in selected_wells),
        curve_group_overrides=curve_group_overrides,
        gis_groups=tuple(gis_groups),
        gas_groups=tuple(gas_groups),
        depth_range=depth_range,
        gis_x_range=gis_x_range,
        gas_x_range=gas_x_range,
        height_per_well=int(height_per_well),
        view_mode=view_mode,
        comparison_curve=comparison_curve,
    )
    if view_mode == VIEW_MODE_BY_CURVE and comparison_curve:
        figure = build_las_curve_comparison_figure(
            selected_wells,
            comparison_curve,
            depth_range=depth_range,
            x_range=_comparison_x_range_for_curve(
                selected_wells,
                comparison_curve,
                tuple(gis_groups),
                tuple(gas_groups),
                gis_x_range,
                gas_x_range,
            ),
            height=max(650, int(height_per_well)),
        )
        figure_title = f"Gas Ratio Interpreter - LAS curve comparison: {comparison_curve}"
        figure_file_name = "las_curve_comparison.html"
    else:
        figure = build_las_correlation_figure(
            selected_wells,
            gis_groups=tuple(gis_groups),
            gas_groups=tuple(gas_groups),
            depth_range=depth_range,
            gis_x_range=gis_x_range,
            gas_x_range=gas_x_range,
            height_per_well=height_per_well,
        )
        figure_title = "Gas Ratio Interpreter - LAS correlation"
        figure_file_name = "las_correlation.html"

    report_metadata_rows = _las_correlation_report_rows(
        project=active_project,
        selected_wells=selected_wells,
        depth_range=depth_range,
        gis_groups=tuple(gis_groups),
        gas_groups=tuple(gas_groups),
        gis_x_range=gis_x_range,
        gas_x_range=gas_x_range,
        view_mode=view_mode,
        comparison_curve=comparison_curve,
    )
    st.plotly_chart(figure, use_container_width=True)
    st.download_button(
        "HTML для печати графика",
        data=_plotly_figures_to_html(
            [figure],
            figure_title,
            subtitle="LAS-корреляция: печатный график выбранного интервала",
            metadata_rows=report_metadata_rows,
            notes=(INTERPRETATION_NOTE,),
        ),
        file_name=figure_file_name,
        mime="text/html",
        use_container_width=True,
    )
    _render_static_export_controls(
        figure,
        base_file_name=figure_file_name,
        default_height=int(figure.layout.height or height_per_well),
        key_prefix="las_correlation",
    )
    _render_las_correlation_interval_table(
        selected_wells,
        groups=selected_groups,
        depth_range=depth_range,
        project_id=active_project.id,
    )
    _render_las_correlation_settings_saver(current_settings, active_project.id)

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
    ui_layout = _select_ui_layout()
    _apply_app_style(ui_scale, ui_layout)
    st.title("Gas Ratio Interpreter v0.3")
    st.caption(INTERPRETATION_NOTE)

    logger = configure_logging()
    logger.info("streamlit_app_started")

    active_project = _render_project_selector(logger, key_prefix="global", expanded=True)

    start_tab, workspace_tab, las_editor_tab, correlation_tab, graphs_tab, docs_tab = st.tabs(list(APP_TABS))
    with start_tab:
        _render_start_tab(active_project)
    with workspace_tab:
        _render_workspace(logger, active_project)
    with las_editor_tab:
        _render_las_editor(logger, active_project)
    with correlation_tab:
        _render_las_correlation_tab(logger, active_project)
    with graphs_tab:
        _render_interpretation_graphs_tab(logger, active_project)
    with docs_tab:
        _render_documentation_tab()


if __name__ == "__main__":
    main()
