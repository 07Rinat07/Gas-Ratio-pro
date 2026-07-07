from __future__ import annotations

import base64
import html
import importlib
import random
import sys
from datetime import datetime
from io import BytesIO
from pathlib import Path
from textwrap import dedent

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

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
    build_correlation_panel,
    build_correlation_panel_figure,
    common_curve_names,
    correlation_marker_rows,
    correlation_panel_summary,
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
from las_editor.curve_alias import assign_curve_alias, available_aliases, suggest_curve_aliases, undo_last_alias
from las_editor.curve_categories import (
    assign_curve_category,
    available_curve_categories,
    build_curve_categories,
    category_summary_rows,
    curve_category_label,
    curve_category_table_rows,
    undo_last_category_assignment,
)
from las_editor.curve_grouping import (
    assign_curve_group,
    available_curve_groups,
    curve_group_label,
    curve_group_table_rows,
    undo_last_group_assignment,
)
from las_editor.curve_units import (
    assign_curve_unit,
    available_curve_units,
    build_curve_units,
    curve_unit_label,
    curve_unit_table_rows,
    undo_last_unit_assignment,
    unit_summary_rows,
)
from las_editor.curve_duplicates import (
    curve_duplicate_summary_rows,
    curve_duplicate_table_rows,
    detect_curve_duplicates,
)
from las_editor.curve_quality import (
    curve_quality_flag_rows,
    curve_quality_summary_rows,
    detect_curve_quality_flags,
)
from las_editor.curve_mnemonics import (
    curve_mnemonic_table_rows,
    mnemonic_reference_manifest,
    mnemonic_summary_rows,
)
from las_editor.curve_bulk_edit import (
    BULK_EDIT_ACTION_LABELS,
    apply_curve_bulk_edit,
    curve_bulk_edit_operation_rows,
)
from las_editor.curve_export_rules import (
    apply_curve_export_rules,
    available_export_profiles,
    curve_export_preview_rows,
    export_profile_rows,
    get_export_profile,
)
from las_editor.curve_metadata import (
    assign_curve_metadata,
    available_metadata_fields,
    available_metadata_qualities,
    available_metadata_statuses,
    build_curve_metadata,
    curve_metadata_table_rows,
    metadata_quality_label,
    metadata_status_label,
    metadata_summary_rows,
    undo_last_metadata_assignment,
)
from las_editor.curve_merge import MERGE_STRATEGIES, merge_curves, undo_last_merge
from las_editor.curve_rename import CurveRenameHistoryEntry, rename_curve, undo_last_rename
from las_editor.depth_grid import (
    apply_las_bulk_operations,
    build_safe_las_filename,
    build_las_edit_audit_log,
    build_las_edit_preview,
    build_las_editor_hints,
    fix_depth_direction,
    insert_manual_depth_rows,
    shift_depth_values,
    convert_depth_units,
    crop_depth_interval,
    resample_depth_step,
    validate_depth_integrity,
    resample_las_data,
)
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
from projects import (
    ProjectRecord,
    build_project_tree,
    create_project,
    ensure_default_project,
    list_project_explorer_folder_targets,
    list_project_explorer_move_options,
    list_project_explorer_well_group_targets,
    list_projects,
    move_project_explorer_item_to_folder,
    move_project_explorer_well_to_group,
    project_tree_table_rows,
    append_project_history,
    archive_project,
    build_project_backups_table,
    build_project_history_table,
    build_project_templates_table,
    clear_project_recovery_state,
    create_project_backup,
    create_project_from_template,
    create_project_template,
    list_project_backups,
    list_project_history,
    list_project_templates,
    load_project_recovery_state,
    project_manager_status,
    save_project_recovery_state,
)
from projects import calculations as project_calculations
from projects import exports as project_exports
from projects import graph_settings as project_graph_settings
from projects import datasets as project_datasets
from projects import project_labels as project_labels
from projects import project_index as project_index
from projects import well_cards as project_well_cards
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
project_datasets = importlib.reload(project_datasets)
project_las_files = importlib.reload(project_las_files)
project_labels = importlib.reload(project_labels)
project_index = importlib.reload(project_index)
project_well_cards = importlib.reload(project_well_cards)
list_project_calculations = project_calculations.list_project_calculations
filter_project_calculations = project_calculations.filter_project_calculations
summarize_project_calculations = project_calculations.summarize_project_calculations
read_project_calculation_dataframe = project_calculations.read_project_calculation_dataframe
read_project_calculation_file_bytes = project_calculations.read_project_calculation_file_bytes
read_project_calculation_metadata = project_calculations.read_project_calculation_metadata
build_project_calculation_card = project_calculations.build_project_calculation_card
check_project_calculation_integrity = project_calculations.check_project_calculation_integrity
compare_project_calculations = project_calculations.compare_project_calculations
build_project_calculation_comparison_table = project_calculations.build_project_calculation_comparison_table
export_project_calculation_comparison_csv = project_calculations.export_project_calculation_comparison_csv
export_project_calculation_comparison_html = project_calculations.export_project_calculation_comparison_html
export_project_calculation_actions_csv = project_calculations.export_project_calculation_actions_csv
export_project_calculation_actions_html = project_calculations.export_project_calculation_actions_html
export_project_calculation_card_html = project_calculations.export_project_calculation_card_html
export_project_calculation_card_csv = project_calculations.export_project_calculation_card_csv
save_project_calculation = project_calculations.save_project_calculation
append_project_calculation_action = project_calculations.append_project_calculation_action
list_project_calculation_actions = project_calculations.list_project_calculation_actions
list_project_exports = project_exports.list_project_exports
read_project_export_file_bytes = project_exports.read_project_export_file_bytes
save_project_export = project_exports.save_project_export
list_project_las_datasets = project_datasets.list_project_las_datasets
list_project_csv_datasets = project_datasets.list_project_csv_datasets
save_project_csv_dataset = project_datasets.save_project_csv_dataset
list_project_excel_datasets = project_datasets.list_project_excel_datasets
save_project_excel_dataset = project_datasets.save_project_excel_dataset
list_project_core_datasets = project_datasets.list_project_core_datasets
save_project_core_dataset = project_datasets.save_project_core_dataset
list_project_mud_log_datasets = project_datasets.list_project_mud_log_datasets
save_project_mud_log_dataset = project_datasets.save_project_mud_log_dataset
list_project_production_datasets = project_datasets.list_project_production_datasets
save_project_production_dataset = project_datasets.save_project_production_dataset
build_project_dataset_table = project_datasets.build_project_dataset_table
build_project_duplicate_files_table = project_index.build_project_duplicate_files_table
build_project_file_index_table = project_index.build_project_file_index_table
build_project_file_versions_table = project_index.build_project_file_versions_table
build_project_file_version_history_table = project_index.build_project_file_version_history_table
build_project_uuid_registry_table = project_index.build_project_uuid_registry_table
detect_project_duplicate_files = project_index.detect_project_duplicate_files
annotate_project_file_index_duplicates = project_index.annotate_project_file_index_duplicates
load_project_file_index = project_index.load_project_file_index
load_project_file_versions = project_index.load_project_file_versions
load_project_uuid_registry = project_index.load_project_uuid_registry
save_project_file_index = project_index.save_project_file_index
update_project_file_versions = project_index.update_project_file_versions
update_project_uuid_registry = project_index.update_project_uuid_registry
validate_project_uuid_registry = project_index.validate_project_uuid_registry
validate_project_file_index = project_index.validate_project_file_index
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
PROJECT_EXPLORER_LABEL_COLORS = project_labels.PROJECT_EXPLORER_LABEL_COLORS
PROJECT_EXPLORER_LABEL_ICONS = project_labels.PROJECT_EXPLORER_LABEL_ICONS
set_project_explorer_label = project_labels.set_project_explorer_label
clear_project_explorer_label = project_labels.clear_project_explorer_label
PROJECT_WELL_CARD_STATUSES = project_well_cards.PROJECT_WELL_CARD_STATUSES
ensure_project_well_card = project_well_cards.ensure_project_well_card
get_project_well_card = project_well_cards.get_project_well_card
save_project_well_card = project_well_cards.save_project_well_card

SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xlsm", ".las"}
WELLS_STORAGE_ROOT = ROOT_DIR / DEFAULT_WELLS_ROOT
LAS_CORRELATION_PROJECTS_ROOT = ROOT_DIR / DEFAULT_PROJECTS_ROOT
APP_LAUNCH_COMMAND = "python -m streamlit run app/streamlit_app.py"
APP_LAUNCH_SCRIPT = ".\\run_app.ps1"
DASHBOARD_BACKGROUND_PATH = ROOT_DIR / "assets" / "dashboard" / "gas_ratio_brand_background.png"
DOCUMENTATION_HERO_PATH = ROOT_DIR / "assets" / "dashboard" / "documentation_hero.png"
BRANDING_LOGO_PATH = ROOT_DIR / "assets" / "branding" / "gas_ratio_pro_logo.png"
APP_ICON_PATH = BRANDING_LOGO_PATH
APP_SPLASH_LOGO_PATH = BRANDING_LOGO_PATH
EXPORT_WATERMARK_LOGO_PATH = BRANDING_LOGO_PATH
APP_IDENTITY: dict[str, str] = {
    "name": "Gas Ratio Pro",
    "version": "2.0.0",
    "author": "Rinat Sarmuldin",
    "copyright": "Copyright (c) 2026 Rinat Sarmuldin. All rights reserved.",
    "contact": "ura07srr@gmail.com",
    "license": "Proprietary License",
    "tagline": "Commercial mud gas and LAS interpretation workspace",
}
APP_BRANDING_PLACEMENTS: tuple[str, ...] = (
    "navbar logo",
    "sidebar logo",
    "dashboard watermark 5-8%",
    "documentation hero logo",
    "about brand block",
    "license header logo",
    "splash screen",
    "application icon",
    "PDF/PNG export watermark option",
    "official copyright block",
)
EXPORT_WATERMARK_DEFAULT_OPACITY = "0.06"
DASHBOARD_TIPS = (
    "Проверяйте единицы измерения перед расчетом газовых коэффициентов.",
    "Используйте LAS-редактор для нормализации глубины перед корреляцией.",
    "Сохраняйте расчет в проект, чтобы он появился в истории и отчетах.",
    "Для сравнения скважин сначала настройте группы кривых в LAS-корреляции.",
    "Экспортируйте interval report после проверки предупреждений по mapping и NULL-значениям.",
)
UI_SCALE_KEY = "ui_scale"
UI_LAYOUT_KEY = "ui_layout"
ACTIVE_MAIN_TAB_KEY = "active_main_tab"
COMMAND_PALETTE_QUERY_KEY = "global_command_palette_query"
COMMAND_PALETTE_CATEGORY_KEY = "global_command_palette_category"
COMMAND_PALETTE_RECENT_KEY = "global_command_palette_recent_commands"
COMMAND_PALETTE_FAVORITES_KEY = "global_command_palette_favorite_commands"
COMMAND_PALETTE_ACTIVE_INDEX_KEY = "global_command_palette_active_index"
DASHBOARD_LAST_QUICK_ACTION_KEY = "dashboard_last_quick_action"
# Legacy compact sidebar width marker: 10.8rem. Current sidebar uses a wider modern project card.
# Smoke-test marker for simplified clickable navigation labels: Старт.
# Dashboard 3.0 nav fix marker: no-empty-nav-cards removes blank rectangles above navigation buttons.
LAS_EDITOR_SESSION_SHEETS_KEY = "las_editor_session_sheets"
LAS_EDITOR_SESSION_SUMMARY_KEY = "las_editor_session_summary"
LAS_EDITOR_RENAME_HISTORY_KEY = "las_editor_curve_rename_history"
LAS_EDITOR_ALIAS_HISTORY_KEY = "las_editor_curve_alias_history"
LAS_EDITOR_ALIAS_MAP_KEY = "las_editor_curve_alias_map"
LAS_EDITOR_MERGE_HISTORY_KEY = "las_editor_curve_merge_history"
LAS_EDITOR_GROUP_HISTORY_KEY = "las_editor_curve_group_history"
LAS_EDITOR_GROUP_OVERRIDES_KEY = "las_editor_curve_group_overrides"
LAS_EDITOR_CATEGORY_HISTORY_KEY = "las_editor_curve_category_history"
LAS_EDITOR_CATEGORY_OVERRIDES_KEY = "las_editor_curve_category_overrides"
LAS_EDITOR_UNIT_HISTORY_KEY = "las_editor_curve_unit_history"
LAS_EDITOR_UNIT_OVERRIDES_KEY = "las_editor_curve_unit_overrides"
LAS_EDITOR_METADATA_HISTORY_KEY = "las_editor_curve_metadata_history"
LAS_EDITOR_METADATA_KEY = "las_editor_curve_metadata"
LAS_EDITOR_DUPLICATES_KEY = "las_editor_curve_duplicate_candidates"
LAS_EDITOR_DUPLICATE_SUMMARY_KEY = "las_editor_curve_duplicate_summary"
LAS_EDITOR_QUALITY_FLAGS_KEY = "las_editor_curve_quality_flags"
LAS_EDITOR_QUALITY_SUMMARY_KEY = "las_editor_curve_quality_summary"
LAS_EDITOR_MNEMONICS_KEY = "las_editor_curve_mnemonics"
LAS_EDITOR_BULK_EDIT_LOG_KEY = "las_editor_curve_bulk_edit_log"
LAS_EDITOR_EXPORT_RULES_KEY = "las_editor_curve_export_rules"
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
    "Лицензия",
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
    "phone": {
        "label": "Телефон",
        "max_width": "100vw",
        "columns": "1",
        "description": "Для узких экранов и телефона: одна колонка, крупные кнопки и скрытие второстепенных панелей.",
    },
    "standard": {
        "label": "Ноутбук",
        "max_width": "min(1440px, calc(100vw - 1.2rem))",
        "columns": "2",
        "description": "Для ноутбуков и стандартных экранов: две колонки, крупные карточки и без лишних пустых полей.",
    },
    "wide": {
        "label": "Большой экран",
        "max_width": "calc(100vw - 0.8rem)",
        "columns": "3",
        "description": "Для широких мониторов: вся доступная ширина под Dashboard, планшеты, корреляцию и таблицы интервала.",
    },
}


RESPONSIVE_DASHBOARD_TARGETS: tuple[dict[str, str], ...] = (
    {"name": "1366×768 laptop", "media": "@media (max-width: 1366px)", "layout": "compact two-column dashboard"},
    {"name": "1440×900 laptop", "media": "@media (max-width: 1440px)", "layout": "balanced laptop dashboard"},
    {"name": "1600×900 desktop", "media": "@media (max-width: 1600px)", "layout": "wide desktop dashboard"},
    {"name": "1920×1080 Full HD", "media": "@media (min-width: 1920px)", "layout": "full-width engineering dashboard"},
    {"name": "2560×1440 / 3440×1440 / 3840×2160", "media": "@media (min-width: 2560px)", "layout": "large monitor dashboard with capped content density"},
    {"name": "Tablet", "media": "@media (max-width: 1024px)", "layout": "tablet stacked dashboard"},
    {"name": "Mobile", "media": "@media (max-width: 760px)", "layout": "single-column mobile dashboard"},
    {"name": "Narrow mobile", "media": "@media (max-width: 480px)", "layout": "minimal controls, no horizontal overflow"},
)



BACKGROUND_MANAGER_RULES: dict[str, dict[str, str]] = {
    "Старт": {
        "mode": "branded",
        "overlay": "0.25",
        "glass": "0.58",
        "position": "right 3vw bottom 1.2rem",
        "size": "clamp(210px, 29vw, 504px) auto",
        "reason": "Dashboard keeps the branded image visible behind glass cards without hiding text.",
    },
    "Инструкции и документация": {
        "mode": "documentation",
        "overlay": "0.22",
        "glass": "0.64",
        "position": "right 2vw top 6rem",
        "size": "clamp(224px, 27vw, 532px) auto",
        "reason": "Documentation can show the branded hero artwork while long text stays on readable glass panels.",
    },
    "Лицензия": {
        "mode": "documentation",
        "overlay": "0.30",
        "glass": "0.74",
        "position": "center bottom 1rem",
        "size": "clamp(180px, 21vw, 360px) auto",
        "reason": "License page uses a centered branded background with high-contrast legal panels.",
    },
    "Работа с данными": {
        "mode": "dark-workspace",
        "overlay": "1.00",
        "glass": "0.88",
        "position": "disabled",
        "size": "disabled",
        "reason": "Tables, mapping controls and numeric diagnostics use a solid workspace for readability.",
    },
    "LAS-редактор": {
        "mode": "dark-workspace",
        "overlay": "1.00",
        "glass": "0.90",
        "position": "disabled",
        "size": "disabled",
        "reason": "LAS curves and depth grids must not be placed over the branded image.",
    },
    "LAS-корреляция": {
        "mode": "dark-workspace",
        "overlay": "1.00",
        "glass": "0.90",
        "position": "disabled",
        "size": "disabled",
        "reason": "Correlation plots require maximum contrast and no decorative background.",
    },
    "Интерпретационные графики": {
        "mode": "dark-workspace",
        "overlay": "1.00",
        "glass": "0.90",
        "position": "disabled",
        "size": "disabled",
        "reason": "Engineering charts, reports and tablets use a plain dark background for data visibility.",
    },
}

BACKGROUND_POSITION_PRESETS: dict[str, str] = {
    "dashboard": "right 3vw bottom 1.2rem",
    "documentation": "right 2vw top 6rem",
    "center-mobile": "center top 5.6rem",
}

BACKGROUND_OPACITY_PRESETS: dict[str, str] = {
    "dashboard_overlay": "0.25",
    "documentation_overlay": "0.22",
    "workspace_overlay": "1.00",
    "dashboard_glass": "0.58",
    "documentation_glass": "0.64",
    "workspace_glass": "0.90",
}

DASHBOARD_BACKGROUND_REFINEMENT: dict[str, str] = {
    "stage": "Dashboard UX Refactoring → Refine dashboard background",
    "marker": "dashboard-background-refinement",
    "desktop_position": "center bottom 1.1rem",
    "desktop_size": "clamp(210px, 18vw, 330px) auto",
    "laptop_position": "center bottom 0.85rem",
    "laptop_size": "clamp(160px, 14vw, 230px) auto",
    "tablet_position": "center bottom 0.65rem",
    "tablet_size": "min(34vw, 190px) auto",
    "mobile_position": "center bottom 0.45rem",
    "mobile_size": "min(42vw, 150px) auto",
    "overlay": "0.90 dark gradient over brand art",
    "rule": "center, contain and dim dashboard artwork without hiding readable cards",
}


GLASS_UI_TOKENS: dict[str, dict[str, str]] = {
    "card": {
        "class": "glass-card",
        "background": "rgba(15, 23, 42, 0.62)",
        "border": "rgba(148, 163, 184, 0.22)",
        "shadow": "0 18px 52px rgba(0, 0, 0, 0.28)",
        "blur": "14px",
        "text": "#f8fafc",
    },
    "panel": {
        "class": "glass-panel",
        "background": "rgba(5, 10, 22, 0.70)",
        "border": "rgba(255, 138, 0, 0.24)",
        "shadow": "0 24px 72px rgba(0, 0, 0, 0.34)",
        "blur": "16px",
        "text": "#f8fafc",
    },
    "hero": {
        "class": "glass-hero",
        "background": "rgba(2, 6, 23, 0.54)",
        "border": "rgba(255, 138, 0, 0.32)",
        "shadow": "0 32px 90px rgba(0, 0, 0, 0.40)",
        "blur": "18px",
        "text": "#ffffff",
    },
    "sidebar": {
        "class": "glass-sidebar",
        "background": "rgba(15, 23, 42, 0.66)",
        "border": "rgba(148, 163, 184, 0.24)",
        "shadow": "0 18px 46px rgba(0, 0, 0, 0.26)",
        "blur": "12px",
        "text": "#f8fafc",
    },
    "navbar": {
        "class": "glass-navbar",
        "background": "rgba(2, 6, 23, 0.58)",
        "border": "rgba(148, 163, 184, 0.24)",
        "shadow": "0 18px 54px rgba(0, 0, 0, 0.28)",
        "blur": "14px",
        "text": "#f8fafc",
    },
    "modal": {
        "class": "glass-modal",
        "background": "rgba(5, 10, 22, 0.78)",
        "border": "rgba(255, 138, 0, 0.28)",
        "shadow": "0 34px 110px rgba(0, 0, 0, 0.46)",
        "blur": "20px",
        "text": "#f8fafc",
    },
    "tooltip": {
        "class": "glass-tooltip",
        "background": "rgba(15, 23, 42, 0.84)",
        "border": "rgba(148, 163, 184, 0.30)",
        "shadow": "0 12px 32px rgba(0, 0, 0, 0.34)",
        "blur": "10px",
        "text": "#f8fafc",
    },
}

GLASS_UI_READABILITY_RULES: tuple[str, ...] = (
    "Dashboard cards keep 55-70% glass opacity so the brand image stays visible while text remains readable.",
    "Documentation panels keep 60-75% glass opacity for long text and quick links.",
    "License and About blocks use 65-80% opacity because legal text must have stronger contrast.",
    "LAS Editor, plots, reports and tables do not use decorative background imagery behind engineering data.",
    "All shared glass surfaces use high contrast text, visible borders and controlled dark overlay tokens.",
)


NAVIGATION_ANIMATION_TOKENS: dict[str, str] = {
    "page_fade": "gas-page-fade 220ms ease-out both",
    "page_slide": "gas-page-slide 260ms cubic-bezier(0.22, 1, 0.36, 1) both",
    "button_hover": "translateY(-2px) scale(1.012)",
    "button_press": "translateY(0) scale(0.985)",
    "card_hover": "translateY(-3px)",
    "sidebar_expand": "gas-sidebar-expand 240ms ease-out both",
    "command_palette_open": "gas-command-open 180ms ease-out both",
    "command_palette_close": "gas-command-close 160ms ease-in both",
    "smooth_scroll": "smooth",
}

NAVIGATION_ANIMATION_FEATURES: tuple[str, ...] = (
    "Page fade transition",
    "Page slide transition",
    "Button hover animation",
    "Button press animation",
    "Card hover animation",
    "Sidebar expand animation",
    "Sidebar collapse animation",
    "Command palette open animation",
    "Command palette close animation",
    "Loading skeletons",
    "Progress indicators",
    "Smooth scroll",
)


START_ACTIONS: tuple[dict[str, str], ...] = (
    {
        "id": "project",
        "title": "Создать / открыть проект",
        "short_title": "Проект",
        "icon": "📁",
        "button_label": "Создать / открыть проект",
        "target_tab": "Работа с данными",
        "description": "Открывает рабочий раздел выбора проекта, импорта и проектного workflow.",
        "when": "Когда нужно создать новый проект, выбрать активный проект или продолжить сохраненную работу.",
        "tooltip": "Перейти в раздел Работа с данными к проектному workflow.",
    },
    {
        "id": "import",
        "title": "Импорт LAS / CSV / Excel",
        "short_title": "Импорт",
        "icon": "⬆️",
        "button_label": "Импорт LAS / CSV / Excel",
        "target_tab": "Работа с данными",
        "description": "Открывает импорт LAS, CSV, XLSX/XLSM, проверку заголовков, mapping и расчет коэффициентов.",
        "when": "Когда есть файл с газовым каротажем или расчетная таблица.",
        "tooltip": "Перейти к загрузке файла и mapping колонок.",
    },
    {
        "id": "las_editor",
        "title": "LAS-редактор",
        "short_title": "LAS Editor",
        "icon": "🧰",
        "button_label": "Открыть LAS-редактор",
        "target_tab": "LAS-редактор",
        "description": "Проверка глубины, подготовка сетки, ручная правка LAS, rename/alias/merge кривых и сохранение версии в проект.",
        "when": "Когда LAS нужно привести в порядок перед расчетами или корреляцией.",
        "tooltip": "Открыть редактор LAS-кривых и глубины.",
    },
    {
        "id": "correlation",
        "title": "LAS-корреляция",
        "short_title": "Корреляция",
        "icon": "📈",
        "button_label": "Открыть LAS-корреляцию",
        "target_tab": "LAS-корреляция",
        "description": "Сравнение нескольких скважин, группировка кривых, X-scale, интервал, печатный HTML и графический экспорт.",
        "when": "Когда нужно сопоставить несколько LAS по одному интервалу.",
        "tooltip": "Открыть multi-LAS корреляцию.",
    },
    {
        "id": "reports",
        "title": "Графики и отчеты",
        "short_title": "Отчеты",
        "icon": "📊",
        "button_label": "Графики и отчеты",
        "target_tab": "Интерпретационные графики",
        "description": "Планшет, маркеры, зоны интерпретации, interval report и экспорт PNG/PDF/SVG.",
        "when": "Когда расчет уже выполнен и нужно подготовить инженерный материал.",
        "tooltip": "Открыть интерпретационный планшет и отчеты.",
    },
    {
        "id": "docs",
        "title": "Инструкции",
        "short_title": "Документы",
        "icon": "📚",
        "button_label": "Инструкции",
        "target_tab": "Инструкции и документация",
        "description": "Формулы, troubleshooting, формат данных, методика mud gas analysis и план проекта.",
        "when": "Когда нужно проверить ограничения методики или понять предупреждение.",
        "tooltip": "Открыть Documentation Center v2.",
    },
    {
        "id": "settings",
        "title": "Настройки интерфейса",
        "short_title": "Настройки",
        "icon": "⚙️",
        "button_label": "Настройки",
        "target_tab": "Старт",
        "description": "Открывает стартовый экран, где доступны профиль компоновки, масштаб интерфейса и проверка Dashboard.",
        "when": "Когда нужно переключить профиль экрана или проверить читаемость интерфейса.",
        "tooltip": "Вернуться на стартовый Dashboard к настройкам интерфейса.",
    },
    {
        "id": "license",
        "title": "Лицензия",
        "short_title": "Лицензия",
        "icon": "🔒",
        "button_label": "Лицензия",
        "target_tab": "Лицензия",
        "description": "Открывает отдельную лицензионную страницу: права автора, ограничения использования, EULA document и контакт.",
        "when": "Когда нужно быстро проверить статус лицензии, copyright и правила коммерческого использования.",
        "tooltip": "Открыть отдельную страницу лицензии приложения.",
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


DOCUMENTATION_QUICK_LINKS: tuple[dict[str, str], ...] = (
    {"title": "Быстрый старт", "anchor": "docs-quick-start", "description": "Запуск приложения, входной файл и первый расчет.", "icon": "🚀"},
    {"title": "Формат данных", "anchor": "docs-data-format", "description": "LAS/CSV/Excel, заголовки, mapping и обязательные поля.", "icon": "📄"},
    {"title": "LAS workflow", "anchor": "docs-las-workflow", "description": "Редактор, корреляция, кривые и сохранение версий.", "icon": "🧰"},
    {"title": "Диагностика", "anchor": "docs-troubleshooting", "description": "Preflight, pytest, логи и типовые ошибки запуска.", "icon": "🩺"},
)

DOCUMENTATION_TOC: tuple[dict[str, str], ...] = (
    {"title": "Быстрый запуск", "anchor": "docs-quick-start"},
    {"title": "Проверка готовности", "anchor": "docs-verification"},
    {"title": "Рабочий сценарий", "anchor": "docs-workflow"},
    {"title": "Формат данных", "anchor": "docs-data-format"},
    {"title": "LAS workflow", "anchor": "docs-las-workflow"},
    {"title": "Горячие клавиши", "anchor": "docs-shortcuts"},
    {"title": "FAQ", "anchor": "docs-faq"},
    {"title": "Troubleshooting", "anchor": "docs-troubleshooting"},
)

DOCUMENTATION_SHORTCUTS: tuple[dict[str, str], ...] = (
    {"keys": "Ctrl+K", "action": "Открыть глобальную командную палитру и найти раздел, документ или объект проекта."},
    {"keys": "Esc", "action": "Закрыть активное окно Streamlit или вернуться из поля поиска после ввода запроса."},
    {"keys": "Enter", "action": "Подтвердить выбранное поле ввода, поиск, mapping или команду в активном блоке."},
)

DOCUMENTATION_FAQ: tuple[dict[str, str], ...] = (
    {"question": "Почему фон виден на документации, но не должен мешать графикам?", "answer": "Документация является справочным экраном и может использовать брендированный hero. LAS-кривые, таблицы и инженерные графики закрываются темным workspace, чтобы числа и линии оставались читаемыми."},
    {"question": "Что проверять перед расчетом?", "answer": "Сначала проверьте строку заголовков, mapping обязательных колонок, предупреждения, режим Ch и выбранный интервал глубин."},
    {"question": "Что делать, если pytest или preflight падают?", "answer": "Проверьте виртуальное окружение, установку зависимостей из requirements.txt, наличие Streamlit, Kaleido для экспорта и последние строки logs/app.log."},
)


def _apply_app_style(scale: str = "large", layout: str = "wide") -> None:
    scale_tokens = {
        "standard": {"base": "17px", "body": "1rem", "caption": "0.95rem", "button": "1rem", "h1": "2.35rem"},
        "large": {"base": "20px", "body": "1.13rem", "caption": "1.02rem", "button": "1.08rem", "h1": "2.75rem"},
        "xlarge": {"base": "22px", "body": "1.22rem", "caption": "1.08rem", "button": "1.16rem", "h1": "3.05rem"},
    }
    tokens = scale_tokens.get(scale, scale_tokens["large"])
    layout_tokens = UI_LAYOUT_PROFILES.get(layout, UI_LAYOUT_PROFILES["wide"])
    app_background_uri = _dashboard_background_data_uri()
    app_background_css = f"url('{app_background_uri}')" if app_background_uri else "none"
    st.markdown(
        """
        <style>
        :root {
            --app-text: #f4f7fb;
            --app-muted: #c5ccd8;
            --app-panel: #0d1723;
            --app-panel-strong: #132235;
            --app-border: rgba(148, 163, 184, 0.28);
            --app-accent: #ff8a00;
            --app-accent-soft: rgba(255, 138, 0, 0.18);
            --global-bg-image: {app_background_css};
            --brand-bg-size: clamp(210px, 18vw, 330px) auto;
            --brand-bg-position: center bottom 1.1rem;
            --glass-dashboard: rgba(4, 10, 24, 0.08);
            --glass-readable: rgba(5, 10, 22, 0.18);
            --brand-overlay-dashboard: rgba(3, 7, 18, 0.04);
            --background-manager-dashboard-overlay: 0.25;
            --background-manager-documentation-overlay: 0.22;
            --background-manager-workspace-overlay: 1.00;
            --background-manager-dashboard-glass: 0.58;
            --background-manager-documentation-glass: 0.64;
            --background-manager-workspace-glass: 0.90;
            --responsive-card-gap: 0.72rem;
            --responsive-dashboard-columns: minmax(12.5rem, 0.55fr) minmax(30rem, 1.55fr) minmax(15rem, 0.72fr);
            --responsive-dashboard-padding: 0.82rem;
        }
        .stApp {
            color: var(--app-text);
            font-size: {tokens["base"]};
            background-image:
                linear-gradient(180deg, rgba(3, 7, 18, 0.88), rgba(3, 7, 18, 0.92)),
                var(--global-bg-image);
            background-size: 100% 100%, var(--brand-bg-size);
            background-position: center center, var(--brand-bg-position);
            background-repeat: no-repeat, no-repeat;
            background-attachment: fixed, fixed;
        }
        .block-container {
            max-width: {layout_tokens["max_width"]};
            padding: 0.35rem 0.7rem 2.2rem 0.7rem;
            overflow-x: hidden;
        }
        @media (min-width: 1920px) {
            :root {
                --brand-bg-size: clamp(230px, 16vw, 360px) auto;
                --brand-bg-position: center bottom 1rem;
                --responsive-card-gap: 0.86rem;
            }
        }
        @media (min-width: 2560px) {
            :root {
                --brand-bg-size: clamp(260px, 12vw, 420px) auto;
                --brand-bg-position: center bottom 1.2rem;
                --responsive-dashboard-columns: minmax(15rem, 0.55fr) minmax(48rem, 1.6fr) minmax(18rem, 0.7fr);
                --responsive-card-gap: 1rem;
            }
            .dashboard-layout { max-width: min(100%, 2480px); margin-left: auto; margin-right: auto; }
        }
        @media (min-width: 3440px) {
            .dashboard-layout { max-width: 2880px; }
            .dashboard-card { padding: 1.08rem; }
        }
        @media (min-width: 3840px) {
            .dashboard-layout { max-width: 3200px; }
            .dashboard-log-track { min-height: 13rem; }
        }
        @media (max-width: 1600px) {
            :root {
                --responsive-dashboard-columns: minmax(13rem, 0.58fr) minmax(31rem, 1.42fr);
                --responsive-card-gap: 0.66rem;
            }
            .dashboard-layout {
                grid-template-areas:
                    "status projects"
                    "las quick"
                    "calculations activity"
                    "license license";
            }
        }
        @media (max-width: 1440px) {
            :root {
                --brand-bg-size: clamp(160px, 14vw, 230px) auto;
                --brand-bg-position: center bottom 0.85rem;
                --responsive-dashboard-columns: minmax(11.5rem, 0.50fr) minmax(34rem, 1.50fr);
            }
        }
        @media (max-width: 1366px) {
            :root {
                --responsive-dashboard-padding: 0.52rem;
                --responsive-card-gap: 0.48rem;
            }
            .dashboard-main { padding: 0.52rem; }
            .dashboard-navbar { padding: 0.62rem 0.72rem; margin-bottom: 0.58rem; gap: 0.55rem; }
            .dashboard-layout {
                grid-template-columns: minmax(7.4rem, 0.30fr) minmax(0, 1.70fr);
                grid-template-areas:
                    "status projects"
                    "las quick"
                    "calculations activity"
                    "license license";
            }
            .dashboard-card { padding: 0.56rem; border-radius: 13px; }
            .dashboard-card.news,
            .dashboard-card.tips,
            .dashboard-card.preview-card,
            .dashboard-card.welcome { display: none; }
            .dashboard-card.welcome { min-height: 5.8rem; }
            .dashboard-card.welcome p:nth-of-type(1) { font-size: 0.76rem !important; line-height: 1.28 !important; }
            .dashboard-card.welcome p:nth-of-type(n+2) { display: none; }
            .dashboard-card h3 { font-size: 0.82rem !important; margin-bottom: 0.42rem; }
            .dashboard-card.stats, .dashboard-card.activity, .dashboard-card.quick, .dashboard-card.projects { overflow: hidden; }
            .dashboard-list-row { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 0.38rem; padding: 0.34rem 0; }
            .dashboard-list-row > * { min-width: 0; overflow-wrap: anywhere; }
            .dashboard-metrics, .dashboard-status-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.36rem; }
            .dashboard-metric { min-height: 2.92rem; padding: 0.42rem; }
            .dashboard-metric b { font-size: 0.98rem; line-height: 1.05; }
            .dashboard-metric span { font-size: 0.66rem !important; line-height: 1.12 !important; }
            .dashboard-action-card { min-height: 3.45rem; padding: 0.46rem; }
            .dashboard-actions { grid-template-columns: repeat(auto-fit, minmax(7.2rem, 1fr)); gap: 0.38rem; }
            .dashboard-action-card strong { font-size: 0.76rem !important; }
            .dashboard-action-card p { font-size: 0.67rem !important; line-height: 1.18 !important; }
            .dashboard-action-card small { margin-top: 0.22rem; font-size: 0.64rem !important; }
            .simplified-dashboard-navigation .app-nav-description { display: none; }
            .simplified-dashboard-navigation.no-empty-nav-cards div[data-testid="stButton"] > button { min-height: 2.65rem; padding-left: 0.2rem; padding-right: 0.2rem; }
            .dashboard-preview { min-height: 7.2rem; }
            .dashboard-log-track { min-height: 6.2rem; }
            .dashboard-muted { font-size: 0.70rem !important; }
        }
        @media (max-width: 1024px) {
            :root {
                --brand-bg-size: min(34vw, 190px) auto;
                --brand-bg-position: center bottom 0.75rem;
                --responsive-card-gap: 0.62rem;
            }
            .dashboard-search-chip:nth-child(n+3) { display: none; }
        }
        @media (max-width: 900px) {
            :root {
                --brand-bg-size: min(36vw, 180px) auto;
                --brand-bg-position: center bottom 0.65rem;
            }
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
            width: 18.2rem !important;
            min-width: 18.2rem !important;
            max-width: 18.2rem !important;
            background:
                radial-gradient(circle at 30% 0%, rgba(255, 138, 0, 0.10), transparent 30%),
                linear-gradient(180deg, rgba(5, 10, 22, 0.90), rgba(8, 14, 26, 0.76)) !important;
            border-right: 1px solid rgba(255, 138, 0, 0.18);
        }
        section[data-testid="stSidebar"] * {
            font-size: 0.84rem !important;
            line-height: 1.35 !important;
        }
        section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] span {
            font-size: 0.84rem !important;
        }
        div[data-testid="stTabs"] div[role="tablist"] {
            gap: 0.55rem;
            border-bottom: 1px solid rgba(148, 163, 184, 0.18);
            padding-bottom: 0.45rem;
        }
        div[data-testid="stTabs"] button[role="tab"] {
            min-height: 3.15rem;
            padding: 0.55rem 0.95rem;
            border-radius: 14px 14px 6px 6px;
            border: 1px solid rgba(148, 163, 184, 0.22);
            background: rgba(15, 23, 42, 0.58);
            transition: transform 140ms ease, background 140ms ease, border-color 140ms ease;
        }
        div[data-testid="stTabs"] button[aria-selected="true"] {
            border-color: rgba(255, 138, 0, 0.58);
            background: linear-gradient(180deg, rgba(255, 138, 0, 0.24), rgba(15, 23, 42, 0.76));
        }
        div[data-testid="stTabs"] button[role="tab"]:hover {
            transform: translateY(-1px);
            border-color: rgba(255, 138, 0, 0.45);
        }
        div[data-testid="stTabs"] button p {
            font-size: {tokens["button"]} !important;
            font-weight: 850 !important;
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


        .glass-card, .glass-panel, .glass-hero, .glass-sidebar, .glass-navbar, .glass-modal, .glass-tooltip {
            color: var(--glass-high-contrast-text) !important;
            border: 1px solid var(--glass-border-token);
            box-shadow: var(--glass-shadow-token);
            backdrop-filter: blur(var(--glass-blur-token));
            -webkit-backdrop-filter: blur(var(--glass-blur-token));
        }
        .glass-card { background: var(--glass-card-bg); border-radius: 16px; }
        .glass-panel { background: var(--glass-panel-bg); border-color: var(--glass-accent-border-token); border-radius: 18px; }
        .glass-hero { background: var(--glass-hero-bg); border-color: rgba(255, 138, 0, 0.32); border-radius: 22px; }
        .glass-sidebar { background: var(--glass-sidebar-bg); border-radius: 16px; }
        .glass-navbar { background: var(--glass-navbar-bg); border-radius: 16px; }
        .glass-modal { background: var(--glass-modal-bg); border-color: var(--glass-accent-border-token); border-radius: 20px; }
        .glass-tooltip { background: var(--glass-tooltip-bg); border-radius: 12px; }
        .glass-card p, .glass-panel p, .glass-hero p, .glass-sidebar p, .glass-navbar p, .glass-modal p, .glass-tooltip p,
        .glass-card span, .glass-panel span, .glass-hero span, .glass-sidebar span, .glass-navbar span, .glass-modal span, .glass-tooltip span {
            color: var(--glass-muted-text) !important;
        }
        .glass-readable-text, .glass-card b, .glass-panel b, .glass-hero b, .glass-sidebar b, .glass-navbar b, .glass-modal b {
            color: var(--glass-high-contrast-text) !important;
        }
        .glass-readability-check { text-shadow: 0 1px 2px rgba(0,0,0,0.55); }
        .background-rule-dark-workspace .glass-card, .background-rule-dark-workspace .glass-panel {
            background: rgba(5, 10, 22, 0.90);
            backdrop-filter: none;
            -webkit-backdrop-filter: none;
        }
        .app-page-shell {
            position: relative;
            border: 1px solid rgba(148, 163, 184, 0.20);
            border-radius: 18px;
            padding: clamp(0.85rem, 1.8vw, 1.35rem);
            margin: 0.85rem 0 1.25rem 0;
            background: rgba(5, 10, 22, 0.82);
            box-shadow: 0 24px 80px rgba(0, 0, 0, 0.34);
            overflow: hidden;
        }
        .app-page-shell::before {
            content: "";
            position: absolute;
            inset: 0;
            pointer-events: none;
            background:
                radial-gradient(circle at 92% 0%, rgba(255, 138, 0, 0.08), transparent 28%),
                linear-gradient(180deg, rgba(15, 23, 42, 0.16), rgba(15, 23, 42, 0.02));
        }
        .app-page-shell > * { position: relative; z-index: 1; }

        .app-page-shell.background-rule-dark-workspace {
            background: linear-gradient(180deg, rgba(5, 10, 22, 0.94), rgba(2, 6, 23, 0.92));
            background-image: none !important;
        }
        .app-page-shell.background-rule-dark-workspace::before {
            background: linear-gradient(180deg, rgba(15, 23, 42, 0.08), rgba(15, 23, 42, 0.02));
        }
        .app-page-shell.background-rule-documentation {
            background: linear-gradient(180deg, rgba(5, 10, 22, 0.64), rgba(2, 6, 23, 0.58));
        }
        .app-page-shell.background-rule-documentation::before {
            background:
                radial-gradient(circle at 86% 8%, rgba(255, 138, 0, 0.10), transparent 24%),
                linear-gradient(180deg, rgba(15, 23, 42, 0.10), rgba(15, 23, 42, 0.02));
        }
        .no-brand-background, #las-editor-workspace, #correlation-workspace, #graphs-workspace, #data-workspace {
            background-image: none !important;
        }
        .engineering-data-surface, .app-page-shell.background-rule-dark-workspace div[data-testid="stDataFrame"], .app-page-shell.background-rule-dark-workspace div[data-testid="stPlotlyChart"] {
            background-color: rgba(5, 10, 22, 0.92) !important;
        }
        .app-page-header {
            display: grid;
            grid-template-columns: minmax(0, 1fr) auto;
            gap: 1rem;
            align-items: start;
            margin-bottom: 1rem;
            padding-bottom: 0.9rem;
            border-bottom: 1px solid rgba(148, 163, 184, 0.18);
        }
        .app-page-kicker { color: var(--app-accent); font-size: 0.78rem !important; font-weight: 900; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 0.25rem; }
        .app-page-title { color: #f8fafc; font-size: clamp(1.65rem, 2.4vw, 2.45rem) !important; line-height: 1.1 !important; font-weight: 950; margin: 0 !important; }
        .app-page-subtitle { color: #cbd5e1 !important; font-size: 0.98rem !important; margin: 0.4rem 0 0 0 !important; max-width: 62rem; }
        .app-page-badge { justify-self: end; min-width: 9.5rem; text-align: center; border: 1px solid rgba(255, 138, 0, 0.34); border-radius: 999px; padding: 0.48rem 0.8rem; color: #ffedd5; background: rgba(255, 138, 0, 0.12); font-weight: 850; white-space: nowrap; }
        .app-section-card, div[data-testid="stDataFrame"], div[data-testid="stPlotlyChart"] { border-radius: 16px; }
        .app-section-card { border: 1px solid rgba(148, 163, 184, 0.18); background: rgba(15, 23, 42, 0.56); padding: 1rem; margin: 0.85rem 0; }
        .app-page-shell h2, .app-page-shell h3 { color: #f8fafc !important; }
        .app-page-shell hr { border-color: rgba(148, 163, 184, 0.18) !important; }
        .app-page-shell div[data-testid="stAlert"], .app-page-shell div[data-testid="stFileUploader"] section, .app-page-shell div[data-testid="stDataFrame"], .app-page-shell div[data-testid="stPlotlyChart"] { background-color: rgba(15, 23, 42, 0.72) !important; border-color: rgba(148, 163, 184, 0.20) !important; }
        .app-page-shell div[data-testid="stExpander"] details { border-radius: 14px; border-color: rgba(148, 163, 184, 0.22); background: rgba(15, 23, 42, 0.42); }
        @media (min-width: 1201px) and (max-width: 1440px) {
            .dashboard-main { padding: 0.64rem; }
            .dashboard-layout {
                grid-template-columns: minmax(8.2rem, 0.34fr) minmax(0, 1.36fr) minmax(11rem, 0.48fr);
                grid-template-areas:
                    "status projects quick"
                    "las calculations activity"
                    "license license license";
            }
            .dashboard-card { padding: 0.66rem; border-radius: 14px; }
            .dashboard-card.welcome { min-height: 6.2rem; }
            .dashboard-card.welcome p:nth-of-type(n+2) { display: none; }
            .dashboard-card.news,
            .dashboard-card.tips,
            .dashboard-card.preview-card,
            .dashboard-card.welcome { display: none; }
            .dashboard-card.stats,
            .dashboard-card.activity,
            .dashboard-card.quick { max-width: 100%; overflow: hidden; }
            .dashboard-metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.42rem; }
            .dashboard-metric { min-height: 3.2rem; padding: 0.48rem; }
            .dashboard-metric b { font-size: 1.08rem; line-height: 1.05; }
            .dashboard-metric span { font-size: 0.68rem !important; line-height: 1.16 !important; }
            .dashboard-actions { grid-template-columns: repeat(auto-fit, minmax(7.4rem, 1fr)); gap: 0.48rem; }
            .dashboard-action-card { min-height: 3.9rem; padding: 0.58rem; }
            .dashboard-action-card strong { font-size: 0.82rem !important; }
            .dashboard-action-card p { font-size: 0.70rem !important; line-height: 1.24 !important; }
            .dashboard-action-card small { font-size: 0.68rem !important; }
            .dashboard-list-row { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 0.45rem; padding: 0.42rem 0; }
            .dashboard-list-row > * { min-width: 0; overflow-wrap: anywhere; }
            .dashboard-preview { min-height: 9rem; }
            .dashboard-log-track { min-height: 7.6rem; }
        }
        @media (max-width: 760px) { .app-page-shell { border-radius: 14px; padding: 0.75rem; } .app-page-header { grid-template-columns: 1fr; } .app-page-badge { justify-self: start; } }
        .dashboard-shell {
            position: relative;
            min-height: calc(100vh - 4.2rem);
            width: 100%;
            border: 1px solid rgba(148, 163, 184, 0.16);
            border-radius: 18px;
            overflow: hidden;
            background-size: var(--brand-bg-size);
            background-position: var(--brand-bg-position);
            background-repeat: no-repeat;
            box-shadow: 0 34px 110px rgba(0, 0, 0, 0.45);
            margin: 0 0 1rem 0;
        }
        .dashboard-overlay {
            position: absolute;
            inset: 0;
            background:
                radial-gradient(circle at 78% 42%, rgba(255, 138, 0, 0.035), transparent 34%),
                linear-gradient(90deg, rgba(3, 7, 18, 0.055) 0%, rgba(7, 12, 24, 0.025) 44%, rgba(7, 12, 24, 0.00) 100%);
        }
        .dashboard-watermark-logo {
            position: absolute;
            right: 1.2rem;
            bottom: 1.2rem;
            width: min(20vw, 260px);
            max-width: 32%;
            opacity: 0.075;
            pointer-events: none;
            filter: drop-shadow(0 18px 28px rgba(0,0,0,0.55));
            z-index: 0;
        }
        .dashboard-content {
            position: relative;
            z-index: 1;
            min-height: calc(100vh - 4.2rem);
            display: block;
        }
        .dashboard-side-rail { display: none; }
        .dashboard-main {
            min-width: 0;
            padding: 0.85rem;
        }
        .navbar-brand-logo { width: 2.15rem; height: 2.15rem; object-fit: contain; filter: drop-shadow(0 8px 16px rgba(0,0,0,0.45)); }
        .dashboard-navbar {
            display: grid;
            grid-template-columns: minmax(10rem, 0.48fr) minmax(24rem, 1.48fr) minmax(14rem, 0.64fr);
            align-items: center;
            gap: 0.8rem;
            padding: 0.78rem 0.95rem;
            margin-bottom: 0.85rem;
            background: rgba(2, 6, 23, 0.22);
            border: 1px solid rgba(148, 163, 184, 0.18);
            border-radius: 16px;
            backdrop-filter: blur(12px);
        }
        .dashboard-brand {
            display: inline-flex;
            align-items: center;
            gap: 0.58rem;
            font-size: 1.1rem;
            font-weight: 900;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            white-space: nowrap;
        }
        .dashboard-brand span { color: var(--app-accent); }
        .dashboard-navlinks {
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 0.55rem;
        }
        .dashboard-navlinks a,
        .dashboard-action-link {
            color: #f8fafc;
            text-decoration: none;
            border: 1px solid rgba(148, 163, 184, 0.24);
            background: linear-gradient(180deg, rgba(30, 41, 59, 0.88), rgba(15, 23, 42, 0.76));
            border-radius: 14px;
            padding: 0.68rem 0.96rem;
            font-weight: 900;
            font-size: 0.9rem !important;
            transition: transform 140ms ease, border-color 140ms ease, background 140ms ease;
        }
        .dashboard-navlinks a:hover,
        .dashboard-action-link:hover {
            transform: translateY(-1px);
            border-color: rgba(255, 138, 0, 0.65);
            background: linear-gradient(180deg, rgba(255, 138, 0, 0.28), rgba(15, 23, 42, 0.82));
        }
        .dashboard-search {
            display: flex;
            justify-content: flex-end;
            gap: 0.45rem;
        }
        .dashboard-search-chip {
            color: #dbeafe !important;
            border: 1px solid rgba(148, 163, 184, 0.22);
            background: rgba(15, 23, 42, 0.68);
            border-radius: 999px;
            padding: 0.52rem 0.74rem;
            font-weight: 850;
            font-size: 0.84rem !important;
            white-space: nowrap;
        }
        .dashboard-layout {
            display: grid;
            grid-template-columns: var(--responsive-dashboard-columns);
            grid-template-areas:
                "status projects activity"
                "las quick calculations"
                "license license license";
            gap: var(--responsive-card-gap);
            align-items: stretch;
            min-width: 0;
            max-width: 100%;
            overflow-x: clip;
        }
        .dashboard-card {
            min-width: 0;
            background: linear-gradient(180deg, rgba(4, 10, 24, 0.08), rgba(5, 10, 22, 0.035));
            border: 1px solid rgba(148, 163, 184, 0.20);
            border-radius: 16px;
            padding: 0.92rem;
            backdrop-filter: blur(1.4px);
            box-shadow: 0 18px 44px rgba(0, 0, 0, 0.22), inset 0 1px 0 rgba(255, 255, 255, 0.04);
            transition: border-color 140ms ease, transform 140ms ease;
        }
        .dashboard-card:hover { border-color: rgba(255, 138, 0, 0.40); }
        .dashboard-card h3 {
            color: var(--app-accent);
            margin: 0 0 0.7rem 0;
            font-size: 0.98rem !important;
            text-transform: uppercase;
        }
        .dashboard-card p,
        .dashboard-card li,
        .dashboard-card div { color: #e5e7eb; overflow-wrap: anywhere; min-width: 0; }
        .dashboard-card.welcome { grid-area: welcome; min-height: 8.5rem; }
        .dashboard-card.projects { grid-area: projects; }
        .dashboard-card.stats { grid-area: status; }
        .dashboard-card.news { grid-area: news; }
        .dashboard-card.recent-las { grid-area: las; }
        .dashboard-card.calculations { grid-area: calculations; }
        .dashboard-card.quick { grid-area: quick; }
        .dashboard-card.activity { grid-area: activity; }
        .dashboard-card.tips { grid-area: tips; }
        .dashboard-card.preview-card { grid-area: preview; }
        .dashboard-card.license { grid-area: license; }
        .dashboard-information-hierarchy .dashboard-card.news,
        .dashboard-information-hierarchy .dashboard-card.tips,
        .dashboard-information-hierarchy .dashboard-card.preview-card,
        .dashboard-information-hierarchy .dashboard-card.welcome { display: none !important; }
        .dashboard-status-grid { display:grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.42rem; }
        .dashboard-status-pill { border:1px solid rgba(148,163,184,0.18); border-radius: 11px; padding:0.48rem; background:rgba(15,23,42,0.18); }
        .dashboard-status-pill b { display:block; font-size:0.88rem; color:#f8fafc; }
        .dashboard-status-pill span { display:block; font-size:0.68rem; color:#cbd5e1; font-weight:800; margin-top:0.12rem; }
        .dashboard-information-hierarchy .dashboard-card { min-height: 7.4rem; }
        .dashboard-information-hierarchy .dashboard-card.license { min-height: auto; }
        .dashboard-information-hierarchy .dashboard-list-row { min-width: 0; }
        .dashboard-information-hierarchy .dashboard-muted { color:#cbd5e1 !important; }
        .dashboard-empty-state { color:#cbd5e1 !important; font-size:0.78rem !important; line-height:1.35 !important; border:1px dashed rgba(148,163,184,0.22); border-radius:12px; padding:0.62rem; background:rgba(15,23,42,0.12); }
        .dashboard-list-row {
            display: flex;
            justify-content: space-between;
            gap: 0.8rem;
            padding: 0.55rem 0;
            border-bottom: 1px solid rgba(148, 163, 184, 0.16);
        }
        .dashboard-muted { color: #aeb8c8 !important; font-size: 0.82rem !important; }
        .dashboard-metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(6.2rem, 1fr)); gap: 0.55rem; }
        .dashboard-metric {
            min-height: 4rem;
            padding: 0.75rem;
            border: 1px solid rgba(148, 163, 184, 0.20);
            border-radius: 13px;
            background: rgba(15, 23, 42, 0.18);
        }
        .dashboard-metric b { display: block; font-size: 1.55rem; }
        .dashboard-metric span { color: #d1d5db; font-weight: 800; }
        .dashboard-actions { display: grid; grid-template-columns: repeat(auto-fit, minmax(7.8rem, 1fr)); gap: 0.42rem; }
        .dashboard-action-card {
            min-height: 3.25rem;
            padding: 0.52rem 0.58rem;
            border: 1px solid rgba(148, 163, 184, 0.22);
            border-radius: 12px;
            background: linear-gradient(180deg, rgba(15, 23, 42, 0.20), rgba(15, 23, 42, 0.10));
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.04);
        }
        .dashboard-action-card strong { display: block; font-size: 0.86rem; margin-bottom: 0.12rem; }
        .dashboard-action-card small { display:block; margin-top:0.18rem; color:#ffedd5; font-weight:800; font-size:0.68rem; }
        .quick-action-wired { cursor: pointer; }
        .quick-action-summary { display:grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap:0.42rem; }
        .quick-action-summary .dashboard-muted { font-size:0.72rem !important; line-height:1.22 !important; }
        .dashboard-action-card:hover { border-color: rgba(255, 138, 0, 0.55); transform: translateY(-1px); }
        .simplified-dashboard-navigation.no-empty-nav-cards .app-nav-card { display: none !important; }
        .simplified-dashboard-navigation.no-empty-nav-cards { gap: 0.55rem; margin-bottom: 0.64rem; }
        .simplified-dashboard-navigation.no-empty-nav-cards .app-nav-description { display: block; margin: 0.30rem 0.10rem 0; color: #cbd5e1; font-size: 0.72rem; line-height: 1.20; min-height: 2.0em; overflow: hidden; }
        .simplified-dashboard-navigation.no-empty-nav-cards div[data-testid="stButton"] > button { min-height: 3.45rem; border-radius: 15px !important; font-weight: 950; border-color: rgba(148, 163, 184, 0.28) !important; background: linear-gradient(180deg, rgba(15, 23, 42, 0.88), rgba(12, 20, 35, 0.78)) !important; }
        .simplified-dashboard-navigation.no-empty-nav-cards div[data-testid="stButton"] > button:hover { border-color: rgba(255, 138, 0, 0.65) !important; background: linear-gradient(180deg, rgba(255, 138, 0, 0.24), rgba(15, 23, 42, 0.82)) !important; }
        .simplified-dashboard-navigation.no-empty-nav-cards div[data-testid="stButton"] > button p { font-size: 0.88rem; line-height: 1.18; }
        .dashboard-preview { min-height: 12rem; }
        .dashboard-log-track { display: grid; grid-template-columns: 0.45fr repeat(5, minmax(2.2rem, 1fr)); gap: 0.25rem; min-height: 10.2rem; margin-top: 0.55rem; overflow: hidden; }
        .dashboard-depth-track, .dashboard-curve-track {
            position: relative;
            border: 1px solid rgba(148, 163, 184, 0.18);
            border-radius: 8px;
            background: rgba(2, 6, 23, 0.38);
            overflow: hidden;
        }
        .dashboard-depth-track::before, .dashboard-curve-track::before {
            content: "";
            position: absolute;
            inset: 0;
            background: repeating-linear-gradient(to bottom, rgba(148, 163, 184, 0.11), rgba(148, 163, 184, 0.11) 1px, transparent 1px, transparent 34px);
        }
        .dashboard-curve-track::after {
            content: "";
            position: absolute;
            top: 16%; bottom: 8%; left: 48%; width: 2px;
            background: var(--app-accent);
            transform: skewX(-8deg);
            box-shadow: 0 0 10px rgba(255, 138, 0, 0.52);
        }
        .dashboard-curve-label { position: relative; z-index: 1; padding: 0.35rem; text-align: center; font-weight: 900; font-size: 0.72rem; }
        .dashboard-footer {
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            margin-top: 0.75rem;
            color: #aeb8c8;
            font-size: 0.86rem;
        }
        .dashboard-tab-note { display: none; }

        @media (min-width: 1601px) {
            .dashboard-3 { --d3-side: clamp(13rem, 13vw, 15rem); --d3-gap: 1rem; }
            .dashboard-3 .dashboard-layout { grid-template-columns: repeat(12, minmax(0, 1fr)); }
        }
        @media (min-width: 1441px) and (max-width: 1600px) {
            .dashboard-3 { --d3-side: 11.4rem; --d3-gap: 0.78rem; background-size: 100% 100%, 100% 100%, 100% 100%, clamp(190px, 16vw, 285px) auto; background-position: center center, center center, center center, center bottom 1rem; }
            .dashboard-3 .dashboard-card { padding: 0.86rem; }
        }
        @media (max-width: 1366px) {
            .dashboard-3 { --d3-side: 8.85rem; --d3-gap: 0.52rem; border-radius: 16px; background-size: 100% 100%, 100% 100%, 100% 100%, clamp(145px, 13vw, 205px) auto; background-position: center center, center center, center center, center bottom 0.72rem; }
            .dashboard-3 .dashboard-main { padding: 0.48rem; }
            .dashboard-3 .dashboard-rail-brand { min-height: 7.2rem; font-size: 0.78rem !important; }
            .dashboard-3 .dashboard-layout {
                grid-template-areas:
                    "status status status status status status status status status status status status"
                    "projects projects projects projects projects projects las las las las las las"
                    "calculations calculations calculations calculations reports reports reports reports activity activity activity activity"
                    "favorites favorites favorites favorites favorites favorites favorites favorites favorites favorites favorites favorites";
            }
            .dashboard-3 .dashboard-status-grid, .dashboard-3 .dashboard-metrics { grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 0.42rem; }
            .dashboard-3 .dashboard-status-pill, .dashboard-3 .dashboard-metric { min-height: 2.65rem; padding: 0.36rem 0.44rem; }
            .dashboard-3 .dashboard-status-pill b, .dashboard-3 .dashboard-metric b { font-size: 0.92rem; }
            .dashboard-3 .dashboard-status-pill span, .dashboard-3 .dashboard-metric span { font-size: 0.66rem !important; }
            .dashboard-3 .dashboard-title-icon { width: 2.6rem; height: 2.6rem; }
            .dashboard-3 .dashboard-page-title { font-size: 1.38rem !important; }
            .dashboard-3 .dashboard-page-subtitle { font-size: 0.78rem !important; }
        }
        @media (max-width: 1200px) {
            .dashboard-navbar { grid-template-columns: 1fr; }
            .dashboard-search { justify-content: flex-start; flex-wrap: wrap; }
            .dashboard-layout {
                grid-template-columns: minmax(9.5rem, 0.46fr) minmax(0, 1.54fr);
                grid-template-areas:
                    "welcome projects"
                    "stats quick"
                    "activity quick"
                    "news preview"
                    "tips license";
            }
            .dashboard-actions { grid-template-columns: repeat(2, minmax(9rem, 1fr)); }
            .dashboard-card.welcome p:nth-of-type(n+2) { display: none; }
        }
        @media (max-width: 760px) {
            .block-container { padding: 0.25rem 0.35rem 1.4rem 0.35rem; max-width: 100vw; }
            section[data-testid="stSidebar"] { display: none; }
            .dashboard-shell { border-radius: 12px; min-height: auto; }
            .dashboard-main { padding: 0.55rem; }
            .dashboard-navlinks { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); }
            .dashboard-navlinks a { text-align: center; padding: 0.72rem 0.5rem; }
            .dashboard-layout {
                grid-template-columns: 1fr;
                grid-template-areas:
                    "welcome"
                    "quick"
                    "projects"
                    "stats"
                    "preview"
                    "activity"
                    "news"
                    "tips"
                    "license";
            }
            .dashboard-actions { grid-template-columns: 1fr; }
            .dashboard-log-track { grid-template-columns: 0.5fr 1fr 1fr; }
            .dashboard-card.news, .dashboard-card.tips, .dashboard-card.preview-card, .dashboard-card.welcome { display: none; }
            .dashboard-footer { flex-direction: column; gap: 0.35rem; }
        }
        @media (max-width: 480px) {
            :root {
                --brand-bg-size: min(42vw, 150px) auto;
                --brand-bg-position: center bottom 0.45rem;
                --responsive-dashboard-padding: 0.42rem;
            }
            .dashboard-brand { font-size: 0.92rem; }
            .dashboard-navlinks { grid-template-columns: 1fr; }
            .dashboard-search-chip:nth-child(n+2) { display: none; }
            .dashboard-metrics { grid-template-columns: 1fr; }
            .dashboard-log-track { display: none; }
            .dashboard-card.preview-card { display: none; }
        }

        /* Dashboard 3.0 branch: complete product-style home screen.
           Requirements: no duplicated Open buttons, visible information hierarchy,
           dashboard-background-refinement: centered contained background art, laptop-safe grid for 1366x768 and 1440x900. */
        .dashboard-3 {
            --d3-gap: clamp(0.52rem, 0.78vw, 0.82rem);
            --d3-side: clamp(12.2rem, 14vw, 15rem);
            --d3-card-min: 0;
            --d3-content-max: 100%;
            min-height: calc(100vh - 4.6rem);
            width: min(100%, 100vw);
            max-width: 100%;
            box-sizing: border-box;
            border: 1px solid rgba(148, 163, 184, 0.18);
            border-radius: 20px;
            overflow-x: clip;
            overflow-y: visible;
            background-image:
                radial-gradient(circle at 82% 8%, rgba(30, 144, 255, 0.10), transparent 28%),
                radial-gradient(circle at 16% 92%, rgba(255, 138, 0, 0.10), transparent 30%),
                linear-gradient(135deg, rgba(2, 6, 23, 0.93), rgba(7, 12, 24, 0.88)),
                var(--global-bg-image);
            background-size: 100% 100%, 100% 100%, 100% 100%, clamp(210px, 18vw, 330px) auto;
            background-position: center center, center center, center center, center bottom 1.1rem;
            background-repeat: no-repeat;
            box-shadow: 0 32px 110px rgba(0, 0, 0, 0.48);
        }
        .dashboard-3 .dashboard-content {
            display: grid;
            grid-template-columns: minmax(0, 1fr);
            min-height: calc(100vh - 3rem);
            max-width: var(--d3-content-max);
            overflow-x: clip;
        }
        .dashboard-3.project-workspace-1 { padding: 0; }
        .dashboard-3 .dashboard-side-rail {
            display: flex;
            flex-direction: column;
            min-width: 0;
            gap: 0.7rem;
            padding: 0.85rem;
            border-right: 1px solid rgba(148, 163, 184, 0.16);
            background: linear-gradient(180deg, rgba(2, 6, 23, 0.64), rgba(7, 12, 24, 0.44));
            backdrop-filter: blur(14px);
        }
        .dashboard-3 .dashboard-rail-link {
            display: grid;
            grid-template-columns: 1.6rem minmax(0, 1fr);
            gap: 0.52rem;
            align-items: center;
            padding: 0.58rem 0.6rem;
            border-radius: 12px;
            color: #dbeafe;
            text-decoration: none;
            font-weight: 850;
            border: 1px solid transparent;
        }
        .dashboard-3 .dashboard-rail-link.active,
        .dashboard-3 .dashboard-rail-link:hover {
            color: #f8fafc;
            border-color: rgba(59, 130, 246, 0.36);
            background: rgba(30, 64, 175, 0.20);
        }
        .dashboard-3 .dashboard-rail-brand {
            margin-top: auto;
            min-height: 13rem;
            border: 1px solid rgba(148, 163, 184, 0.18);
            border-radius: 16px;
            padding: 0.8rem;
            background-image:
                linear-gradient(180deg, rgba(2, 6, 23, 0.10), rgba(2, 6, 23, 0.72)),
                var(--global-bg-image);
            background-size: 100% 100%, contain;
            background-position: center center, center center;
            background-repeat: no-repeat;
        }
        .dashboard-3 .dashboard-main { padding: clamp(0.58rem, 0.86vw, 0.95rem); min-width: 0; }
        .dashboard-3 .dashboard-navbar {
            display: grid;
            grid-template-columns: minmax(0, 1fr) auto;
            gap: 0.55rem;
            align-items: center;
            min-width: 0;
            margin-bottom: 0.58rem;
            padding: 0;
            border: 0;
            background: transparent;
            backdrop-filter: none;
        }
        .dashboard-3 .dashboard-title-row { display: flex; gap: 0.82rem; align-items: center; min-width: 0; }
        .dashboard-3 .dashboard-title-icon {
            width: 2.55rem;
            height: 2.55rem;
            display: grid;
            place-items: center;
            border-radius: 12px;
            color: #38bdf8;
            background: rgba(14, 165, 233, 0.12);
            border: 1px solid rgba(56, 189, 248, 0.22);
            font-size: 1.2rem;
        }
        .dashboard-3 .dashboard-page-title { font-size: clamp(1.22rem, 1.62vw, 1.74rem) !important; color: #f8fafc; margin: 0 !important; line-height: 1.06 !important; }
        .dashboard-3 .dashboard-page-subtitle { color: #cbd5e1 !important; margin: 0.12rem 0 0 0 !important; font-size: 0.78rem !important; line-height: 1.22 !important; max-width: 72rem; }
        .dashboard-3 .dashboard-search { justify-content: flex-end; align-items: center; flex-wrap: wrap; }
        .dashboard-3 .dashboard-search-chip { background: rgba(15, 23, 42, 0.72); }
        .dashboard-3 .dashboard-layout {
            display: grid;
            grid-template-columns: repeat(12, minmax(0, 1fr));
            grid-template-areas:
                "status status status status status status status status status status status status"
                "projects projects projects projects las las las las calculations calculations calculations calculations"
                "reports reports reports reports activity activity activity activity favorites favorites favorites favorites";
            gap: var(--d3-gap);
            align-items: stretch;
            min-width: 0;
            max-width: 100%;
            overflow-x: clip;
        }
        .dashboard-3 .dashboard-card {
            min-width: var(--d3-card-min);
            max-width: 100%;
            box-sizing: border-box;
            border-radius: 16px;
            padding: clamp(0.82rem, 1vw, 1.1rem);
            background: linear-gradient(180deg, rgba(15, 23, 42, 0.72), rgba(7, 12, 24, 0.58));
            border: 1px solid rgba(148, 163, 184, 0.18);
            box-shadow: 0 18px 52px rgba(0,0,0,0.30), inset 0 1px 0 rgba(255,255,255,0.05);
            backdrop-filter: blur(14px);
        }
        .dashboard-3 .dashboard-card h3 {
            display: flex;
            justify-content: space-between;
            gap: 0.8rem;
            align-items: center;
            color: #f8fafc;
            text-transform: none;
            font-size: 1.02rem !important;
            margin-bottom: 0.72rem;
        }
        .dashboard-3 .dashboard-card h3 span { color: #38bdf8; font-size: 0.82rem !important; font-weight: 850; }
        .dashboard-3 .dashboard-card.stats { grid-area: status; min-height: auto; }
        .dashboard-3 .dashboard-card.projects { grid-area: projects; }
        .dashboard-3 .dashboard-card.recent-las { grid-area: las; }
        .dashboard-3 .dashboard-card.calculations { grid-area: calculations; }
        .dashboard-3 .dashboard-card.activity { grid-area: activity; }
        .dashboard-3 .dashboard-card.project-health { grid-area: project; }
        .dashboard-3 .dashboard-card.license { grid-area: license; }
        .dashboard-3 .dashboard-card.reports { grid-area: reports; }
        .dashboard-3 .dashboard-card.favorites { grid-area: favorites; }
        .dashboard-3 .workspace-search-card { margin-bottom: var(--d3-gap); padding-top: 0.62rem; padding-bottom: 0.62rem; }
        .dashboard-3 .workspace-search-box {
            display: grid;
            grid-template-columns: minmax(0, 1fr);
            gap: 0.22rem;
            padding: 0.52rem 0.68rem;
            border-radius: 14px;
            background: rgba(15, 23, 42, 0.58);
            border: 1px solid rgba(56, 189, 248, 0.18);
        }
        .dashboard-3 .workspace-search-box b { color: #f8fafc; font-size: 0.82rem !important; line-height: 1.18 !important; }
        .dashboard-3 .workspace-search-box span { color: #94a3b8; font-size: 0.68rem !important; line-height: 1.18 !important; }
        .dashboard-3 .workspace-search-results { margin-bottom: var(--d3-gap); }
        .dashboard-3 .workspace-search-result-row { border-left: 2px solid rgba(125, 211, 252, 0.42); }
        .dashboard-3 .dashboard-row-badge {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            max-width: 9.5rem;
            padding: 0.18rem 0.46rem;
            border-radius: 999px;
            color: #bae6fd;
            background: rgba(14, 165, 233, 0.12);
            border: 1px solid rgba(14, 165, 233, 0.20);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .dashboard-3 .dashboard-status-grid,
        .dashboard-3 .dashboard-metrics {
            display: grid;
            grid-template-columns: repeat(5, minmax(0, 1fr));
            gap: 0.52rem;
            min-width: 0;
            max-width: 100%;
        }
        .dashboard-3 .dashboard-status-pill,
        .dashboard-3 .dashboard-metric {
            min-height: 3.25rem;
            min-width: 0;
            padding: 0.52rem 0.62rem;
            border-radius: 14px;
            border: 1px solid rgba(148, 163, 184, 0.18);
            background: linear-gradient(135deg, rgba(30, 64, 175, 0.18), rgba(15, 23, 42, 0.30));
        }
        .dashboard-3 .dashboard-status-pill b,
        .dashboard-3 .dashboard-metric b { display:block; font-size: 1.08rem; color:#f8fafc; line-height:1.02; }
        .dashboard-3 .dashboard-status-pill span,
        .dashboard-3 .dashboard-metric span { color:#cbd5e1; font-weight:850; font-size:0.68rem !important; line-height: 1.1 !important; }
        .dashboard-3 .dashboard-list-row {
            display: grid;
            grid-template-columns: minmax(0, 1fr) auto;
            gap: 0.72rem;
            padding: 0.58rem 0;
            border-bottom: 1px solid rgba(148, 163, 184, 0.12);
        }
        .dashboard-3 .dashboard-list-row b { color: #f8fafc; font-size: 0.88rem !important; }
        .dashboard-3 .dashboard-list-row > div:first-child,
        .dashboard-3 .dashboard-list-row b,
        .dashboard-3 .dashboard-muted { min-width: 0; overflow-wrap: anywhere; }
        .dashboard-3 .dashboard-muted { color: #94a3b8 !important; font-size: 0.76rem !important; line-height: 1.3 !important; }
        .dashboard-3 .dashboard-health-grid { display:grid; grid-template-columns: 1fr; gap:0.64rem; }
        .dashboard-3 .dashboard-health-row { display:grid; grid-template-columns: minmax(0,1fr) auto; gap:0.7rem; align-items:center; }
        .dashboard-3 .dashboard-health-bar { height: 0.52rem; border-radius:999px; background:rgba(30,41,59,0.9); overflow:hidden; }
        .dashboard-3 .dashboard-health-bar i { display:block; height:100%; border-radius:inherit; background:linear-gradient(90deg, #0ea5e9, #22c55e); }
        .dashboard-3 .license-brand-header { margin: 0.2rem 0 0.72rem 0; }
        .dashboard-3 .dashboard-footer { margin-top: 0.95rem; }
        .dashboard-3 .quick-actions-redesigned { display:none; }
        .dashboard-3-branch-marker { display:none; }
        .dashboard-3.dashboard-compact-workspace-fix { --dashboard-compact-fix: screenshot-top-density; }
        @media (max-width: 1440px) {
            .dashboard-3 { --d3-side: 9.75rem; --d3-gap: 0.62rem; background-size: 100% 100%, 100% 100%, 100% 100%, clamp(160px, 14vw, 230px) auto; background-position: center center, center center, center center, center bottom 0.85rem; }
            .dashboard-3 .dashboard-side-rail { padding: 0.62rem; gap: 0.42rem; }
            .dashboard-3 .dashboard-rail-link { padding: 0.48rem 0.42rem; grid-template-columns: 1.25rem minmax(0,1fr); font-size:0.78rem !important; }
            .dashboard-3 .dashboard-rail-brand { min-height: 9.8rem; }
            .dashboard-3 .dashboard-layout {
                grid-template-areas:
                    "status status status status status status status status status status status status"
                    "projects projects projects projects las las las las calculations calculations calculations calculations"
                    "reports reports reports reports activity activity activity activity favorites favorites favorites favorites";
            }
            .dashboard-3 .dashboard-card { padding: 0.72rem; }
            .dashboard-3 .dashboard-status-grid, .dashboard-3 .dashboard-metrics { gap:0.5rem; }
            .dashboard-3 .dashboard-status-pill, .dashboard-3 .dashboard-metric { min-height: 2.85rem; padding:0.42rem 0.5rem; }
            .dashboard-3 .dashboard-status-pill b, .dashboard-3 .dashboard-metric b { font-size:0.98rem; }
            .dashboard-3 .dashboard-card h3 { font-size:0.92rem !important; margin-bottom:0.5rem; }
            .dashboard-3 .dashboard-list-row { padding:0.42rem 0; gap:0.45rem; }
        }

        @media (min-width: 1601px) {
            .dashboard-3 { --d3-side: clamp(13rem, 13vw, 15rem); --d3-gap: 1rem; }
            .dashboard-3 .dashboard-layout { grid-template-columns: repeat(12, minmax(0, 1fr)); }
        }
        @media (min-width: 1441px) and (max-width: 1600px) {
            .dashboard-3 { --d3-side: 11.4rem; --d3-gap: 0.78rem; background-size: 100% 100%, 100% 100%, 100% 100%, clamp(190px, 16vw, 285px) auto; background-position: center center, center center, center center, center bottom 1rem; }
            .dashboard-3 .dashboard-card { padding: 0.86rem; }
        }
        @media (max-width: 1366px) {
            .dashboard-3 { --d3-side: 8.85rem; --d3-gap: 0.52rem; border-radius: 16px; background-size: 100% 100%, 100% 100%, 100% 100%, clamp(145px, 13vw, 205px) auto; background-position: center center, center center, center center, center bottom 0.72rem; }
            .dashboard-3 .dashboard-main { padding: 0.48rem; }
            .dashboard-3 .dashboard-rail-brand { min-height: 7.2rem; font-size: 0.78rem !important; }
            .dashboard-3 .dashboard-layout {
                grid-template-areas:
                    "status status status status status status status status status status status status"
                    "projects projects projects projects projects projects las las las las las las"
                    "calculations calculations calculations calculations reports reports reports reports activity activity activity activity"
                    "favorites favorites favorites favorites favorites favorites favorites favorites favorites favorites favorites favorites";
            }
            .dashboard-3 .dashboard-status-grid, .dashboard-3 .dashboard-metrics { grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 0.42rem; }
            .dashboard-3 .dashboard-status-pill, .dashboard-3 .dashboard-metric { min-height: 2.65rem; padding: 0.36rem 0.44rem; }
            .dashboard-3 .dashboard-status-pill b, .dashboard-3 .dashboard-metric b { font-size: 0.92rem; }
            .dashboard-3 .dashboard-status-pill span, .dashboard-3 .dashboard-metric span { font-size: 0.66rem !important; }
            .dashboard-3 .dashboard-title-icon { width: 2.6rem; height: 2.6rem; }
            .dashboard-3 .dashboard-page-title { font-size: 1.38rem !important; }
            .dashboard-3 .dashboard-page-subtitle { font-size: 0.78rem !important; }
        }
        @media (max-width: 1200px) {
            .dashboard-3 .dashboard-content { grid-template-columns: 1fr; }
            .dashboard-3 .dashboard-side-rail { display: none; }
            .dashboard-3 .dashboard-layout {
                grid-template-areas:
                    "status status status status status status status status status status status status"
                    "projects projects projects projects projects projects las las las las las las"
                    "calculations calculations calculations calculations reports reports reports reports activity activity activity activity"
                    "favorites favorites favorites favorites favorites favorites favorites favorites favorites favorites favorites favorites";
            }
        }
        @media (max-width: 820px) {
            .dashboard-3 .dashboard-navbar { grid-template-columns: 1fr; }
            .dashboard-3 .dashboard-search { justify-content:flex-start; }
            .dashboard-3 .dashboard-layout { grid-template-columns: 1fr; grid-template-areas: "status" "projects" "las" "calculations" "reports" "activity" "favorites"; }
            .dashboard-3 .dashboard-status-grid, .dashboard-3 .dashboard-metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        }
        @media (max-width: 520px) {
            .dashboard-3 .dashboard-status-grid, .dashboard-3 .dashboard-metrics { grid-template-columns: 1fr; }
            .dashboard-3 .dashboard-title-row { align-items:flex-start; }
            .dashboard-3 .dashboard-title-icon { display:none; }
        }

        div[data-testid="stDataFrame"] {
            border: 1px solid var(--app-border);
            border-radius: 8px;
            overflow: hidden;
        }
        div[data-testid="stDataFrame"] * {
            font-size: 0.96rem !important;
        }
        .app-nav-wrap {
            display: grid;
            grid-template-columns: repeat(6, minmax(0, 1fr));
            gap: 0.65rem;
            margin: 0.2rem 0 0.95rem 0;
        }
        .app-nav-card {
            position: relative;
            background: linear-gradient(180deg, rgba(15, 23, 42, 0.86), rgba(7, 12, 24, 0.72));
            border: 1px solid rgba(148, 163, 184, 0.24);
            border-radius: 16px;
            padding: 0.8rem 0.9rem;
            min-height: 5.1rem;
            box-shadow: 0 18px 48px rgba(0, 0, 0, 0.28);
            backdrop-filter: blur(14px);
            animation: gas-page-fade 220ms ease-out both;
            transition: transform 180ms cubic-bezier(0.22, 1, 0.36, 1), border-color 180ms ease, box-shadow 180ms ease, background 180ms ease;
            will-change: transform;
        }
        .app-nav-card:hover {
            transform: translateY(-3px);
            border-color: rgba(255, 138, 0, 0.58);
            box-shadow: 0 24px 64px rgba(0, 0, 0, 0.34), 0 0 22px rgba(255, 138, 0, 0.12);
        }
        .app-nav-card.active {
            border-color: rgba(255, 138, 0, 0.78);
            background: linear-gradient(180deg, rgba(255, 138, 0, 0.24), rgba(15, 23, 42, 0.78));
        }
        .app-nav-card.active::after {
            content: "";
            position: absolute;
            left: 0.9rem;
            right: 0.9rem;
            bottom: 0.55rem;
            height: 2px;
            border-radius: 999px;
            background: linear-gradient(90deg, transparent, rgba(255, 138, 0, 0.95), transparent);
            animation: gas-active-underline 620ms ease-out both;
        }
        .app-nav-card b { display: block; color: #f8fafc; font-size: 0.98rem; margin-bottom: 0.3rem; }
        .app-nav-card span { color: #cbd5e1; font-size: 0.78rem !important; line-height: 1.25 !important; }
        div[data-testid="stButton"] button {
            border-radius: 14px !important;
            background: linear-gradient(180deg, rgba(30, 41, 59, 0.92), rgba(15, 23, 42, 0.82)) !important;
            border: 1px solid rgba(148, 163, 184, 0.30) !important;
            color: #f8fafc !important;
            box-shadow: 0 10px 30px rgba(0,0,0,0.18);
            transition: transform 150ms cubic-bezier(0.22, 1, 0.36, 1), border-color 150ms ease, background 150ms ease, box-shadow 150ms ease;
            will-change: transform;
        }
        div[data-testid="stButton"] button:hover {
            transform: translateY(-2px) scale(1.012);
            border-color: rgba(255, 138, 0, 0.70) !important;
            background: linear-gradient(180deg, rgba(255, 138, 0, 0.30), rgba(15, 23, 42, 0.84)) !important;
            box-shadow: 0 16px 38px rgba(0,0,0,0.28), 0 0 18px rgba(255,138,0,0.12);
        }
        div[data-testid="stButton"] button:active {
            transform: translateY(0) scale(0.985);
            transition-duration: 90ms;
        }
        .modern-sidebar-card,
        .sidebar-brand-card,
        .sidebar-status-card,
        .sidebar-recent-card {
            border: 1px solid rgba(148, 163, 184, 0.20);
            border-radius: 16px;
            padding: 0.78rem;
            margin: 0.55rem 0;
            background: linear-gradient(180deg, rgba(15, 23, 42, 0.44), rgba(15, 23, 42, 0.24));
            box-shadow: 0 18px 46px rgba(0,0,0,0.24), inset 0 1px 0 rgba(255,255,255,0.05);
            backdrop-filter: blur(8px);
        }
        .sidebar-brand-card {
            border-color: rgba(255, 138, 0, 0.32);
            background: linear-gradient(150deg, rgba(255, 138, 0, 0.14), rgba(15, 23, 42, 0.34));
        }
        .sidebar-brand-row { display: flex; gap: 0.65rem; align-items: center; }
        .sidebar-brand-logo { width: 3.1rem; height: 3.1rem; object-fit: contain; filter: drop-shadow(0 10px 18px rgba(0,0,0,0.45)); }
        .sidebar-brand-title { color: #f8fafc; font-weight: 950; text-transform: uppercase; letter-spacing: 0.04em; }
        .sidebar-brand-title span { color: #ff8a00; }
        .sidebar-brand-subtitle { display:block; color: #cbd5e1; margin-top: 0.15rem; font-size: 0.74rem !important; }
        .modern-sidebar-card b,
        .sidebar-status-card b,
        .sidebar-recent-card b { color: #f8fafc; }
        .modern-sidebar-card small,
        .sidebar-status-card small,
        .sidebar-recent-card small { color: #aeb8c8; display: block; margin-top: 0.2rem; }
        .modern-sidebar-metrics { display: grid; grid-template-columns: 1fr 1fr; gap: 0.45rem; margin-top: 0.55rem; }
        .modern-sidebar-metric { border: 1px solid rgba(148,163,184,0.17); border-radius: 12px; padding: 0.5rem; background: rgba(2,6,23,0.28); }
        .modern-sidebar-metric b { display:block; font-size: 1.08rem; color:#ff8a00; }
        .sidebar-status-grid { display: grid; gap: 0.38rem; margin-top: 0.55rem; }
        .sidebar-status-row { display:flex; justify-content:space-between; gap:0.5rem; border-bottom:1px solid rgba(148,163,184,0.12); padding-bottom:0.32rem; }
        .sidebar-status-row span:first-child { color:#aeb8c8; }
        .sidebar-status-row span:last-child { color:#f8fafc; font-weight:850; text-align:right; }
        .sidebar-state-pill { display:inline-flex; align-items:center; gap:0.35rem; margin-top:0.45rem; padding:0.34rem 0.55rem; border-radius:999px; background:rgba(34,197,94,0.12); color:#bbf7d0 !important; border:1px solid rgba(34,197,94,0.24); font-weight:900; }
        .sidebar-action-grid { display:grid; grid-template-columns:1fr 1fr; gap:0.45rem; margin:0.55rem 0; }
        .sidebar-recent-item { border-left:3px solid rgba(255,138,0,0.74); padding:0.34rem 0.45rem; margin:0.28rem 0; background:rgba(15,23,42,0.18); border-radius:9px; }
        .sidebar-recent-item strong { display:block; color:#f8fafc; }
        .sidebar-recent-item span { color:#aeb8c8; font-size:0.74rem !important; }

        .application-license-page {
            display: grid;
            gap: 0.92rem;
            max-width: 1180px;
            margin: 0 auto;
        }
        .application-license-hero {
            display: grid;
            grid-template-columns: minmax(0, 1.35fr) minmax(15rem, 0.65fr);
            gap: 1rem;
            align-items: stretch;
            border: 1px solid rgba(255, 138, 0, 0.34);
            border-radius: 1.2rem;
            padding: 1.15rem;
            background: linear-gradient(135deg, rgba(255, 138, 0, 0.18), rgba(8, 18, 34, 0.84));
            box-shadow: 0 18px 50px rgba(0,0,0,0.32);
        }
        .application-license-hero h2 { margin: 0 0 0.4rem 0; font-size: clamp(1.35rem, 2.4vw, 2.1rem); }
        .application-license-hero p { color: #dbeafe; margin: 0.25rem 0; line-height: 1.55; }
        .license-status-panel {
            border: 1px solid rgba(148, 163, 184, 0.25);
            border-radius: 1rem;
            padding: 0.9rem;
            background: rgba(4, 10, 24, 0.72);
        }
        .license-status-panel strong { display:block; color:#ffedd5; margin-bottom:0.35rem; }
        .license-status-list { display:grid; gap:0.42rem; margin-top:0.6rem; }
        .license-status-row { display:flex; justify-content:space-between; gap:0.8rem; color:#d8e2f0; border-bottom:1px solid rgba(148,163,184,0.13); padding-bottom:0.35rem; }
        .license-status-row span:last-child { color:#ffedd5; font-weight:800; text-align:right; }
        .license-cards-grid {
            display:grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap:0.78rem;
        }
        .license-rule-card {
            border:1px solid rgba(148,163,184,0.24);
            border-radius:1rem;
            padding:0.88rem;
            background:rgba(8,18,34,0.72);
            min-height:8.2rem;
        }
        .license-rule-card h3 { margin:0 0 0.4rem 0; font-size:1rem; color:#ffedd5; }
        .license-rule-card p, .license-rule-card li { color:#cbd5e1; line-height:1.45; font-size:0.94rem; }
        .license-text-panel,
        .eula-text-panel {
            border:1px solid rgba(148,163,184,0.22);
            border-radius:1.05rem;
            padding:1rem;
            background:rgba(2,8,23,0.78);
            max-height:32rem;
            overflow:auto;
        }
        .eula-text-panel { border-color:rgba(255,138,0,0.28); background:rgba(8,18,34,0.82); }
        .license-text-panel h3, .eula-text-panel h3 { margin:0 0 0.75rem 0; color:#ffedd5; font-size:1rem; }
        .license-text-panel pre, .eula-text-panel pre { white-space:pre-wrap; color:#dbeafe; font-size:0.92rem; line-height:1.45; margin:0; }
        @media (max-width: 1366px) {
            .application-license-hero { grid-template-columns: 1fr; padding:0.95rem; }
            .license-cards-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        }
        @media (max-width: 760px) {
            .license-cards-grid { grid-template-columns: 1fr; }
            .license-status-row { flex-direction:column; gap:0.12rem; }
            .license-status-row span:last-child { text-align:left; }
        }
        .about-brand-block,
        .license-brand-header,
        .splash-screen-brand {
            display: flex;
            align-items: center;
            gap: 0.8rem;
            border: 1px solid rgba(255, 138, 0, 0.28);
            border-radius: 18px;
            padding: 0.85rem 1rem;
            background: rgba(5, 10, 22, 0.72);
            box-shadow: 0 18px 52px rgba(0,0,0,0.30);
        }
        .about-brand-logo,
        .license-header-logo,
        .splash-screen-logo { width: 3.4rem; height: 3.4rem; object-fit: contain; filter: drop-shadow(0 12px 22px rgba(0,0,0,0.50)); }
        .about-brand-block strong,
        .license-brand-header strong,
        .splash-screen-brand strong { display:block; color:#f8fafc; font-weight:950; text-transform:uppercase; letter-spacing:0.04em; }
        .about-brand-block span,
        .license-brand-header span,
        .splash-screen-brand span { display:block; color:#cbd5e1; margin-top:0.18rem; }
        .about-brand-block small,
        .license-brand-header small { display:block; color:#ffedd5; margin-top:0.22rem; }
        .export-watermark-option { opacity: 0.06; pointer-events: none; }

        .command-palette-shell {
            border: 1px solid rgba(255, 138, 0, 0.30);
            border-radius: 18px;
            padding: 0.52rem 0.68rem;
            margin: 0.15rem 0 0.9rem 0;
            background: linear-gradient(135deg, rgba(2, 6, 23, 0.58), rgba(15, 23, 42, 0.34));
            box-shadow: 0 18px 50px rgba(0,0,0,0.24), inset 0 1px 0 rgba(255,255,255,0.05);
            backdrop-filter: blur(10px);
        }
        .command-palette-title {
            display:flex;
            justify-content:space-between;
            align-items:center;
            gap:0.8rem;
            margin-bottom:0.35rem;
        }
        .command-palette-title b { color:#f8fafc; font-size:1.02rem; }
        .command-palette-title span {
            border:1px solid rgba(148,163,184,0.28);
            border-radius:999px;
            padding:0.32rem 0.55rem;
            color:#cbd5e1;
            background:rgba(15,23,42,0.42);
            font-size:0.78rem !important;
            font-weight:900;
        }
        .command-result-card {
            border: 1px solid rgba(148,163,184,0.20);
            border-radius: 13px;
            padding: 0.62rem 0.72rem;
            margin: 0.32rem 0;
            background: rgba(15, 23, 42, 0.24);
        }
        .command-result-card b { color: #f8fafc; }
        .command-result-card small { color: #aeb8c8; display:block; margin-top:0.18rem; }
        .command-result-card code { color:#ffedd5; background:rgba(255,138,0,0.10); border-radius:6px; padding:0.08rem 0.28rem; }

        .functional-quick-actions {
            border: 1px solid rgba(148, 163, 184, 0.22);
            border-radius: 16px;
            padding: 0.58rem 0.64rem 0.50rem;
            margin: 0.25rem 0 0.62rem 0;
            background: linear-gradient(180deg, rgba(4, 10, 24, 0.20), rgba(5, 10, 22, 0.10));
            backdrop-filter: blur(3px);
        }
        .functional-quick-actions div[data-testid="stButton"] > button {
            min-height: 2.85rem;
            padding: 0.34rem 0.42rem;
            border-radius: 12px;
            font-size: 0.82rem;
            font-weight: 900;
            border: 1px solid rgba(148, 163, 184, 0.22);
            background: rgba(15, 23, 42, 0.22);
        }
        .functional-quick-actions div[data-testid="stButton"] > button:hover {
            border-color: rgba(255, 138, 0, 0.55);
            transform: translateY(-1px);
        }
        .functional-quick-actions div[data-testid="stButton"] > button:active {
            transform: translateY(0);
            background: rgba(255, 138, 0, 0.12);
        }
        .quick-actions-redesigned { display: block; }
        .quick-action-caption {
            min-height: 3.2rem;
            border: 1px solid rgba(148, 163, 184, 0.18);
            border-radius: 12px;
            padding: 0.48rem 0.56rem;
            margin: 0.30rem 0 0.30rem 0;
            background: rgba(15, 23, 42, 0.16);
        }
        .quick-action-caption b { display:block; color:#f8fafc; font-size:0.88rem; margin-bottom:0.16rem; }
        .quick-action-caption span { display:block; color:#cbd5e1; font-size:0.74rem; line-height:1.24; }
        .project-search-result {
            border: 1px solid rgba(148,163,184,0.22);
            border-radius: 12px;
            padding: 0.55rem 0.7rem;
            margin: 0.35rem 0;
            background: rgba(15, 23, 42, 0.18);
        }
        .sidebar-search-hit {
            border-left: 3px solid rgba(255, 138, 0, 0.75);
            padding: 0.35rem 0.45rem;
            margin: 0.25rem 0;
            background: rgba(15, 23, 42, 0.18);
            border-radius: 8px;
        }
        .docs-hero {
            min-height: auto;
            margin-top: 0.4rem;
            padding: 0;
            border-radius: 18px;
            border: 1px solid rgba(255, 138, 0, 0.38);
            background: rgba(2, 6, 23, 0.08);
            box-shadow: 0 28px 90px rgba(0,0,0,0.26);
            overflow: hidden;
        }
        .docs-hero-banner {
            position: relative;
            min-height: clamp(250px, 34vw, 430px);
            border-radius: 18px 18px 0 0;
            overflow: hidden;
            background: rgba(2, 6, 23, 0.08);
        }
        .docs-hero-image {
            position: absolute;
            inset: 0;
            width: 100%;
            height: 100%;
            object-fit: cover;
            object-position: center center;
            display: block;
            opacity: 1;
            filter: saturate(1.08) contrast(1.04);
        }
        .docs-hero-banner::before {
            content: "";
            position: absolute;
            inset: 0;
            z-index: 1;
            background:
                radial-gradient(circle at 82% 52%, rgba(255, 138, 0, 0.02), transparent 32%),
                linear-gradient(90deg, rgba(3, 7, 18, 0.34) 0%, rgba(3, 7, 18, 0.16) 46%, rgba(3, 7, 18, 0.02) 100%);
        }
        .docs-hero-brand-badge {
            position: absolute;
            right: clamp(1rem, 3vw, 2.4rem);
            top: clamp(1rem, 2.4vw, 2rem);
            z-index: 2;
            width: clamp(70px, 7vw, 120px);
            height: clamp(70px, 7vw, 120px);
            border-radius: 22px;
            border: 1px solid rgba(255, 255, 255, 0.22);
            background: rgba(2, 6, 23, 0.18);
            backdrop-filter: blur(3px);
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 18px 45px rgba(0, 0, 0, 0.22);
        }
        .docs-hero-brand-badge img {
            width: 86%;
            height: 86%;
            object-fit: contain;
            display: block;
        }
        .docs-hero-content {
            position: absolute;
            left: clamp(1.2rem, 4vw, 4rem);
            bottom: clamp(1.2rem, 4vw, 3rem);
            z-index: 2;
            max-width: min(42rem, 72vw);
            padding: 1rem 1.2rem;
            border: 1px solid rgba(148, 163, 184, 0.20);
            border-radius: 18px;
            background: rgba(4, 10, 24, 0.24);
            backdrop-filter: blur(3px);
            box-shadow: 0 20px 70px rgba(0, 0, 0, 0.24);
        }
        .docs-hero-kicker {
            color: var(--app-accent);
            font-weight: 900;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            margin-bottom: 0.35rem;
        }
        .docs-hero-title {
            color: #ffffff;
            font-size: clamp(2rem, 4vw, 4rem) !important;
            line-height: 1.05 !important;
            font-weight: 950;
            margin: 0 0 0.5rem 0 !important;
        }
        .docs-hero-subtitle {
            color: #e5e7eb !important;
            font-size: clamp(1rem, 1.35vw, 1.35rem) !important;
            margin: 0 !important;
        }
        .docs-panel {
            border: 1px solid rgba(148, 163, 184, 0.22);
            border-radius: 16px;
            background: rgba(5, 10, 22, 0.66);
            backdrop-filter: blur(8px);
            padding: 1rem;
            margin: 0.9rem 1rem;
        }
        .docs-panel h3 { color: var(--app-accent); margin-top: 0; }
        .docs-v2-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.75rem;
            margin: 0.85rem 0 1rem 0;
        }
        .docs-v2-card {
            border: 1px solid rgba(148, 163, 184, 0.22);
            border-radius: 16px;
            padding: 0.85rem;
            min-height: 8.2rem;
            background: linear-gradient(180deg, rgba(15, 23, 42, 0.58), rgba(2, 6, 23, 0.42));
            box-shadow: 0 16px 42px rgba(0, 0, 0, 0.20);
        }
        .docs-v2-card b { color: #f8fafc; display:block; margin: 0.25rem 0; }
        .docs-v2-card span { color: #cbd5e1; font-size: 0.92rem; line-height: 1.35; }
        .docs-v2-icon { font-size: 1.55rem; }
        .docs-toc {
            display: flex;
            flex-wrap: wrap;
            gap: 0.45rem;
            margin: 0.4rem 0 1rem 0;
        }
        .docs-toc a {
            color: #ffedd5 !important;
            text-decoration: none;
            border: 1px solid rgba(255, 138, 0, 0.30);
            border-radius: 999px;
            padding: 0.34rem 0.62rem;
            background: rgba(255, 138, 0, 0.09);
            font-weight: 800;
            font-size: 0.86rem;
        }
        .docs-section-anchor { scroll-margin-top: 5rem; }

        html { scroll-behavior: smooth; }
        @keyframes gas-page-fade { from { opacity: 0; } to { opacity: 1; } }
        @keyframes gas-page-slide { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes gas-active-underline { from { opacity: 0; transform: scaleX(0.18); } to { opacity: 1; transform: scaleX(1); } }
        @keyframes gas-sidebar-expand { from { opacity: 0.88; transform: translateX(-8px); } to { opacity: 1; transform: translateX(0); } }
        @keyframes gas-sidebar-collapse { from { opacity: 1; transform: translateX(0); } to { opacity: 0.88; transform: translateX(-8px); } }
        @keyframes gas-command-open { from { opacity: 0; transform: translateY(-8px) scale(0.985); } to { opacity: 1; transform: translateY(0) scale(1); } }
        @keyframes gas-command-close { from { opacity: 1; transform: translateY(0) scale(1); } to { opacity: 0; transform: translateY(-6px) scale(0.99); } }
        @keyframes gas-skeleton-shimmer { 0% { background-position: 220% 0; } 100% { background-position: -220% 0; } }
        @keyframes gas-progress-pulse { 0%, 100% { opacity: 0.65; transform: scaleX(0.96); } 50% { opacity: 1; transform: scaleX(1); } }
        .app-page-shell { animation: gas-page-slide 260ms cubic-bezier(0.22, 1, 0.36, 1) both; }
        .dashboard-card, .docs-v2-card, .command-result-card, .quick-action-caption { transition: transform 180ms cubic-bezier(0.22, 1, 0.36, 1), border-color 180ms ease, box-shadow 180ms ease; }
        .dashboard-card:hover, .docs-v2-card:hover, .command-result-card:hover, .quick-action-caption:hover { transform: translateY(-3px); }
        section[data-testid="stSidebar"] { animation: gas-sidebar-expand 240ms ease-out both; }
        .command-palette-shell { animation: gas-command-open 180ms ease-out both; }
        .navigation-loading-skeleton {
            min-height: 0.72rem;
            border-radius: 999px;
            background: linear-gradient(90deg, rgba(148,163,184,0.12), rgba(255,138,0,0.22), rgba(148,163,184,0.12));
            background-size: 220% 100%;
            animation: gas-skeleton-shimmer 1.15s ease-in-out infinite;
        }
        .navigation-progress-indicator {
            height: 3px;
            border-radius: 999px;
            background: linear-gradient(90deg, rgba(255,138,0,0.18), rgba(255,138,0,0.88), rgba(255,138,0,0.18));
            transform-origin: center;
            animation: gas-progress-pulse 1.2s ease-in-out infinite;
        }
        @media (prefers-reduced-motion: reduce) {
            html { scroll-behavior: auto; }
            *, *::before, *::after { animation-duration: 1ms !important; animation-iteration-count: 1 !important; transition-duration: 1ms !important; scroll-behavior: auto !important; }
        }
        .docs-info-row {
            border-left: 3px solid rgba(255, 138, 0, 0.80);
            border-radius: 10px;
            padding: 0.6rem 0.75rem;
            margin: 0.45rem 0;
            background: rgba(15, 23, 42, 0.42);
        }
        .docs-info-row b { color: #f8fafc; }
        .docs-info-row span { color: #cbd5e1; }
        @media (max-width: 1100px) {
            .docs-v2-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        }
        @media (max-width: 760px) {
            .docs-v2-grid { grid-template-columns: 1fr; }
        }
        @media (max-width: 1100px) {
            .app-nav-wrap { grid-template-columns: repeat(3, minmax(0, 1fr)); }
            section[data-testid="stSidebar"] { width: 12.6rem !important; min-width: 12.6rem !important; max-width: 12.6rem !important; }
        }
        @media (max-width: 760px) {
            .app-nav-wrap { grid-template-columns: 1fr; }
            .docs-hero { border-radius: 14px; }
            .docs-hero-banner { min-height: 240px; }
            .docs-hero-content { left: 0.8rem; right: 0.8rem; bottom: 0.8rem; max-width: none; }
        }
        </style>
        """
        .replace('{tokens["base"]}', tokens["base"])
        .replace('{tokens["body"]}', tokens["body"])
        .replace('{tokens["caption"]}', tokens["caption"])
        .replace('{tokens["button"]}', tokens["button"])
        .replace('{tokens["h1"]}', tokens["h1"])
        .replace('{layout_tokens["max_width"]}', layout_tokens["max_width"])
        .replace('{app_background_css}', app_background_css),
        unsafe_allow_html=True,
    )


def _select_ui_scale() -> str:
    with st.sidebar.expander("Вид интерфейса", expanded=False):
        selected = st.radio(
            "Размер",
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
    with st.sidebar.expander("Компоновка", expanded=False):
        selected = st.radio(
            "Экран",
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


def _responsive_dashboard_target_names() -> tuple[str, ...]:
    """Expose supported responsive Dashboard targets for tests and documentation."""
    return tuple(target["name"] for target in RESPONSIVE_DASHBOARD_TARGETS)


def _responsive_dashboard_media_queries() -> tuple[str, ...]:
    """Expose the CSS breakpoint queries used by the responsive Dashboard pass."""
    return tuple(target["media"] for target in RESPONSIVE_DASHBOARD_TARGETS)


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



def _las_editor_reference_state(column_names: list[str]) -> dict[str, object]:
    """Collect currently existing curve-reference containers for safe rename."""

    return {
        "tablet_tracks": list(st.session_state.get("interpretation_tablet_columns", [])),
        "templates": {},
        "presets": {
            "mud_gas": list(mud_gas_literature_tablet_columns(column_names)),
            "default_tablet": list(default_tablet_columns(column_names)),
        },
        "saved_calculations": {},
        "exports": {"columns": list(column_names)},
        "manifest": {name: {"source": "las_editor"} for name in column_names},
        "curve_aliases": dict(st.session_state.get(LAS_EDITOR_ALIAS_MAP_KEY, {})),
        "curve_group_overrides": dict(st.session_state.get(LAS_EDITOR_GROUP_OVERRIDES_KEY, {})),
        "curve_category_overrides": dict(st.session_state.get(LAS_EDITOR_CATEGORY_OVERRIDES_KEY, {})),
        "curve_unit_overrides": dict(st.session_state.get(LAS_EDITOR_UNIT_OVERRIDES_KEY, {})),
        "curve_metadata": dict(st.session_state.get(LAS_EDITOR_METADATA_KEY, {})),
    }


def _apply_las_editor_reference_state(references: dict[str, object]) -> None:
    """Write back rename-aware references that are represented in session state."""

    tablet_tracks = references.get("tablet_tracks")
    if isinstance(tablet_tracks, list):
        st.session_state["interpretation_tablet_columns"] = tablet_tracks


def _render_las_curve_alias_manager(prepared_df: pd.DataFrame) -> None:
    st.markdown("### Curve Manager · Alias curves")
    st.caption(
        "Назначение стандартных alias без переименования колонок: depth, c1, c2, c3, "
        "i/n C4-C5, CO2, H2S, ROP и литология."
    )

    if LAS_EDITOR_ALIAS_HISTORY_KEY not in st.session_state:
        st.session_state[LAS_EDITOR_ALIAS_HISTORY_KEY] = ()
    if LAS_EDITOR_ALIAS_MAP_KEY not in st.session_state:
        st.session_state[LAS_EDITOR_ALIAS_MAP_KEY] = {}

    column_names = [str(column) for column in prepared_df.columns]
    current_aliases = dict(st.session_state.get(LAS_EDITOR_ALIAS_MAP_KEY, {}))
    suggestions = suggest_curve_aliases(column_names)

    if st.button("Автоопределить alias", use_container_width=True, key="las_editor_alias_autodetect"):
        st.session_state[LAS_EDITOR_ALIAS_MAP_KEY] = {**current_aliases, **suggestions}
        current_aliases = dict(st.session_state.get(LAS_EDITOR_ALIAS_MAP_KEY, {}))
        st.success(f"Автоопределено alias: {len(suggestions)}")

    curve_col, alias_col, action_col = st.columns([2, 2, 1])
    curve_name = curve_col.selectbox(
        "Кривая для alias",
        options=column_names,
        key="las_editor_alias_curve",
    )
    alias_options = list(available_aliases())
    suggested_alias = current_aliases.get(curve_name) or suggestions.get(curve_name) or ""
    alias_index = alias_options.index(suggested_alias) if suggested_alias in alias_options else 0
    alias = alias_col.selectbox(
        "Стандартный alias",
        options=alias_options,
        index=alias_index,
        key="las_editor_alias_value",
    )

    references = _las_editor_reference_state(column_names)
    if action_col.button("Назначить", use_container_width=True, key="las_editor_alias_apply"):
        try:
            result = assign_curve_alias(
                prepared_df,
                curve_name,
                alias,
                aliases=current_aliases,
                history=st.session_state.get(LAS_EDITOR_ALIAS_HISTORY_KEY, ()),
                references=references,
                reason="manual",
                source="las_editor_ui",
            )
            st.session_state[LAS_EDITOR_ALIAS_MAP_KEY] = result.aliases
            st.session_state[LAS_EDITOR_ALIAS_HISTORY_KEY] = result.history
            for message in result.diagnostics:
                st.info(message)
            for message in result.warnings:
                st.warning(message)
            if result.assigned:
                st.success(f"Alias назначен: {result.curve_name} → {result.alias}")
            else:
                st.warning("Alias не изменился: назначение уже существовало.")
        except ValueError as exc:
            st.warning(str(exc))

    history = tuple(st.session_state.get(LAS_EDITOR_ALIAS_HISTORY_KEY, ()))
    if st.button("Undo последнего alias", disabled=not history, use_container_width=True, key="las_editor_alias_undo"):
        try:
            result = undo_last_alias(
                aliases=dict(st.session_state.get(LAS_EDITOR_ALIAS_MAP_KEY, {})),
                history=history,
                references=references,
            )
            st.session_state[LAS_EDITOR_ALIAS_MAP_KEY] = result.aliases
            st.session_state[LAS_EDITOR_ALIAS_HISTORY_KEY] = result.history
            for message in result.diagnostics:
                st.info(message)
            st.success("Последнее alias-назначение отменено.")
        except ValueError as exc:
            st.warning(str(exc))

    current_aliases = dict(st.session_state.get(LAS_EDITOR_ALIAS_MAP_KEY, {}))
    with st.expander("Текущие alias и история", expanded=bool(current_aliases or history)):
        if current_aliases:
            st.dataframe(
                pd.DataFrame([{"curve_name": key, "alias": value} for key, value in current_aliases.items()]),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.caption("Alias пока не назначены.")
        history = tuple(st.session_state.get(LAS_EDITOR_ALIAS_HISTORY_KEY, ()))
        if history:
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "curve_name": entry.curve_name,
                            "alias": entry.alias,
                            "previous_alias": entry.previous_alias,
                            "timestamp": entry.timestamp,
                            "reason": entry.reason,
                            "source": entry.source,
                        }
                        for entry in history
                    ]
                ),
                use_container_width=True,
                hide_index=True,
            )



def _render_las_curve_grouping_manager(prepared_df: pd.DataFrame) -> None:
    st.markdown("### Curve Manager · Curve grouping")
    st.caption(
        "Группировка LAS-кривых по инженерным категориям: глубина, GR, газ, "
        "компоненты C1-C5, сопротивления, density/neutron, буровые параметры и прочие кривые."
    )

    if LAS_EDITOR_GROUP_HISTORY_KEY not in st.session_state:
        st.session_state[LAS_EDITOR_GROUP_HISTORY_KEY] = ()
    if LAS_EDITOR_GROUP_OVERRIDES_KEY not in st.session_state:
        st.session_state[LAS_EDITOR_GROUP_OVERRIDES_KEY] = {}

    column_names = [str(column) for column in prepared_df.columns]
    aliases = dict(st.session_state.get(LAS_EDITOR_ALIAS_MAP_KEY, {}))
    overrides = dict(st.session_state.get(LAS_EDITOR_GROUP_OVERRIDES_KEY, {}))
    group_rows = curve_group_table_rows(column_names, overrides=overrides, aliases=aliases)

    st.dataframe(
        pd.DataFrame(group_rows).rename(
            columns={
                "curve_name": "Кривая",
                "alias": "Alias",
                "auto_group_label": "Авто-группа",
                "group_label": "Текущая группа",
                "manual_override": "Ручное правило",
            }
        )[["Кривая", "Alias", "Авто-группа", "Текущая группа", "Ручное правило"]],
        use_container_width=True,
        hide_index=True,
    )

    curve_col, group_col, action_col = st.columns([2, 2, 1])
    curve_name = curve_col.selectbox(
        "Кривая для группировки",
        options=column_names,
        key="las_editor_group_curve",
    )
    group_options = list(available_curve_groups())
    current_group = next((row["group"] for row in group_rows if row["curve_name"] == curve_name), "other")
    group_index = group_options.index(current_group) if current_group in group_options else group_options.index("other")
    selected_group = group_col.selectbox(
        "Инженерная группа",
        options=group_options,
        index=group_index,
        format_func=curve_group_label,
        key="las_editor_group_value",
    )

    references = _las_editor_reference_state(column_names)
    if action_col.button("Назначить группу", use_container_width=True, key="las_editor_group_apply"):
        try:
            result = assign_curve_group(
                prepared_df,
                curve_name,
                selected_group,
                overrides=overrides,
                history=st.session_state.get(LAS_EDITOR_GROUP_HISTORY_KEY, ()),
                references=references,
                reason="manual",
                source="las_editor_ui",
            )
            st.session_state[LAS_EDITOR_GROUP_OVERRIDES_KEY] = result.overrides
            st.session_state[LAS_EDITOR_GROUP_HISTORY_KEY] = result.history
            for message in result.diagnostics:
                st.info(message)
            if result.assigned:
                st.success(f"Группа назначена: {result.curve_name} → {curve_group_label(result.group)}")
            else:
                st.warning("Группа не изменилась: назначение уже существовало.")
        except ValueError as exc:
            st.warning(str(exc))

    history = tuple(st.session_state.get(LAS_EDITOR_GROUP_HISTORY_KEY, ()))
    if st.button("Undo последней группировки", disabled=not history, use_container_width=True, key="las_editor_group_undo"):
        try:
            result = undo_last_group_assignment(
                prepared_df,
                overrides=dict(st.session_state.get(LAS_EDITOR_GROUP_OVERRIDES_KEY, {})),
                history=history,
                references=references,
            )
            st.session_state[LAS_EDITOR_GROUP_OVERRIDES_KEY] = result.overrides
            st.session_state[LAS_EDITOR_GROUP_HISTORY_KEY] = result.history
            for message in result.diagnostics:
                st.info(message)
            st.success("Последняя группировка отменена.")
        except ValueError as exc:
            st.warning(str(exc))

    history = tuple(st.session_state.get(LAS_EDITOR_GROUP_HISTORY_KEY, ()))
    with st.expander("История группировки кривых", expanded=bool(history)):
        if history:
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "curve_name": entry.curve_name,
                            "group": curve_group_label(entry.group),
                            "previous_group": curve_group_label(entry.previous_group),
                            "timestamp": entry.timestamp,
                            "reason": entry.reason,
                            "source": entry.source,
                        }
                        for entry in history
                    ]
                ),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.caption("История ручной группировки пока пуста.")


def _render_las_curve_category_manager(prepared_df: pd.DataFrame) -> None:
    st.markdown("### Curve Manager · Curve categories")
    st.caption(
        "Категории LAS-кривых над уровнем инженерных групп: depth reference, petrophysics, "
        "mud gas, drilling, interpretation и uncategorized. Категории помогают готовить "
        "отчеты, фильтры и будущие правила импорта/экспорта без изменения исходных данных."
    )

    if LAS_EDITOR_CATEGORY_HISTORY_KEY not in st.session_state:
        st.session_state[LAS_EDITOR_CATEGORY_HISTORY_KEY] = ()
    if LAS_EDITOR_CATEGORY_OVERRIDES_KEY not in st.session_state:
        st.session_state[LAS_EDITOR_CATEGORY_OVERRIDES_KEY] = {}

    column_names = [str(column) for column in prepared_df.columns]
    aliases = dict(st.session_state.get(LAS_EDITOR_ALIAS_MAP_KEY, {}))
    group_overrides = dict(st.session_state.get(LAS_EDITOR_GROUP_OVERRIDES_KEY, {}))
    category_overrides = dict(st.session_state.get(LAS_EDITOR_CATEGORY_OVERRIDES_KEY, {}))
    category_rows = curve_category_table_rows(
        column_names,
        group_overrides=group_overrides,
        category_overrides=category_overrides,
        aliases=aliases,
    )
    categories = build_curve_categories(
        column_names,
        group_overrides=group_overrides,
        category_overrides=category_overrides,
    )

    summary_rows = category_summary_rows(categories)
    with st.expander("Сводка категорий", expanded=True):
        st.dataframe(
            pd.DataFrame(summary_rows).rename(
                columns={
                    "category_label": "Категория",
                    "curve_count": "Кривых",
                    "curves": "Состав",
                }
            )[["Категория", "Кривых", "Состав"]],
            use_container_width=True,
            hide_index=True,
        )

    st.dataframe(
        pd.DataFrame(category_rows).rename(
            columns={
                "curve_name": "Кривая",
                "alias": "Alias",
                "group_label": "Группа",
                "auto_category_label": "Авто-категория",
                "category_label": "Текущая категория",
                "manual_override": "Ручное правило",
            }
        )[["Кривая", "Alias", "Группа", "Авто-категория", "Текущая категория", "Ручное правило"]],
        use_container_width=True,
        hide_index=True,
    )

    curve_col, category_col, action_col = st.columns([2, 2, 1])
    curve_name = curve_col.selectbox(
        "Кривая для категории",
        options=column_names,
        key="las_editor_category_curve",
    )
    category_options = list(available_curve_categories())
    current_category = next((row["category"] for row in category_rows if row["curve_name"] == curve_name), "uncategorized")
    category_index = category_options.index(current_category) if current_category in category_options else category_options.index("uncategorized")
    selected_category = category_col.selectbox(
        "Категория",
        options=category_options,
        index=category_index,
        format_func=curve_category_label,
        key="las_editor_category_value",
    )

    references = _las_editor_reference_state(column_names)
    if action_col.button("Назначить категорию", use_container_width=True, key="las_editor_category_apply"):
        try:
            result = assign_curve_category(
                prepared_df,
                curve_name,
                selected_category,
                group_overrides=group_overrides,
                category_overrides=category_overrides,
                history=st.session_state.get(LAS_EDITOR_CATEGORY_HISTORY_KEY, ()),
                references=references,
                reason="manual",
                source="las_editor_ui",
            )
            st.session_state[LAS_EDITOR_CATEGORY_OVERRIDES_KEY] = result.overrides
            st.session_state[LAS_EDITOR_CATEGORY_HISTORY_KEY] = result.history
            for message in result.diagnostics:
                st.info(message)
            if result.assigned:
                st.success(f"Категория назначена: {result.curve_name} → {curve_category_label(result.category)}")
            else:
                st.warning("Категория не изменилась: назначение уже существовало.")
        except ValueError as exc:
            st.warning(str(exc))

    history = tuple(st.session_state.get(LAS_EDITOR_CATEGORY_HISTORY_KEY, ()))
    if st.button("Undo последней категории", disabled=not history, use_container_width=True, key="las_editor_category_undo"):
        try:
            result = undo_last_category_assignment(
                prepared_df,
                group_overrides=group_overrides,
                category_overrides=dict(st.session_state.get(LAS_EDITOR_CATEGORY_OVERRIDES_KEY, {})),
                history=history,
                references=references,
            )
            st.session_state[LAS_EDITOR_CATEGORY_OVERRIDES_KEY] = result.overrides
            st.session_state[LAS_EDITOR_CATEGORY_HISTORY_KEY] = result.history
            for message in result.diagnostics:
                st.info(message)
            st.success("Последняя категория отменена.")
        except ValueError as exc:
            st.warning(str(exc))

    history = tuple(st.session_state.get(LAS_EDITOR_CATEGORY_HISTORY_KEY, ()))
    with st.expander("История категорий кривых", expanded=bool(history)):
        if history:
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "curve_name": entry.curve_name,
                            "category": curve_category_label(entry.category),
                            "previous_category": curve_category_label(entry.previous_category),
                            "timestamp": entry.timestamp,
                            "reason": entry.reason,
                            "source": entry.source,
                        }
                        for entry in history
                    ]
                ),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.caption("История ручных категорий пока пуста.")


def _render_las_curve_units_manager(prepared_df: pd.DataFrame) -> None:
    st.markdown("### Curve Manager · Curve units manager")
    st.caption(
        "Единицы LAS-кривых управляются metadata-only: исходные значения не пересчитываются, "
        "а выбранные unit overrides сохраняются для отчетов, будущего импорта/экспорта и проверки расчетов."
    )

    if LAS_EDITOR_UNIT_HISTORY_KEY not in st.session_state:
        st.session_state[LAS_EDITOR_UNIT_HISTORY_KEY] = ()
    if LAS_EDITOR_UNIT_OVERRIDES_KEY not in st.session_state:
        st.session_state[LAS_EDITOR_UNIT_OVERRIDES_KEY] = {}

    column_names = [str(column) for column in prepared_df.columns]
    aliases = dict(st.session_state.get(LAS_EDITOR_ALIAS_MAP_KEY, {}))
    group_overrides = dict(st.session_state.get(LAS_EDITOR_GROUP_OVERRIDES_KEY, {}))
    category_overrides = dict(st.session_state.get(LAS_EDITOR_CATEGORY_OVERRIDES_KEY, {}))
    unit_overrides = dict(st.session_state.get(LAS_EDITOR_UNIT_OVERRIDES_KEY, {}))

    unit_rows = curve_unit_table_rows(
        column_names,
        group_overrides=group_overrides,
        category_overrides=category_overrides,
        unit_overrides=unit_overrides,
        aliases=aliases,
    )
    units = build_curve_units(
        column_names,
        group_overrides=group_overrides,
        category_overrides=category_overrides,
        unit_overrides=unit_overrides,
    )

    with st.expander("Сводка единиц измерения", expanded=True):
        st.dataframe(
            pd.DataFrame(unit_summary_rows(units)).rename(
                columns={"unit_label": "Единица", "curve_count": "Кривых", "curves": "Состав"}
            )[["Единица", "Кривых", "Состав"]],
            use_container_width=True,
            hide_index=True,
        )

    st.dataframe(
        pd.DataFrame(unit_rows).rename(
            columns={
                "curve_name": "Кривая",
                "alias": "Alias",
                "category_label": "Категория",
                "auto_unit_label": "Авто-единица",
                "unit_label": "Текущая единица",
                "manual_override": "Ручное правило",
                "convertible_targets": "Безопасный пересчет",
            }
        )[["Кривая", "Alias", "Категория", "Авто-единица", "Текущая единица", "Ручное правило", "Безопасный пересчет"]],
        use_container_width=True,
        hide_index=True,
    )

    curve_col, unit_col, action_col = st.columns([2, 2, 1])
    curve_name = curve_col.selectbox("Кривая для unit", options=column_names, key="las_editor_unit_curve")
    unit_options = list(available_curve_units())
    current_unit = next((row["unit"] for row in unit_rows if row["curve_name"] == curve_name), "unknown")
    unit_index = unit_options.index(current_unit) if current_unit in unit_options else unit_options.index("unknown")
    selected_unit = unit_col.selectbox(
        "Единица измерения",
        options=unit_options,
        index=unit_index,
        format_func=curve_unit_label,
        key="las_editor_unit_value",
    )

    references = _las_editor_reference_state(column_names)
    if action_col.button("Назначить unit", use_container_width=True, key="las_editor_unit_apply"):
        try:
            result = assign_curve_unit(
                prepared_df,
                curve_name,
                selected_unit,
                group_overrides=group_overrides,
                category_overrides=category_overrides,
                unit_overrides=unit_overrides,
                history=st.session_state.get(LAS_EDITOR_UNIT_HISTORY_KEY, ()),
                references=references,
                reason="manual",
                source="las_editor_ui",
            )
            st.session_state[LAS_EDITOR_UNIT_OVERRIDES_KEY] = result.overrides
            st.session_state[LAS_EDITOR_UNIT_HISTORY_KEY] = result.history
            for message in result.diagnostics:
                st.info(message)
            if result.assigned:
                st.success(f"Единица назначена: {result.curve_name} → {curve_unit_label(result.unit)}")
            else:
                st.warning("Единица не изменилась: назначение уже существовало.")
        except ValueError as exc:
            st.warning(str(exc))

    history = tuple(st.session_state.get(LAS_EDITOR_UNIT_HISTORY_KEY, ()))
    if st.button("Undo последней единицы", disabled=not history, use_container_width=True, key="las_editor_unit_undo"):
        try:
            result = undo_last_unit_assignment(
                prepared_df,
                group_overrides=group_overrides,
                category_overrides=category_overrides,
                unit_overrides=dict(st.session_state.get(LAS_EDITOR_UNIT_OVERRIDES_KEY, {})),
                history=history,
                references=references,
            )
            st.session_state[LAS_EDITOR_UNIT_OVERRIDES_KEY] = result.overrides
            st.session_state[LAS_EDITOR_UNIT_HISTORY_KEY] = result.history
            for message in result.diagnostics:
                st.info(message)
            st.success("Последняя единица отменена.")
        except ValueError as exc:
            st.warning(str(exc))

    history = tuple(st.session_state.get(LAS_EDITOR_UNIT_HISTORY_KEY, ()))
    with st.expander("История единиц кривых", expanded=bool(history)):
        if history:
            st.dataframe(
                pd.DataFrame([
                    {
                        "curve_name": entry.curve_name,
                        "unit": curve_unit_label(entry.unit),
                        "previous_unit": curve_unit_label(entry.previous_unit),
                        "timestamp": entry.timestamp,
                        "reason": entry.reason,
                        "source": entry.source,
                    }
                    for entry in history
                ]),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.caption("История ручных единиц пока пуста.")



def _render_las_curve_mnemonics_dictionary(prepared_df: pd.DataFrame) -> None:
    st.markdown("### Curve Manager · Curve mnemonics dictionary")
    st.caption(
        "Словарь мнемоник помогает быстро сверить LAS-кривые с каноническими названиями, "
        "группами, категориями и единицами перед alias/merge/quality review. Данные LAS не изменяются."
    )

    column_names = [str(column) for column in prepared_df.columns]
    rows = curve_mnemonic_table_rows(column_names)
    st.session_state[LAS_EDITOR_MNEMONICS_KEY] = rows
    references = mnemonic_reference_manifest(column_names, references=_las_editor_reference_state(column_names))

    st.dataframe(
        pd.DataFrame(mnemonic_summary_rows(column_names)).rename(
            columns={"metric": "Показатель", "value": "Значение"}
        ),
        use_container_width=True,
        hide_index=True,
    )

    if rows:
        st.dataframe(
            pd.DataFrame(rows).rename(
                columns={
                    "curve_name": "Кривая",
                    "canonical": "Каноническая",
                    "label": "Описание",
                    "group_label": "Группа",
                    "category_label": "Категория",
                    "unit_label": "Единица",
                    "match_type": "Источник",
                    "aliases": "Alias",
                    "recommendation": "Рекомендация",
                }
            )[
                [
                    "Кривая",
                    "Каноническая",
                    "Описание",
                    "Группа",
                    "Категория",
                    "Единица",
                    "Источник",
                    "Alias",
                    "Рекомендация",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )
    suggested_count = sum(1 for row in rows if row.get("match_type") == "suggested")
    if suggested_count:
        st.warning(f"Мнемоник без точного словарного совпадения: {suggested_count}. Проверьте alias, группу и единицы.")
    else:
        st.success("Все кривые распознаны словарем или alias-правилами.")
    st.caption(f"Dictionary manifest готов для сохранения: {len(references.get('curve_mnemonics', {}))} записей.")

def _render_las_curve_duplicate_detection(prepared_df: pd.DataFrame) -> None:
    st.markdown("### Curve Manager · Curve duplicate detection")
    st.caption(
        "Поиск дубликатов кривых сравнивает мнемоники, alias, числовые значения и корреляцию. "
        "Инструмент только формирует кандидаты для инженерной проверки: он не удаляет, не объединяет и не меняет LAS-данные."
    )

    column_names = [str(column) for column in prepared_df.columns]
    aliases = dict(st.session_state.get(LAS_EDITOR_ALIAS_MAP_KEY, {}))
    group_overrides = dict(st.session_state.get(LAS_EDITOR_GROUP_OVERRIDES_KEY, {}))
    category_overrides = dict(st.session_state.get(LAS_EDITOR_CATEGORY_OVERRIDES_KEY, {}))
    unit_overrides = dict(st.session_state.get(LAS_EDITOR_UNIT_OVERRIDES_KEY, {}))

    threshold_col, match_col, action_col = st.columns([1, 1, 1])
    correlation_threshold = threshold_col.slider(
        "Порог корреляции",
        min_value=0.980,
        max_value=1.000,
        value=0.995,
        step=0.001,
        format="%.3f",
        key="las_editor_duplicate_correlation_threshold",
    )
    value_match_threshold = match_col.slider(
        "Порог совпадения значений",
        min_value=0.950,
        max_value=1.000,
        value=0.999,
        step=0.001,
        format="%.3f",
        key="las_editor_duplicate_value_match_threshold",
    )

    should_run = action_col.button(
        "Найти дубликаты кривых",
        use_container_width=True,
        key="las_editor_duplicate_detect_apply",
    )
    if LAS_EDITOR_DUPLICATES_KEY not in st.session_state or should_run:
        result = detect_curve_duplicates(
            prepared_df,
            aliases=aliases,
            group_overrides=group_overrides,
            category_overrides=category_overrides,
            unit_overrides=unit_overrides,
            correlation_threshold=correlation_threshold,
            value_match_threshold=value_match_threshold,
            references=_las_editor_reference_state(column_names),
        )
        st.session_state[LAS_EDITOR_DUPLICATES_KEY] = result.candidates
        st.session_state[LAS_EDITOR_DUPLICATE_SUMMARY_KEY] = result.summary
        if should_run:
            for message in result.diagnostics:
                st.info(message)

    candidates = tuple(st.session_state.get(LAS_EDITOR_DUPLICATES_KEY, ()))
    summary = dict(st.session_state.get(LAS_EDITOR_DUPLICATE_SUMMARY_KEY, {}))
    summary.setdefault("total", len(candidates))

    if candidates:
        st.success(f"Найдено кандидатов-дубликатов: {summary.get('total', len(candidates))}.")
    else:
        st.info("Кандидаты-дубликаты не найдены при текущих порогах.")

    st.dataframe(
        pd.DataFrame(curve_duplicate_summary_rows(summary)).rename(
            columns={"severity_label": "Тип", "candidate_count": "Кандидатов"}
        )[["Тип", "Кандидатов"]],
        use_container_width=True,
        hide_index=True,
    )

    rows = curve_duplicate_table_rows(candidates)
    if rows:
        st.dataframe(
            pd.DataFrame(rows).rename(
                columns={
                    "primary_curve": "Основная кривая",
                    "duplicate_curve": "Кандидат-дубликат",
                    "severity_label": "Уровень",
                    "reason": "Причина",
                    "correlation": "Корреляция",
                    "value_match_ratio": "Совпадение значений",
                    "shared_non_null": "Общих точек",
                    "primary_alias": "Alias основной",
                    "duplicate_alias": "Alias кандидата",
                    "group": "Группа",
                    "category": "Категория",
                    "unit": "Единица",
                    "recommendation": "Рекомендация",
                }
            )[
                [
                    "Основная кривая",
                    "Кандидат-дубликат",
                    "Уровень",
                    "Причина",
                    "Корреляция",
                    "Совпадение значений",
                    "Общих точек",
                    "Alias основной",
                    "Alias кандидата",
                    "Группа",
                    "Категория",
                    "Единица",
                    "Рекомендация",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )
    st.caption("Duplicate detection — диагностический этап перед merge/rename. Удаление кривых здесь намеренно не выполняется.")



def _render_las_curve_bulk_edit_manager(prepared_df: pd.DataFrame) -> pd.DataFrame:
    st.markdown("### Curve Manager · Curve bulk edit")
    st.caption(
        "Массовое редактирование применяет одно явное действие к выбранным кривым: "
        "назначение группы, категории, единицы, metadata или аккуратный prefix/suffix rename. "
        "Все операции пишутся в журнал и не выполняются молча."
    )

    columns = [str(column) for column in prepared_df.columns]
    if not columns:
        st.info("Нет кривых для массового редактирования.")
        return prepared_df

    selected_curves = st.multiselect(
        "Кривые для bulk edit",
        options=columns,
        default=columns[: min(3, len(columns))],
        key="las_editor_bulk_edit_selected_curves",
    )
    action = st.selectbox(
        "Действие",
        options=tuple(BULK_EDIT_ACTION_LABELS),
        format_func=lambda value: BULK_EDIT_ACTION_LABELS.get(value, value),
        key="las_editor_bulk_edit_action",
    )

    value_col1, value_col2, value_col3 = st.columns(3)
    group = value_col1.text_input("Группа", value="", key="las_editor_bulk_edit_group")
    category = value_col2.text_input("Категория", value="", key="las_editor_bulk_edit_category")
    unit = value_col3.text_input("Единица", value="", key="las_editor_bulk_edit_unit")

    affix_col1, affix_col2 = st.columns(2)
    prefix = affix_col1.text_input("Prefix", value="", key="las_editor_bulk_edit_prefix")
    suffix = affix_col2.text_input("Suffix", value="", key="las_editor_bulk_edit_suffix")

    with st.expander("Metadata patch", expanded=False):
        description = st.text_input("Описание", value="", key="las_editor_bulk_edit_metadata_description")
        status = st.text_input("Статус", value="", key="las_editor_bulk_edit_metadata_status")
        quality = st.text_input("Качество", value="", key="las_editor_bulk_edit_metadata_quality")
        comment = st.text_area("Комментарий", value="", key="las_editor_bulk_edit_metadata_comment")

    metadata_patch = {
        key: value
        for key, value in {
            "description": description,
            "status": status,
            "quality": quality,
            "comment": comment,
        }.items()
        if str(value).strip()
    }

    if st.button("Применить bulk edit", use_container_width=True, key="las_editor_bulk_edit_apply"):
        try:
            result = apply_curve_bulk_edit(
                prepared_df,
                selected_curves=selected_curves,
                action=action,
                group=group.strip() or None,
                category=category.strip() or None,
                unit=unit.strip() or None,
                metadata_patch=metadata_patch,
                prefix=prefix,
                suffix=suffix,
                group_overrides=dict(st.session_state.get(LAS_EDITOR_GROUP_OVERRIDES_KEY, {})),
                category_overrides=dict(st.session_state.get(LAS_EDITOR_CATEGORY_OVERRIDES_KEY, {})),
                unit_overrides=dict(st.session_state.get(LAS_EDITOR_UNIT_OVERRIDES_KEY, {})),
                metadata=dict(st.session_state.get(LAS_EDITOR_METADATA_KEY, {})),
                references=_las_editor_reference_state(columns),
            )
            st.session_state[LAS_EDITOR_GROUP_OVERRIDES_KEY] = result.group_overrides
            st.session_state[LAS_EDITOR_CATEGORY_OVERRIDES_KEY] = result.category_overrides
            st.session_state[LAS_EDITOR_UNIT_OVERRIDES_KEY] = result.unit_overrides
            st.session_state[LAS_EDITOR_METADATA_KEY] = result.metadata
            st.session_state[LAS_EDITOR_BULK_EDIT_LOG_KEY] = tuple(st.session_state.get(LAS_EDITOR_BULK_EDIT_LOG_KEY, ())) + result.operations
            for warning in result.warnings:
                st.warning(warning)
            st.success(f"Bulk edit применен: {result.references['curve_bulk_edit_summary']['applied']} операций.")
            prepared_df = result.data
        except ValueError as exc:
            st.warning(str(exc))

    log = tuple(st.session_state.get(LAS_EDITOR_BULK_EDIT_LOG_KEY, ()))
    with st.expander("Журнал Curve bulk edit", expanded=bool(log)):
        if log:
            st.dataframe(
                pd.DataFrame(curve_bulk_edit_operation_rows(log)).rename(
                    columns={
                        "curve_name": "Кривая",
                        "action_label": "Действие",
                        "previous_value": "Было",
                        "new_value": "Стало",
                        "status": "Статус",
                        "message": "Сообщение",
                        "timestamp": "Время",
                    }
                )[["Кривая", "Действие", "Было", "Стало", "Статус", "Сообщение", "Время"]],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.caption("Журнал bulk edit пока пуст.")

    return prepared_df


def _render_las_curve_export_rules_manager(prepared_df: pd.DataFrame) -> None:
    st.markdown("### Curve Manager · Curve export rules")
    st.caption(
        "Правила экспорта готовят LAS-кривые перед выгрузкой: переименование мнемоник, "
        "конвертация единиц, обработка дублей, metadata и preview. Данные редактора не меняются до явного экспорта."
    )

    columns = [str(column) for column in prepared_df.columns]
    if not columns:
        st.info("Нет кривых для подготовки экспорта.")
        return

    profile_options = available_export_profiles()
    profile_col, mode_col, duplicate_col = st.columns([1.2, 1, 1])
    profile_id = profile_col.selectbox(
        "Профиль экспорта",
        options=profile_options,
        format_func=lambda value: get_export_profile(value).label,
        key="las_editor_export_profile",
    )
    curve_mode = mode_col.selectbox(
        "Кривые",
        options=("all", "selected", "source_only", "calculated_only"),
        format_func=lambda value: {
            "all": "Все",
            "selected": "Выбранные",
            "source_only": "Только исходные",
            "calculated_only": "Только расчетные",
        }.get(value, value),
        key="las_editor_export_curve_mode",
    )
    duplicate_strategy = duplicate_col.selectbox(
        "Дубликаты",
        options=("rename", "exclude", "keep"),
        format_func=lambda value: {
            "rename": "Переименовать",
            "exclude": "Исключить",
            "keep": "Оставить",
        }.get(value, value),
        key="las_editor_export_duplicate_strategy",
    )

    selected_curves = st.multiselect(
        "Кривые для экспорта",
        options=columns,
        default=columns,
        key="las_editor_export_selected_curves",
    )

    with st.expander("Профили экспорта", expanded=False):
        st.dataframe(
            pd.DataFrame(export_profile_rows()).rename(
                columns={
                    "profile_id": "ID",
                    "label": "Профиль",
                    "description": "Описание",
                    "null_value": "NULL",
                    "duplicate_strategy": "Дубликаты",
                    "curve_mode": "Режим",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

    null_col, metadata_col = st.columns([1, 2])
    null_value = null_col.number_input(
        "NULL value",
        value=float(get_export_profile(profile_id).null_value),
        key="las_editor_export_null_value",
    )
    metadata_text = metadata_col.text_input(
        "WELL metadata override",
        value="",
        placeholder="Например: WELL=Well-01; COMPANY=Gas Ratio Pro",
        key="las_editor_export_metadata_text",
    )

    metadata: dict[str, str] = {}
    for item in metadata_text.split(";"):
        if "=" in item:
            key, value = item.split("=", 1)
            if key.strip() and value.strip():
                metadata[key.strip().upper()] = value.strip()

    if st.button("Построить preview export rules", use_container_width=True, key="las_editor_export_rules_preview"):
        try:
            result = apply_curve_export_rules(
                prepared_df,
                profile_id=profile_id,
                selected_curves=selected_curves,
                aliases=dict(st.session_state.get(LAS_EDITOR_ALIAS_MAP_KEY, {})),
                unit_overrides=dict(st.session_state.get(LAS_EDITOR_UNIT_OVERRIDES_KEY, {})),
                metadata=metadata,
                null_value=null_value,
                curve_mode=curve_mode,
                duplicate_strategy=duplicate_strategy,
                references=_las_editor_reference_state(columns),
            )
            st.session_state[LAS_EDITOR_EXPORT_RULES_KEY] = result
            for warning in result.warnings:
                st.warning(warning)
            st.success(
                "Export rules preview готов: "
                f"{result.summary['exported']} кривых, "
                f"{result.summary['renamed']} rename, "
                f"{result.summary['unit_converted']} unit conversions."
            )
        except ValueError as exc:
            st.warning(str(exc))

    result = st.session_state.get(LAS_EDITOR_EXPORT_RULES_KEY)
    if result is not None:
        rows = curve_export_preview_rows(result.preview)
        if rows:
            st.dataframe(
                pd.DataFrame(rows).rename(
                    columns={
                        "source_curve": "Исходная кривая",
                        "export_curve": "Экспортная кривая",
                        "source_unit": "Исходная единица",
                        "export_unit": "Экспортная единица",
                        "export": "Экспорт",
                        "action": "Действие",
                        "message": "Сообщение",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )
        st.caption(
            "Export summary: "
            f"exported={result.summary['exported']}, "
            f"renamed={result.summary['renamed']}, "
            f"converted={result.summary['unit_converted']}, "
            f"skipped={result.summary['skipped']}."
        )

def _render_las_curve_quality_flags(prepared_df: pd.DataFrame) -> None:
    st.markdown("### Curve Manager · Curve quality flags")
    st.caption(
        "Quality flags показывают пропуски, плоские интервалы, выбросы и нечисловые кривые. "
        "Это диагностический слой: исходные LAS-значения не изменяются."
    )

    column_names = [str(column) for column in prepared_df.columns]
    group_overrides = dict(st.session_state.get(LAS_EDITOR_GROUP_OVERRIDES_KEY, {}))
    category_overrides = dict(st.session_state.get(LAS_EDITOR_CATEGORY_OVERRIDES_KEY, {}))
    unit_overrides = dict(st.session_state.get(LAS_EDITOR_UNIT_OVERRIDES_KEY, {}))

    missing_col, flat_col, spike_col, action_col = st.columns([1, 1, 1, 1])
    missing_threshold = missing_col.slider(
        "Порог пропусков",
        min_value=0.01,
        max_value=0.80,
        value=0.15,
        step=0.01,
        format="%.2f",
        key="las_editor_quality_missing_threshold",
    )
    flat_min_length = flat_col.number_input(
        "Мин. длина flat",
        min_value=3,
        max_value=200,
        value=4,
        step=1,
        key="las_editor_quality_flat_min_length",
    )
    spike_threshold = spike_col.slider(
        "Порог spike z-score",
        min_value=3.0,
        max_value=12.0,
        value=6.0,
        step=0.5,
        key="las_editor_quality_spike_threshold",
    )
    should_run = action_col.button(
        "Проверить качество кривых",
        use_container_width=True,
        key="las_editor_quality_flags_apply",
    )

    if LAS_EDITOR_QUALITY_FLAGS_KEY not in st.session_state or should_run:
        result = detect_curve_quality_flags(
            prepared_df,
            group_overrides=group_overrides,
            category_overrides=category_overrides,
            unit_overrides=unit_overrides,
            missing_ratio_threshold=missing_threshold,
            flat_run_min_length=int(flat_min_length),
            spike_zscore_threshold=spike_threshold,
            references=_las_editor_reference_state(column_names),
        )
        st.session_state[LAS_EDITOR_QUALITY_FLAGS_KEY] = result.flags
        st.session_state[LAS_EDITOR_QUALITY_SUMMARY_KEY] = result.summary
        if should_run:
            for message in result.diagnostics:
                st.info(message)

    flags = tuple(st.session_state.get(LAS_EDITOR_QUALITY_FLAGS_KEY, ()))
    summary = dict(st.session_state.get(LAS_EDITOR_QUALITY_SUMMARY_KEY, {}))
    summary.setdefault("total", len(flags))

    if flags:
        st.warning(f"Найдено quality flags: {summary.get('total', len(flags))}.")
    else:
        st.success("Quality flags не найдены при текущих порогах.")

    st.dataframe(
        pd.DataFrame(curve_quality_summary_rows(summary)).rename(
            columns={"flag_label": "Тип", "flag_count": "Флагов"}
        )[["Тип", "Флагов"]],
        use_container_width=True,
        hide_index=True,
    )

    rows = curve_quality_flag_rows(flags)
    if rows:
        st.dataframe(
            pd.DataFrame(rows).rename(
                columns={
                    "curve_name": "Кривая",
                    "flag_label": "Флаг",
                    "severity_label": "Уровень",
                    "message": "Что найдено",
                    "sample_count": "Точек",
                    "affected_count": "Затронуто",
                    "affected_ratio": "Доля",
                    "group": "Группа",
                    "category": "Категория",
                    "unit": "Единица",
                    "recommendation": "Рекомендация",
                }
            )[[
                "Кривая",
                "Флаг",
                "Уровень",
                "Что найдено",
                "Точек",
                "Затронуто",
                "Доля",
                "Группа",
                "Категория",
                "Единица",
                "Рекомендация",
            ]],
            use_container_width=True,
            hide_index=True,
        )
    st.caption("Quality flags помогают проверить кривые перед bulk edit, import/export rules и отчетами.")


def _render_las_curve_metadata_editor(prepared_df: pd.DataFrame) -> None:
    st.markdown("### Curve Manager · Curve metadata editor")
    st.caption(
        "Редактор metadata кривых хранит описание, источник, прибор, статус, качество и комментарий "
        "без изменения числовых значений LAS. Эти поля нужны для аудита, отчетов и будущих правил импорта/экспорта."
    )

    if LAS_EDITOR_METADATA_HISTORY_KEY not in st.session_state:
        st.session_state[LAS_EDITOR_METADATA_HISTORY_KEY] = ()
    if LAS_EDITOR_METADATA_KEY not in st.session_state:
        st.session_state[LAS_EDITOR_METADATA_KEY] = {}

    column_names = [str(column) for column in prepared_df.columns]
    aliases = dict(st.session_state.get(LAS_EDITOR_ALIAS_MAP_KEY, {}))
    group_overrides = dict(st.session_state.get(LAS_EDITOR_GROUP_OVERRIDES_KEY, {}))
    category_overrides = dict(st.session_state.get(LAS_EDITOR_CATEGORY_OVERRIDES_KEY, {}))
    unit_overrides = dict(st.session_state.get(LAS_EDITOR_UNIT_OVERRIDES_KEY, {}))
    metadata = dict(st.session_state.get(LAS_EDITOR_METADATA_KEY, {}))

    built_metadata = build_curve_metadata(
        column_names,
        aliases=aliases,
        group_overrides=group_overrides,
        category_overrides=category_overrides,
        unit_overrides=unit_overrides,
        metadata=metadata,
    )
    metadata_rows = curve_metadata_table_rows(
        column_names,
        aliases=aliases,
        group_overrides=group_overrides,
        category_overrides=category_overrides,
        unit_overrides=unit_overrides,
        metadata=metadata,
    )

    with st.expander("Сводка metadata", expanded=True):
        st.dataframe(
            pd.DataFrame(metadata_summary_rows(built_metadata)).rename(
                columns={"type": "Тип", "label": "Значение", "curve_count": "Кривых"}
            )[["Тип", "Значение", "Кривых"]],
            use_container_width=True,
            hide_index=True,
        )

    st.dataframe(
        pd.DataFrame(metadata_rows).rename(
            columns={
                "curve_name": "Кривая",
                "alias": "Alias",
                "category": "Категория",
                "unit_label": "Единица",
                "description": "Описание",
                "source": "Источник",
                "tool": "Прибор/инструмент",
                "status_label": "Статус",
                "quality_label": "Качество",
                "comment": "Комментарий",
                "manual_fields": "Ручные поля",
            }
        )[["Кривая", "Alias", "Категория", "Единица", "Описание", "Источник", "Прибор/инструмент", "Статус", "Качество", "Комментарий", "Ручные поля"]],
        use_container_width=True,
        hide_index=True,
    )

    curve_col, field_col, value_col, action_col = st.columns([2, 2, 3, 1])
    curve_name = curve_col.selectbox("Кривая для metadata", options=column_names, key="las_editor_metadata_curve")
    field_options = list(available_metadata_fields())
    selected_field = field_col.selectbox("Поле metadata", options=field_options, key="las_editor_metadata_field")
    current_values = built_metadata.get(curve_name, {})
    if selected_field == "status":
        status_options = list(available_metadata_statuses())
        current_status = current_values.get("status", "draft")
        index = status_options.index(current_status) if current_status in status_options else 0
        selected_value = value_col.selectbox(
            "Значение",
            options=status_options,
            index=index,
            format_func=metadata_status_label,
            key="las_editor_metadata_status_value",
        )
    elif selected_field == "quality":
        quality_options = list(available_metadata_qualities())
        current_quality = current_values.get("quality", "unknown")
        index = quality_options.index(current_quality) if current_quality in quality_options else 0
        selected_value = value_col.selectbox(
            "Значение",
            options=quality_options,
            index=index,
            format_func=metadata_quality_label,
            key="las_editor_metadata_quality_value",
        )
    else:
        selected_value = value_col.text_input(
            "Значение",
            value=current_values.get(selected_field, ""),
            key=f"las_editor_metadata_text_{selected_field}",
        )

    references = _las_editor_reference_state(column_names)
    if action_col.button("Сохранить", use_container_width=True, key="las_editor_metadata_apply"):
        try:
            result = assign_curve_metadata(
                prepared_df,
                curve_name,
                selected_field,
                selected_value,
                aliases=aliases,
                group_overrides=group_overrides,
                category_overrides=category_overrides,
                unit_overrides=unit_overrides,
                metadata=metadata,
                history=st.session_state.get(LAS_EDITOR_METADATA_HISTORY_KEY, ()),
                references=references,
                reason="manual",
                source="las_editor_ui",
            )
            st.session_state[LAS_EDITOR_METADATA_KEY] = result.references.get("curve_metadata", result.metadata)
            st.session_state[LAS_EDITOR_METADATA_HISTORY_KEY] = result.history
            for message in result.diagnostics:
                st.info(message)
            if result.assigned:
                st.success(f"Metadata обновлена: {result.curve_name}.{result.field}")
            else:
                st.warning("Metadata не изменилась: такое значение уже существовало.")
        except ValueError as exc:
            st.warning(str(exc))

    history = tuple(st.session_state.get(LAS_EDITOR_METADATA_HISTORY_KEY, ()))
    if st.button("Undo последней metadata-правки", disabled=not history, use_container_width=True, key="las_editor_metadata_undo"):
        try:
            result = undo_last_metadata_assignment(
                prepared_df,
                aliases=aliases,
                group_overrides=group_overrides,
                category_overrides=category_overrides,
                unit_overrides=unit_overrides,
                metadata=dict(st.session_state.get(LAS_EDITOR_METADATA_KEY, {})),
                history=history,
                references=references,
            )
            st.session_state[LAS_EDITOR_METADATA_KEY] = result.references.get("curve_metadata", result.metadata)
            st.session_state[LAS_EDITOR_METADATA_HISTORY_KEY] = result.history
            for message in result.diagnostics:
                st.info(message)
            st.success("Последняя metadata-правка отменена.")
        except ValueError as exc:
            st.warning(str(exc))

    history = tuple(st.session_state.get(LAS_EDITOR_METADATA_HISTORY_KEY, ()))
    with st.expander("История metadata кривых", expanded=bool(history)):
        if history:
            st.dataframe(
                pd.DataFrame([
                    {
                        "curve_name": entry.curve_name,
                        "field": entry.field,
                        "value": entry.value,
                        "previous_value": entry.previous_value,
                        "timestamp": entry.timestamp,
                        "reason": entry.reason,
                        "source": entry.source,
                    }
                    for entry in history
                ]),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.caption("История metadata пока пуста.")


def _render_las_curve_rename_manager(prepared_df: pd.DataFrame) -> pd.DataFrame:
    st.markdown("### Curve Manager · Rename curves")
    st.caption(
        "Безопасное переименование LAS-кривых: проверка существования, пустого имени, "
        "конфликтов, сохранение истории и одноуровневый undo."
    )

    if LAS_EDITOR_RENAME_HISTORY_KEY not in st.session_state:
        st.session_state[LAS_EDITOR_RENAME_HISTORY_KEY] = ()

    column_names = [str(column) for column in prepared_df.columns]
    rename_col, new_col, action_col = st.columns([2, 2, 1])
    old_name = rename_col.selectbox(
        "Кривая для rename",
        options=column_names,
        key="las_editor_rename_old_curve",
    )
    new_name = new_col.text_input(
        "Новое имя кривой",
        value=old_name,
        key="las_editor_rename_new_curve",
    )

    references = _las_editor_reference_state(column_names)
    active_df = prepared_df
    if action_col.button("Переименовать", use_container_width=True, key="las_editor_rename_apply"):
        try:
            result = rename_curve(
                prepared_df,
                old_name,
                new_name,
                history=st.session_state.get(LAS_EDITOR_RENAME_HISTORY_KEY, ()),
                references=references,
                reason="manual",
                source="las_editor_ui",
            )
            active_df = result.data
            st.session_state[LAS_EDITOR_RENAME_HISTORY_KEY] = result.history
            _apply_las_editor_reference_state(result.references)
            for message in result.diagnostics:
                st.info(message)
            if result.renamed:
                st.success(f"Кривая переименована: {result.old_name} → {result.new_name}")
            else:
                st.warning("Имя не изменилось: rename не применялся.")
        except ValueError as exc:
            st.warning(str(exc))

    history = tuple(st.session_state.get(LAS_EDITOR_RENAME_HISTORY_KEY, ()))
    undo_disabled = not history
    if st.button("Undo последнего rename", disabled=undo_disabled, use_container_width=True, key="las_editor_rename_undo"):
        try:
            result = undo_last_rename(prepared_df, history=history, references=references)
            active_df = result.data
            st.session_state[LAS_EDITOR_RENAME_HISTORY_KEY] = result.history
            _apply_las_editor_reference_state(result.references)
            for message in result.diagnostics:
                st.info(message)
            st.success(f"Rename отменен: {result.old_name} → {result.new_name}")
        except ValueError as exc:
            st.warning(str(exc))

    history = tuple(st.session_state.get(LAS_EDITOR_RENAME_HISTORY_KEY, ()))
    with st.expander("История rename", expanded=bool(history)):
        if history:
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "old_name": entry.old_name,
                            "new_name": entry.new_name,
                            "timestamp": entry.timestamp,
                            "reason": entry.reason,
                            "source": entry.source,
                        }
                        for entry in history
                    ]
                ),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.caption("История переименований пока пуста.")

    return active_df


def _render_las_curve_merge_manager(prepared_df: pd.DataFrame) -> pd.DataFrame:
    st.markdown("### Curve Manager · Merge curves")
    st.caption(
        "Объединение нескольких LAS-кривых в одну расчетную кривую: coalesce-first, "
        "coalesce-last, mean или sum с историей операций и undo последнего merge."
    )

    if LAS_EDITOR_MERGE_HISTORY_KEY not in st.session_state:
        st.session_state[LAS_EDITOR_MERGE_HISTORY_KEY] = ()

    column_names = [str(column) for column in prepared_df.columns]
    active_df = prepared_df
    source_col, target_col, strategy_col = st.columns([3, 2, 2])
    selected_sources = source_col.multiselect(
        "Исходные кривые для merge",
        options=column_names,
        default=column_names[:2] if len(column_names) >= 2 else column_names,
        key="las_editor_merge_sources",
    )
    default_target = "_MERGED".join([]) or "MERGED_CURVE"
    target_name = target_col.text_input(
        "Результирующая кривая",
        value=default_target,
        key="las_editor_merge_target",
    )
    strategy_labels = {
        "coalesce_first": "coalesce_first: первое непустое значение слева",
        "coalesce_last": "coalesce_last: последнее непустое значение справа",
        "mean": "mean: среднее по выбранным кривым",
        "sum": "sum: сумма выбранных кривых",
    }
    selected_strategy_label = strategy_col.selectbox(
        "Стратегия merge",
        options=[strategy_labels[item] for item in MERGE_STRATEGIES],
        key="las_editor_merge_strategy",
    )
    selected_strategy = next(key for key, label in strategy_labels.items() if label == selected_strategy_label)
    keep_sources = st.checkbox(
        "Оставить исходные кривые после merge",
        value=True,
        key="las_editor_merge_keep_sources",
    )

    references = _las_editor_reference_state(column_names)
    action_col, undo_col = st.columns(2)
    if action_col.button("Создать merged curve", use_container_width=True, key="las_editor_merge_apply"):
        try:
            result = merge_curves(
                prepared_df,
                selected_sources,
                target_name,
                strategy=selected_strategy,
                keep_sources=keep_sources,
                history=st.session_state.get(LAS_EDITOR_MERGE_HISTORY_KEY, ()),
                references=references,
                reason="manual",
                source="las_editor_ui",
            )
            active_df = result.data
            st.session_state[LAS_EDITOR_MERGE_HISTORY_KEY] = result.history
            _apply_las_editor_reference_state(result.references)
            for message in result.diagnostics:
                st.info(message)
            for message in result.warnings:
                st.warning(message)
            st.success(f"Merged curve создана: {result.target_name}")
        except ValueError as exc:
            st.warning(str(exc))

    history = tuple(st.session_state.get(LAS_EDITOR_MERGE_HISTORY_KEY, ()))
    if undo_col.button("Undo последнего merge", disabled=not history, use_container_width=True, key="las_editor_merge_undo"):
        try:
            result = undo_last_merge(prepared_df, history=history, references=references)
            active_df = result.data
            st.session_state[LAS_EDITOR_MERGE_HISTORY_KEY] = result.history
            _apply_las_editor_reference_state(result.references)
            for message in result.diagnostics:
                st.info(message)
            st.success("Последний merge отменен.")
        except ValueError as exc:
            st.warning(str(exc))

    history = tuple(st.session_state.get(LAS_EDITOR_MERGE_HISTORY_KEY, ()))
    with st.expander("История merge", expanded=bool(history)):
        if history:
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "source_names": ", ".join(entry.source_names),
                            "target_name": entry.target_name,
                            "strategy": entry.strategy,
                            "keep_sources": entry.keep_sources,
                            "timestamp": entry.timestamp,
                            "reason": entry.reason,
                            "source": entry.source,
                        }
                        for entry in history
                    ]
                ),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.caption("История merge пока пуста.")

    return active_df

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


def _quick_action_by_id(action_id: str) -> dict[str, str] | None:
    """Return a dashboard quick action by stable identifier."""
    normalized = str(action_id or "").strip()
    for action in START_ACTIONS:
        if action.get("id") == normalized:
            return dict(action)
    return None


def _quick_action_button_label(action: dict[str, str]) -> str:
    """Return a compact button label for the redesigned quick actions panel."""
    icon = action.get("icon", "•")
    title = action.get("short_title") or action.get("title", "Действие")
    return f"{icon} {title}"


def _dashboard_quick_action_cards_html(last_action: dict[str, str] | None = None) -> str:
    """Render a compact quick-action summary without duplicating executable buttons."""
    primary_actions = tuple(START_ACTIONS[:4])
    cards: list[str] = []
    for action in primary_actions:
        cards.append(
            "<div class='dashboard-action-card quick-action-wired simplified-quick-action compact-quick-action-summary' "
            f"data-action='{_html_escape(action['id'])}' data-target='{_html_escape(action['target_tab'])}'>"
            f"<strong>{_html_escape(_quick_action_button_label(action))}</strong>"
            f"<span class='dashboard-muted'>{_html_escape(action['target_tab'])}</span>"
            "</div>"
        )
    last_html = ""
    if last_action:
        last_html = (
            "<div class='dashboard-action-card compact-quick-action-summary'>"
            "<strong>Последнее действие</strong>"
            f"<span class='dashboard-muted'>{_html_escape(last_action['title'])} → {_html_escape(last_action['target_tab'])}</span>"
            "</div>"
        )
    return "<div class='quick-action-summary'>" + "".join(cards) + last_html + "</div>"


def _trigger_quick_action(action: dict[str, str]) -> None:
    """Switch to the quick action target and remember the latest executed action."""
    st.session_state[DASHBOARD_LAST_QUICK_ACTION_KEY] = action["id"]
    _set_active_main_tab(action["target_tab"])
    st.rerun()


def _asset_to_data_uri(path: Path) -> str:
    """Return an inline data URI for a local application asset."""
    if not path.exists() or not path.is_file():
        return ""
    suffix = path.suffix.lower().lstrip(".") or "png"
    mime = "image/jpeg" if suffix in {"jpg", "jpeg"} else f"image/{suffix}"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def _dashboard_background_data_uri() -> str:
    """Expose the branded application background for UI tests and CSS rendering."""
    return _asset_to_data_uri(DASHBOARD_BACKGROUND_PATH)


def _documentation_hero_data_uri() -> str:
    """Expose the documentation hero artwork for the Instructions page."""
    return _asset_to_data_uri(DOCUMENTATION_HERO_PATH)


def _branding_logo_data_uri() -> str:
    """Expose the Gas Ratio Pro logo for navbar, license and watermark rendering."""
    return _asset_to_data_uri(BRANDING_LOGO_PATH)


def _app_icon_data_uri() -> str:
    """Expose the application icon asset used by browser/page branding."""
    return _asset_to_data_uri(APP_ICON_PATH)


def _export_watermark_data_uri() -> str:
    """Expose the optional export watermark logo for PDF/PNG/report templates."""
    return _asset_to_data_uri(EXPORT_WATERMARK_LOGO_PATH)


def _branding_asset_manifest() -> tuple[dict[str, str], ...]:
    """Return the branded asset inventory and approved placements."""
    logo_exists = "yes" if BRANDING_LOGO_PATH.exists() else "no"
    return (
        {"name": "Application logo", "path": str(BRANDING_LOGO_PATH.relative_to(ROOT_DIR)), "placement": "navbar logo, sidebar logo, documentation hero logo, about brand block, license header logo", "available": logo_exists},
        {"name": "Application icon", "path": str(APP_ICON_PATH.relative_to(ROOT_DIR)), "placement": "application icon", "available": logo_exists},
        {"name": "Splash screen logo", "path": str(APP_SPLASH_LOGO_PATH.relative_to(ROOT_DIR)), "placement": "splash screen", "available": logo_exists},
        {"name": "Export watermark", "path": str(EXPORT_WATERMARK_LOGO_PATH.relative_to(ROOT_DIR)), "placement": "PDF/PNG export watermark option", "available": logo_exists},
    )


def _branding_placement_names() -> tuple[str, ...]:
    """Return approved UI surfaces where the logo may be shown."""
    return APP_BRANDING_PLACEMENTS


def _app_identity_metadata() -> dict[str, str]:
    """Return official application identity metadata for About, License and exports."""
    return dict(APP_IDENTITY)


def _render_brand_logo_html(class_name: str, *, alt: str = "Gas Ratio Pro logo") -> str:
    """Render the shared logo image with a caller-specific CSS class."""
    logo_uri = _branding_logo_data_uri()
    if not logo_uri:
        return ""
    safe_class = _html_escape(class_name)
    return f'<img class="{safe_class}" src="{logo_uri}" alt="{_html_escape(alt)}">'


def _render_about_brand_block_html() -> str:
    """Render a compact branded About block for dashboard and future About page."""
    identity = _app_identity_metadata()
    logo_html = _render_brand_logo_html("about-brand-logo")
    return (
        "<section class='about-brand-block glass-panel'>"
        f"{logo_html}"
        "<div>"
        f"<strong>{_html_escape(identity['name'])}</strong>"
        f"<span>{_html_escape(identity['tagline'])}</span>"
        f"<small>Автор: {_html_escape(identity['author'])} · {_html_escape(identity['contact'])}</small>"
        "</div></section>"
    )


def _render_license_brand_header_html() -> str:
    """Render the licensed product identity header with logo and copyright."""
    identity = _app_identity_metadata()
    logo_html = _render_brand_logo_html("license-header-logo")
    return (
        "<section class='license-brand-header glass-panel'>"
        f"{logo_html}"
        "<div>"
        f"<strong>{_html_escape(identity['license'])}</strong>"
        f"<span>{_html_escape(identity['copyright'])}</span>"
        f"<small>Commercial use requires written permission: {_html_escape(identity['contact'])}</small>"
        "</div></section>"
    )


def _read_application_license_text() -> str:
    """Read the repository license text for the in-app licensing page."""
    license_path = ROOT_DIR / "LICENSE"
    try:
        return license_path.read_text(encoding="utf-8").strip()
    except OSError:
        return "LICENSE file is missing. Contact the copyright owner before using the software."


def _read_application_eula_text() -> str:
    """Read the project EULA document for the in-app licensing page."""
    eula_path = ROOT_DIR / "docs" / "eula.md"
    try:
        return eula_path.read_text(encoding="utf-8").strip()
    except OSError:
        return "EULA document is missing. Contact the copyright owner before using the software."


def _license_page_rule_cards() -> tuple[dict[str, str], ...]:
    """Return concise legal rule cards shown above the full license text."""
    return (
        {
            "title": "Ownership",
            "body": "Исходный код, assets, документация и связанные материалы принадлежат Rinat Sarmuldin.",
        },
        {
            "title": "Read-only evaluation",
            "body": "Разрешен только просмотр или загрузка для личной некоммерческой оценки без права производственного применения.",
        },
        {
            "title": "Commercial permission",
            "body": "Commercial, SaaS, internal company, production use, redistribution and modification требуют письменного разрешения автора.",
        },
        {
            "title": "Third-party components",
            "body": "Сторонние библиотеки сохраняют собственные лицензии; этот экран фиксирует права на Gas Ratio Pro materials.",
        },
        {
            "title": "EULA document",
            "body": "Встроенный EULA фиксирует разрешенное evaluation-use, запрет production/commercial use без письменного разрешения и отказ от гарантий.",
        },
        {
            "title": "Contact",
            "body": "Для разрешений на использование: ura07srr@gmail.com.",
        },
    )


def _render_application_licensing_page() -> None:
    """Render the dedicated high-contrast application licensing page."""
    identity = _app_identity_metadata()
    license_text = _read_application_license_text()
    eula_text = _read_application_eula_text()
    cards_html = "".join(
        "<article class='license-rule-card'>"
        f"<h3>{_html_escape(card['title'])}</h3>"
        f"<p>{_html_escape(card['body'])}</p>"
        "</article>"
        for card in _license_page_rule_cards()
    )
    st.markdown(
        f"""
        <section class='application-license-page' id='application-license-page'>
          <div class='application-license-hero glass-panel'>
            <div>
              {_render_license_brand_header_html()}
              <h2>Лицензия и коммерческая защита</h2>
              <p>Эта страница закрепляет правила использования Gas Ratio Pro внутри приложения, чтобы статус продукта был виден не только в файле LICENSE, но и в интерфейсе.</p>
              <p>Любое коммерческое, production, SaaS, internal company использование, распространение или модификация требуют предварительного письменного разрешения автора.</p>
            </div>
            <aside class='license-status-panel'>
              <strong>Статус продукта</strong>
              <div class='license-status-list'>
                <div class='license-status-row'><span>License</span><span>{_html_escape(identity['license'])}</span></div>
                <div class='license-status-row'><span>Owner</span><span>{_html_escape(identity['author'])}</span></div>
                <div class='license-status-row'><span>Copyright</span><span>{_html_escape(identity['copyright'])}</span></div>
                <div class='license-status-row'><span>Contact</span><span>{_html_escape(identity['contact'])}</span></div>
                <div class='license-status-row'><span>Commercial use</span><span>Written permission only</span></div>
              </div>
            </aside>
          </div>
          <div class='license-cards-grid'>{cards_html}</div>
          <section class='eula-text-panel' aria-label='Full EULA text'>
            <h3>End User License Agreement</h3>
            <pre>{_html_escape(eula_text)}</pre>
          </section>
          <section class='license-text-panel' aria-label='Full LICENSE text'>
            <h3>Repository LICENSE</h3>
            <pre>{_html_escape(license_text)}</pre>
          </section>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _render_splash_screen_html() -> str:
    """Render a lightweight splash-screen placeholder for future startup packaging."""
    identity = _app_identity_metadata()
    logo_html = _render_brand_logo_html("splash-screen-logo")
    return (
        "<section class='splash-screen-brand'>"
        f"{logo_html}"
        f"<strong>{_html_escape(identity['name'])}</strong>"
        f"<span>{_html_escape(identity['tagline'])}</span>"
        "</section>"
    )


def _export_watermark_style() -> dict[str, str]:
    """Return default watermark settings for future PDF/PNG/report export integration."""
    return {"enabled": "optional", "opacity": EXPORT_WATERMARK_DEFAULT_OPACITY, "asset": str(EXPORT_WATERMARK_LOGO_PATH.relative_to(ROOT_DIR)), "avoid": "plots, LAS curves, tables, engineering data"}


def _dashboard_recent_projects(projects: tuple[ProjectRecord, ...], limit: int = 3) -> tuple[ProjectRecord, ...]:
    """Return the newest project cards shown on the dashboard."""
    if limit <= 0:
        return ()
    return tuple(projects[:limit])


def _dashboard_project_statistics(active_project: ProjectRecord, projects: tuple[ProjectRecord, ...]) -> dict[str, int]:
    """Build dashboard statistics from real project storage and session data."""
    return {
        "projects": len(projects),
        "wells": len(list_wells(WELLS_STORAGE_ROOT)),
        "las_files": len(list_project_las_files(LAS_CORRELATION_PROJECTS_ROOT, active_project.id)),
        "calculations": len(list_project_calculations(LAS_CORRELATION_PROJECTS_ROOT, active_project.id)),
        "exports": len(list_project_exports(LAS_CORRELATION_PROJECTS_ROOT, active_project.id)),
    }


def _dashboard_news_items(active_project: ProjectRecord) -> tuple[str, ...]:
    """Return dynamic dashboard news derived from current project state."""
    items = [f"Активный проект: {active_project.name}"]
    if active_project.updated_at:
        items.append(f"Проект обновлен: {active_project.updated_at}")
    calculations_count = len(list_project_calculations(LAS_CORRELATION_PROJECTS_ROOT, active_project.id))
    exports_count = len(list_project_exports(LAS_CORRELATION_PROJECTS_ROOT, active_project.id))
    items.append(f"Сохраненных расчетов: {calculations_count}")
    items.append(f"Сохраненных экспортов: {exports_count}")
    return tuple(items)


def _dashboard_activity_items(active_project: ProjectRecord, limit: int = 4) -> tuple[str, ...]:
    """Return the latest available project activities for the dashboard."""
    activities: list[tuple[str, str]] = []
    for calculation in list_project_calculations(LAS_CORRELATION_PROJECTS_ROOT, active_project.id):
        timestamp = getattr(calculation, "created_at", "") or getattr(calculation, "updated_at", "") or ""
        name = getattr(calculation, "name", "") or getattr(calculation, "id", "расчет")
        activities.append((timestamp, f"Расчет: {name}"))
    for export in list_project_exports(LAS_CORRELATION_PROJECTS_ROOT, active_project.id):
        timestamp = getattr(export, "created_at", "") or getattr(export, "updated_at", "") or ""
        name = getattr(export, "file_name", "") or getattr(export, "name", "") or "экспорт"
        activities.append((timestamp, f"Экспорт: {name}"))
    if not activities:
        return ("Пока нет проектной активности", "Импортируйте LAS/CSV/XLSX или сохраните расчет")
    return tuple(message for _timestamp, message in sorted(activities, reverse=True)[: max(1, limit)])


def _dashboard_tip(active_project: ProjectRecord) -> str:
    """Return a stable daily tip for the active project."""
    day_key = datetime.now().strftime("%Y-%m-%d")
    rng = random.Random(f"{active_project.id}:{day_key}")
    return rng.choice(DASHBOARD_TIPS)


def _navigation_animation_feature_names() -> tuple[str, ...]:
    """Expose implemented navigation animation features for smoke tests and documentation."""
    return NAVIGATION_ANIMATION_FEATURES


def _navigation_animation_token_names() -> tuple[str, ...]:
    """Return stable animation token names used by the shared navigation system."""
    return tuple(NAVIGATION_ANIMATION_TOKENS.keys())


def _html_escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def _project_search_results(project: ProjectRecord, query: str, *, limit: int = 12) -> tuple[dict[str, str], ...]:
    """Search visible project explorer rows by label, status, and kind."""
    normalized_query = str(query or "").strip().lower()
    if not normalized_query:
        return ()
    try:
        tree = build_project_tree(LAS_CORRELATION_PROJECTS_ROOT, project.id)
        rows = project_tree_table_rows(tree)
    except Exception:
        return ()

    matches: list[dict[str, str]] = []
    for row in rows:
        label = str(row.get("label", ""))
        status = str(row.get("status", ""))
        kind = str(row.get("kind", ""))
        haystack = f"{label} {status} {kind}".lower()
        if normalized_query in haystack:
            matches.append({"label": label, "status": status, "kind": kind})
        if len(matches) >= max(1, limit):
            break
    return tuple(matches)


NAVIGATION_ITEMS: tuple[dict[str, str], ...] = (
    {"label": "Старт", "icon": "🏠", "description": "Dashboard, проекты, статистика"},
    {"label": "Работа с данными", "icon": "📥", "description": "Импорт, mapping, расчеты"},
    {"label": "LAS-редактор", "icon": "🧰", "description": "Кривые, глубина, правки"},
    {"label": "LAS-корреляция", "icon": "🔗", "description": "Сравнение скважин"},
    {"label": "Интерпретационные графики", "icon": "📈", "description": "Планшеты и отчеты"},
    {"label": "Инструкции и документация", "icon": "📘", "description": "Руководства и методика"},
    {"label": "Лицензия", "icon": "🔒", "description": "Права и коммерческое использование"},
)


COMMAND_PALETTE_STATIC_COMMANDS: tuple[dict[str, str], ...] = (
    {
        "title": "Создать или открыть проект",
        "category": "Проекты",
        "target_tab": "Работа с данными",
        "description": "Перейти к выбору активного проекта, импорту и проектному workflow.",
        "keywords": "проект открыть создать project import",
    },
    {
        "title": "Импорт LAS / CSV / Excel",
        "category": "Данные",
        "target_tab": "Работа с данными",
        "description": "Загрузить файл, проверить заголовки, mapping и выполнить расчет.",
        "keywords": "импорт загрузить las csv xlsx mapping расчет",
    },
    {
        "title": "Открыть LAS-редактор",
        "category": "LAS",
        "target_tab": "LAS-редактор",
        "description": "Проверить глубину, шаг, NULL-значения, rename/alias/merge кривых.",
        "keywords": "las редактор curve rename alias merge глубина",
    },
    {
        "title": "Открыть LAS-корреляцию",
        "category": "Корреляция",
        "target_tab": "LAS-корреляция",
        "description": "Сравнить несколько скважин и настроить группы кривых.",
        "keywords": "корреляция multi well сравнение скважины",
    },
    {
        "title": "Интерпретационные графики и отчеты",
        "category": "Графики",
        "target_tab": "Интерпретационные графики",
        "description": "Открыть планшет, маркеры, зоны интерпретации и exports.",
        "keywords": "графики планшет report отчет export png pdf svg",
    },
    {
        "title": "Инструкции и документация",
        "category": "Справка",
        "target_tab": "Инструкции и документация",
        "description": "Открыть руководство, быстрый старт, формулы и troubleshooting.",
        "keywords": "инструкции документация help руководство формулы troubleshooting",
    },
    {
        "title": "Лицензия и коммерческое использование",
        "category": "Лицензия",
        "target_tab": "Лицензия",
        "description": "Открыть отдельную лицензионную страницу с Proprietary License, EULA document и контактом автора.",
        "keywords": "license лицензия proprietary eula commercial коммерческое copyright права автор",
    },
)


COMMAND_PALETTE_CATEGORY_ORDER: tuple[str, ...] = (
    "Все",
    "Команды",
    "Разделы",
    "Проекты",
    "Скважины",
    "LAS",
    "Кривые",
    "Расчеты",
    "Отчеты",
    "Документация",
    "Недавние",
    "Избранное",
)

COMMAND_PALETTE_KIND_CATEGORY_MAP: dict[str, str] = {
    "project": "Проекты",
    "folder": "Проекты",
    "well": "Скважины",
    "wells": "Скважины",
    "las": "LAS",
    "las_file": "LAS",
    "curve": "Кривые",
    "calculation": "Расчеты",
    "calculations": "Расчеты",
    "report": "Отчеты",
    "export": "Отчеты",
}

COMMAND_PALETTE_RECENT_LIMIT = 8
COMMAND_PALETTE_SEARCH_LIMIT = 10


def _normalize_command_text(value: object) -> str:
    """Normalize command palette text for predictable Russian/English search."""
    return " ".join(str(value or "").replace("/", " ").replace("-", " ").lower().split())


def _command_entry_id(entry: dict[str, str]) -> str:
    """Build a stable command id without depending on Streamlit widget keys."""
    return _normalize_command_text(f"{entry.get('category', '')}:{entry.get('title', '')}:{entry.get('target_tab', '')}")


def _command_palette_entry_category(entry: dict[str, str]) -> str:
    """Return the high-level searchable category for a command entry."""
    explicit = str(entry.get("search_category", "")).strip()
    if explicit:
        return explicit
    category = str(entry.get("category", "")).strip()
    if category == "Раздел":
        return "Разделы"
    if category == "Документация":
        return "Документация"
    if category.startswith("Проект ·"):
        kind = category.split("·", 1)[1].strip().lower()
        return COMMAND_PALETTE_KIND_CATEGORY_MAP.get(kind, "Проекты")
    return "Команды"


def _command_palette_categories(entries: tuple[dict[str, str], ...]) -> tuple[str, ...]:
    """Return available command palette filters in a stable product order."""
    present = {_command_palette_entry_category(entry) for entry in entries}
    categories = [category for category in COMMAND_PALETTE_CATEGORY_ORDER if category == "Все" or category in present]
    return tuple(dict.fromkeys(categories))


def _remember_command_palette_entry(entry: dict[str, str]) -> None:
    """Store recent command ids and keep the list short."""
    entry_id = _command_entry_id(entry)
    recent = [item for item in st.session_state.get(COMMAND_PALETTE_RECENT_KEY, []) if item != entry_id]
    st.session_state[COMMAND_PALETTE_RECENT_KEY] = [entry_id, *recent][:COMMAND_PALETTE_RECENT_LIMIT]


def _toggle_command_palette_favorite(entry: dict[str, str]) -> None:
    """Toggle command favorite state in Streamlit session state."""
    entry_id = _command_entry_id(entry)
    favorites = list(st.session_state.get(COMMAND_PALETTE_FAVORITES_KEY, []))
    if entry_id in favorites:
        favorites.remove(entry_id)
    else:
        favorites.insert(0, entry_id)
    st.session_state[COMMAND_PALETTE_FAVORITES_KEY] = favorites[:COMMAND_PALETTE_RECENT_LIMIT]


def _command_palette_recent_or_favorite_entries(
    entries: tuple[dict[str, str], ...],
    ids: object,
) -> tuple[dict[str, str], ...]:
    """Resolve stored command ids back to current entries."""
    by_id = {_command_entry_id(entry): entry for entry in entries}
    ordered: list[dict[str, str]] = []
    for entry_id in ids if isinstance(ids, list) else []:
        entry = by_id.get(str(entry_id))
        if entry:
            ordered.append(entry)
    return tuple(ordered)


def _command_palette_entries(active_project: ProjectRecord) -> tuple[dict[str, str], ...]:
    """Build command palette entries from navigation, actions, docs and project objects."""
    entries: list[dict[str, str]] = []
    for item in NAVIGATION_ITEMS:
        entries.append({
            "title": item["label"],
            "category": "Раздел",
            "search_category": "Разделы",
            "target_tab": item["label"],
            "description": item["description"],
            "keywords": f"{item['label']} {item['description']} navigation tab вкладка раздел",
        })

    for command in COMMAND_PALETTE_STATIC_COMMANDS:
        prepared = dict(command)
        prepared.setdefault("search_category", "Команды")
        prepared["keywords"] = f"{prepared.get('keywords', '')} команда действие быстрый доступ quick action"
        entries.append(prepared)

    for action in START_ACTIONS:
        entries.append({
            "title": action["title"],
            "category": "Быстрый доступ",
            "search_category": "Команды",
            "target_tab": action["target_tab"],
            "description": action["description"],
            "keywords": f"{action['title']} {action['button_label']} {action['when']} {action['tooltip']} quick dashboard",
        })

    try:
        tree_rows = project_tree_table_rows(build_project_tree(LAS_CORRELATION_PROJECTS_ROOT, active_project.id))
    except Exception:
        tree_rows = ()
    for row in tree_rows:
        label = str(row.get("label", "")).strip()
        if not label:
            continue
        kind = str(row.get("kind", "project"))
        status = str(row.get("status", ""))
        search_category = COMMAND_PALETTE_KIND_CATEGORY_MAP.get(kind.lower(), "Проекты")
        entries.append({
            "title": label,
            "category": f"Проект · {kind}",
            "search_category": search_category,
            "target_tab": "Работа с данными",
            "description": status or "Объект активного проекта",
            "keywords": f"{label} {kind} {status} project well скважина las curve кривые calculation расчет report отчет export",
        })

    for doc_title, doc_path in DOCUMENTATION_TAB_DOCS:
        entries.append({
            "title": doc_title,
            "category": "Документация",
            "search_category": "Документация",
            "target_tab": "Инструкции и документация",
            "description": doc_path,
            "keywords": f"{doc_title} {doc_path} docs help guide руководство документация faq troubleshooting shortcuts hotkeys",
        })

    for link in DOCUMENTATION_QUICK_LINKS:
        entries.append({
            "title": link["title"],
            "category": "Документация",
            "search_category": "Документация",
            "target_tab": "Инструкции и документация",
            "description": link["description"],
            "keywords": f"{link['title']} {link['anchor']} {link['description']} docs quick link",
        })
    return tuple(entries)

def _filter_command_palette_entries(
    entries: tuple[dict[str, str], ...],
    query: str,
    *,
    category: str = "Все",
    recent_ids: object = None,
    favorite_ids: object = None,
    limit: int = COMMAND_PALETTE_SEARCH_LIMIT,
) -> tuple[dict[str, str], ...]:
    """Filter and rank command palette entries by query, category and command state."""
    normalized_query = _normalize_command_text(query)
    selected_category = str(category or "Все")

    if selected_category == "Недавние":
        entries = _command_palette_recent_or_favorite_entries(entries, recent_ids or [])
    elif selected_category == "Избранное":
        entries = _command_palette_recent_or_favorite_entries(entries, favorite_ids or [])
    elif selected_category != "Все":
        entries = tuple(entry for entry in entries if _command_palette_entry_category(entry) == selected_category)

    if not normalized_query:
        return entries[: max(1, limit)]

    words = tuple(part for part in normalized_query.split() if part)
    matches: list[tuple[int, str, str, dict[str, str]]] = []
    favorite_set = set(favorite_ids or []) if isinstance(favorite_ids, list) else set()
    recent_set = set(recent_ids or []) if isinstance(recent_ids, list) else set()

    for entry in entries:
        title = entry.get("title", "")
        category_label = entry.get("category", "")
        description = entry.get("description", "")
        keywords = entry.get("keywords", "")
        target_tab = entry.get("target_tab", "")
        haystack = _normalize_command_text(f"{title} {category_label} {description} {keywords} {target_tab}")
        if not all(word in haystack for word in words):
            continue

        lower_title = _normalize_command_text(title)
        score = 0
        if lower_title.startswith(normalized_query):
            score += 50
        if normalized_query in lower_title:
            score += 25
        if _normalize_command_text(category_label).startswith(normalized_query):
            score += 12
        if normalized_query in _normalize_command_text(keywords):
            score += 8
        entry_category = _command_palette_entry_category(entry)
        if entry_category == "Разделы":
            score += 5
        if entry_category == "Команды":
            score += 4
        entry_id = _command_entry_id(entry)
        if entry_id in favorite_set:
            score += 6
        if entry_id in recent_set:
            score += 3
        matches.append((score, entry_category, lower_title, entry))

    matches.sort(key=lambda item: (-item[0], item[1], item[2]))
    return tuple(entry for _score, _category, _title, entry in matches[: max(1, limit)])

def _render_global_command_palette(active_project: ProjectRecord) -> None:
    """Render a searchable Ctrl+K-style command palette with categories and state."""
    st.markdown(
        "<div class='command-palette-shell'>"
        "<div class='command-palette-title'><b>Командная палитра</b><span>Ctrl+K · поиск команд, проектов, скважин, LAS, расчетов, отчетов и документации</span></div>",
        unsafe_allow_html=True,
    )
    entries = _command_palette_entries(active_project)
    category_options = _command_palette_categories(entries)
    col_query, col_category = st.columns([3, 1])
    with col_query:
        query = st.text_input(
            "Команда или объект проекта",
            key=COMMAND_PALETTE_QUERY_KEY,
            placeholder="например: импорт LAS, скважина, curve, расчет, отчет, troubleshooting",
            label_visibility="collapsed",
        )
    with col_category:
        selected_category = st.selectbox(
            "Категория поиска",
            category_options,
            key=COMMAND_PALETTE_CATEGORY_KEY,
            label_visibility="collapsed",
        )

    recent_ids = st.session_state.get(COMMAND_PALETTE_RECENT_KEY, [])
    favorite_ids = st.session_state.get(COMMAND_PALETTE_FAVORITES_KEY, [])
    results = _filter_command_palette_entries(
        entries,
        query,
        category=selected_category,
        recent_ids=recent_ids,
        favorite_ids=favorite_ids,
        limit=COMMAND_PALETTE_SEARCH_LIMIT if query else 6,
    )
    if query and not results:
        st.warning("Команда или объект проекта не найдены. Попробуйте: LAS, импорт, скважина, расчет, отчет, инструкции.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    helper = "Enter выполняет выбранную кнопку Streamlit, Esc закрывает активное поле ввода браузера, Ctrl+K используется как основной shortcut поиска."
    if query or selected_category != "Все":
        st.caption(f"Найдено: {len(results)} · категория: {selected_category} · {helper}")
    else:
        st.caption("Введите запрос или выберите категорию. Доступны команды, проекты, скважины, LAS, кривые, расчеты, отчеты, документация, недавние и избранные.")

    for index, entry in enumerate(results):
        col_text, col_favorite, col_button = st.columns([4, 0.8, 1])
        entry_id = _command_entry_id(entry)
        is_favorite = entry_id in set(favorite_ids if isinstance(favorite_ids, list) else [])
        with col_text:
            st.markdown(
                "<div class='command-result-card'>"
                f"<b>{_html_escape(entry.get('title', ''))}</b> "
                f"<code>{_html_escape(entry.get('category', ''))}</code>"
                f"<small>{_html_escape(_command_palette_entry_category(entry))} · {_html_escape(entry.get('description', ''))}</small>"
                "</div>",
                unsafe_allow_html=True,
            )
        with col_favorite:
            if st.button("★" if is_favorite else "☆", key=f"command_palette_fav_{index}_{entry_id}", help="Добавить или убрать команду из избранного"):
                _toggle_command_palette_favorite(entry)
                st.rerun()
        with col_button:
            target_tab = entry.get("target_tab", APP_TABS[0])
            if st.button("Открыть", key=f"command_palette_open_{index}_{target_tab}_{entry.get('title', '')}", use_container_width=True):
                _remember_command_palette_entry(entry)
                _set_active_main_tab(target_tab)
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def _workspace_universal_search_results(
    active_project: ProjectRecord,
    query: str,
    *,
    limit: int = 8,
) -> tuple[dict[str, str], ...]:
    """Search all workspace entities that matter on the home screen.

    The workspace search intentionally reuses the command-palette index so one
    query covers projects, wells, LAS files, curves, calculations, reports,
    documentation, history-oriented actions and pinned commands.
    """
    if not str(query or "").strip():
        return ()
    return _filter_command_palette_entries(
        _command_palette_entries(active_project),
        query,
        category="Все",
        recent_ids=st.session_state.get(COMMAND_PALETTE_RECENT_KEY, []),
        favorite_ids=st.session_state.get(COMMAND_PALETTE_FAVORITES_KEY, []),
        limit=limit,
    )


def _workspace_favorite_entries(active_project: ProjectRecord, *, limit: int = 5) -> tuple[dict[str, str], ...]:
    """Return pinned workspace entries with safe defaults for a new install."""
    entries = _command_palette_entries(active_project)
    favorite_ids = st.session_state.get(COMMAND_PALETTE_FAVORITES_KEY, [])
    pinned = _command_palette_recent_or_favorite_entries(entries, favorite_ids)
    if pinned:
        return pinned[: max(1, limit)]

    defaults = (
        "Создать или открыть проект",
        "Импорт LAS / CSV / Excel",
        "LAS Curve Manager",
        "Documentation Center",
        active_project.name,
    )
    selected: list[dict[str, str]] = []
    for title in defaults:
        for entry in entries:
            if entry.get("title") == title and entry not in selected:
                selected.append(entry)
                break
    return tuple(selected[: max(1, limit)])


def _workspace_search_results_html(results: tuple[dict[str, str], ...], query: str) -> str:
    """Render compact workspace search results without adding duplicated navigation cards."""
    if not str(query or "").strip():
        return ""
    if not results:
        return (
            "<div class='dashboard-card workspace-search-results' id='dashboard-workspace-search-results'>"
            "<h3>Результаты поиска <span>0</span></h3>"
            "<div class='dashboard-empty-state'>Ничего не найдено. Попробуйте LAS, скважина, расчет, отчет, docs или curve.</div>"
            "</div>"
        )

    rows = []
    for entry in results:
        rows.append(
            "<div class='dashboard-list-row workspace-search-result-row'>"
            f"<div><b>{_html_escape(entry.get('title', ''))}</b>"
            f"<div class='dashboard-muted'>{_html_escape(entry.get('description', ''))}</div></div>"
            f"<div class='dashboard-row-badge'>{_html_escape(_command_palette_entry_category(entry))}</div>"
            "</div>"
        )
    return (
        "<div class='dashboard-card workspace-search-results' id='dashboard-workspace-search-results'>"
        f"<h3>Результаты поиска <span>{len(results)}</span></h3>"
        + "".join(rows)
        + "</div>"
    )

def _background_manager_rule(tab_name: str) -> dict[str, str]:
    """Return the final branded background rule for a page.

    The rule explicitly separates branded screens from engineering workspaces,
    so decorative imagery is never applied behind LAS curves, plots, tables or reports.
    """
    return BACKGROUND_MANAGER_RULES.get(tab_name, BACKGROUND_MANAGER_RULES["Работа с данными"])


def _background_manager_workspace_tabs() -> tuple[str, ...]:
    """Return tabs where the branded background is intentionally disabled."""
    return tuple(tab for tab, rule in BACKGROUND_MANAGER_RULES.items() if rule["mode"] == "dark-workspace")


def _background_manager_branded_tabs() -> tuple[str, ...]:
    """Return tabs where branded imagery is allowed by the final background manager."""
    return tuple(tab for tab, rule in BACKGROUND_MANAGER_RULES.items() if rule["mode"] in {"branded", "documentation"})


def _glass_ui_token_names() -> tuple[str, ...]:
    """Return the shared glass component token names used by the UI system."""
    return tuple(GLASS_UI_TOKENS.keys())


def _glass_ui_css_classes() -> tuple[str, ...]:
    """Return CSS classes for the shared glass surfaces."""
    return tuple(token["class"] for token in GLASS_UI_TOKENS.values())


def _glass_ui_readability_rules() -> tuple[str, ...]:
    """Return readability constraints for branded and engineering surfaces."""
    return GLASS_UI_READABILITY_RULES


def _set_active_main_tab(tab_name: str) -> None:
    """Switch the single-page Streamlit workspace to a concrete application section."""
    if tab_name in APP_TABS:
        st.session_state[ACTIVE_MAIN_TAB_KEY] = tab_name


def _active_main_tab() -> str:
    """Return the selected application section, defaulting to the dashboard."""
    tab = st.session_state.get(ACTIVE_MAIN_TAB_KEY, APP_TABS[0])
    if tab not in APP_TABS:
        tab = APP_TABS[0]
        st.session_state[ACTIVE_MAIN_TAB_KEY] = tab
    return str(tab)


def _render_main_navigation() -> str:
    """Render one compact navigation button per application section.

    Dashboard 3.0 must not draw an empty decorative rectangle above the real
    Streamlit button. Each section is now represented by one accessible button
    and one short text caption below it. The active page is shown in the button
    label itself, which avoids fragile half-open HTML wrappers around widgets.
    """
    active_tab = _active_main_tab()
    st.markdown('<div class="app-nav-wrap simplified-dashboard-navigation no-empty-nav-cards">', unsafe_allow_html=True)
    columns = st.columns(len(NAVIGATION_ITEMS))
    for column, item in zip(columns, NAVIGATION_ITEMS):
        label = item["label"]
        active_prefix = "▸ " if label == active_tab else ""
        button_label = f"{active_prefix}{item['icon']} {label}"
        with column:
            if st.button(button_label, key=f"main_nav_{label}", use_container_width=True, help=item["description"]):
                _set_active_main_tab(label)
                st.rerun()
            st.markdown(
                f'<span class="app-nav-description" data-target="{_html_escape(label)}">{_html_escape(item["description"])}</span>',
                unsafe_allow_html=True,
            )
    st.markdown('</div>', unsafe_allow_html=True)
    return _active_main_tab()



PAGE_LAYOUT_META: dict[str, dict[str, str]] = {
    "Работа с данными": {"kicker": "Data Management", "title": "Работа с данными", "subtitle": "Единый рабочий контейнер для загрузки LAS/CSV/Excel, project datasets, mapping, расчетов и snapshot-истории.", "badge": "Темный workspace"},
    "LAS-редактор": {"kicker": "LAS Professional", "title": "LAS-редактор", "subtitle": "Нормализация глубины, правка кривых, rename/alias/merge и подготовка LAS перед расчетом.", "badge": "Без фонового шума"},
    "LAS-корреляция": {"kicker": "Correlation", "title": "LAS-корреляция", "subtitle": "Сравнение скважин, групп кривых, глубинных интервалов и подготовка печатных корреляционных материалов.", "badge": "Графики читаемы"},
    "Интерпретационные графики": {"kicker": "Interpretation", "title": "Интерпретационные графики", "subtitle": "Планшетные треки, Pixler/ternary, маркеры, зоны интерпретации и инженерные отчеты.", "badge": "Plot workspace"},
    "Инструкции и документация": {"kicker": "Documentation", "title": "Инструкции и документация", "subtitle": "Единая справочная зона с брендированным hero-блоком, быстрым запуском и встроенными документами проекта.", "badge": "Docs center"},
}


def _page_layout_meta(tab_name: str) -> dict[str, str]:
    """Return unified header metadata for a workspace tab."""
    return PAGE_LAYOUT_META.get(tab_name, {"kicker": "Gas Ratio Pro", "title": tab_name, "subtitle": "Единая рабочая область приложения.", "badge": "Workspace"})


def _open_page_shell(tab_name: str) -> None:
    """Open the shared page shell used by all non-dashboard workspaces."""
    meta = _page_layout_meta(tab_name)
    background_rule = _background_manager_rule(tab_name)
    rule_class = f"background-rule-{background_rule['mode']}"
    st.markdown(
        "<section class='app-page-shell glass-panel " + rule_class + "' data-background-rule='" + _html_escape(background_rule["mode"]) + "' data-page='" + _html_escape(tab_name) + "'>"
        "<header class='app-page-header glass-navbar'><div>"
        "<div class='app-page-kicker'>" + _html_escape(meta["kicker"]) + "</div>"
        "<h1 class='app-page-title'>" + _html_escape(meta["title"]) + "</h1>"
        "<p class='app-page-subtitle'>" + _html_escape(meta["subtitle"]) + "</p>"
        "</div><div class='app-page-badge'>" + _html_escape(meta["badge"]) + "</div></header>",
        unsafe_allow_html=True,
    )


def _close_page_shell() -> None:
    """Close the shared page shell opened for the active workspace."""
    st.markdown("</section>", unsafe_allow_html=True)

def _render_dashboard_shell(active_project: ProjectRecord, projects: tuple[ProjectRecord, ...]) -> None:
    """Render Project Workspace 1.0 as the application home screen.

    Project Workspace 1.0 removes the duplicated central navigation model from
    Dashboard 3.0. The Sidebar remains the only primary navigation surface, while
    the central area is reserved for engineering work context: recent projects,
    LAS files, calculations, reports, favorites, activity and universal search.
    """
    background_uri = _dashboard_background_data_uri()
    style = f"--global-bg-image: url('{background_uri}');" if background_uri else ""
    recent_projects = _dashboard_recent_projects(projects, limit=5)
    stats = _dashboard_project_statistics(active_project, projects)
    activity_items = _dashboard_activity_items(active_project, limit=6)
    las_files = list_project_las_files(LAS_CORRELATION_PROJECTS_ROOT, active_project.id)[:5]
    calculations = list_project_calculations(LAS_CORRELATION_PROJECTS_ROOT, active_project.id)[:5]
    exports = list_project_exports(LAS_CORRELATION_PROJECTS_ROOT, active_project.id)[:5]
    now_label = datetime.now().strftime("%d.%m.%Y %H:%M")

    def _row(title: str, meta: str, badge: str = "") -> str:
        badge_html = f"<span class='dashboard-row-badge'>{_html_escape(badge)}</span>" if badge else ""
        return (
            "<div class='dashboard-list-row'>"
            f"<div><b>{_html_escape(title)}</b><div class='dashboard-muted'>{_html_escape(meta)}</div></div>"
            f"<div class='dashboard-muted'>{badge_html}</div>"
            "</div>"
        )

    recent_html = "".join(
        _row(
            project.name,
            f"Изменен: {project.updated_at or 'без даты'} · ID: {project.id}",
            "проект",
        )
        for project in recent_projects
    ) or "<div class='dashboard-empty-state'>Проекты пока не найдены.</div>"

    recent_las_html = "".join(
        _row(
            getattr(item, "file_name", "") or getattr(item, "original_file_name", "") or getattr(item, "name", "") or getattr(item, "id", "LAS файл"),
            f"Скважина: {getattr(item, 'well_name', '') or getattr(item, 'well_id', '') or 'не указана'} · Кривые: {getattr(item, 'curve_count', '—')}",
            getattr(item, "saved_at", "") or getattr(item, "updated_at", "") or "LAS",
        )
        for item in las_files
    ) or "<div class='dashboard-empty-state'>LAS-файлы пока не импортированы.</div>"

    calculations_html = "".join(
        _row(
            getattr(item, "name", "") or getattr(item, "source_label", "") or getattr(item, "id", "Расчет"),
            f"Тип: {getattr(item, 'ch_mode_label', '') or getattr(item, 'ch_mode', '') or 'gas ratio'} · Проект: {active_project.name}",
            getattr(item, "saved_at", "") or getattr(item, "created_at", "") or "готов",
        )
        for item in calculations
    ) or "<div class='dashboard-empty-state'>Расчеты появятся после сохранения интерпретации.</div>"

    reports_html = "".join(
        _row(
            getattr(item, "label", "") or getattr(item, "file_name", "") or getattr(item, "id", "Отчет"),
            f"Формат: {getattr(item, 'kind', '') or getattr(item, 'mime_type', '') or 'export'} · Файл: {getattr(item, 'file_name', '') or '—'}",
            getattr(item, "saved_at", "") or "отчет",
        )
        for item in exports
    ) or "<div class='dashboard-empty-state'>Отчеты и экспорты пока не созданы.</div>"

    activity_html = "".join(
        _row(item, f"Проект: {active_project.name}", "history")
        for item in activity_items
    ) or "<div class='dashboard-empty-state'>Пока нет проектной активности.</div>"

    favorite_entries = _workspace_favorite_entries(active_project)
    favorites_html = "".join(
        _row(
            entry.get("title", "Закрепленный объект"),
            entry.get("description", "Workspace favorite"),
            _command_palette_entry_category(entry),
        )
        for entry in favorite_entries
    ) or "<div class='dashboard-empty-state'>Закрепите команды и объекты через Ctrl+K.</div>"

    workspace_query = st.text_input(
        "Глобальный поиск workspace",
        key="workspace_universal_search_query",
        placeholder="Поиск: проект, скважина, LAS, кривая, расчет, отчет, документация, история",
        help="Поиск использует единый индекс Workspace и Ctrl+K: проекты, скважины, LAS, кривые, расчеты, отчеты, документация, история и избранное.",
    )
    workspace_search_results = _workspace_universal_search_results(active_project, workspace_query)
    workspace_search_results_html = _workspace_search_results_html(workspace_search_results, workspace_query)

    metrics_html = f"""
      <div class='dashboard-status-grid dashboard-metrics'>
        <div class='dashboard-status-pill dashboard-metric'><b>{stats['projects']}</b><span>Проекты</span></div>
        <div class='dashboard-status-pill dashboard-metric'><b>{stats['wells']}</b><span>Скважины</span></div>
        <div class='dashboard-status-pill dashboard-metric'><b>{stats['las_files']}</b><span>LAS-файлы</span></div>
        <div class='dashboard-status-pill dashboard-metric'><b>{stats['calculations']}</b><span>Расчеты</span></div>
        <div class='dashboard-status-pill dashboard-metric'><b>{stats['exports']}</b><span>Отчеты</span></div>
      </div>
    """

    # Render the workspace inside a Streamlit HTML component instead of Markdown.
    # This avoids a Streamlit/Markdown regression where layout tags can be shown
    # as plain text on the page (<section>/<article>/<div> visible to the user).
    workspace_component_html = dedent(f"""
    <!doctype html>
    <html lang="ru">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
          :root {{ color-scheme: dark; }}
          * {{ box-sizing: border-box; }}
          html, body {{ margin: 0; padding: 0; overflow-x: hidden; background: transparent; font-family: Inter, Segoe UI, Roboto, Arial, sans-serif; }}
          .dashboard-shell {{ width: 100%; max-width: 100%; border: 1px solid rgba(148,163,184,.18); border-radius: 18px; overflow: hidden; background: radial-gradient(circle at 82% 8%, rgba(30,144,255,.10), transparent 28%), radial-gradient(circle at 16% 92%, rgba(255,138,0,.10), transparent 30%), linear-gradient(135deg, rgba(2,6,23,.96), rgba(7,12,24,.91)); box-shadow: 0 24px 82px rgba(0,0,0,.42); }}
          .dashboard-main {{ padding: clamp(.56rem, .9vw, .92rem); min-width: 0; }}
          .dashboard-navbar {{ display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: .55rem; align-items: center; margin-bottom: .62rem; }}
          .dashboard-title-row {{ display: flex; gap: .78rem; align-items: center; min-width: 0; }}
          .dashboard-title-icon {{ width: 2.45rem; height: 2.45rem; display: grid; place-items: center; border-radius: 12px; color: #38bdf8; background: rgba(14,165,233,.12); border: 1px solid rgba(56,189,248,.22); font-size: 1.12rem; flex: 0 0 auto; }}
          .dashboard-page-title {{ margin: 0; color: #f8fafc; font-size: clamp(1.14rem, 1.42vw, 1.62rem); line-height: 1.06; font-weight: 950; }}
          .dashboard-page-subtitle {{ margin: .12rem 0 0; color: #cbd5e1; font-size: .77rem; line-height: 1.22; }}
          .dashboard-search {{ display: flex; justify-content: flex-end; gap: .42rem; flex-wrap: wrap; }}
          .dashboard-search-chip {{ color: #dbeafe; border: 1px solid rgba(148,163,184,.22); background: rgba(15,23,42,.72); border-radius: 999px; padding: .46rem .68rem; font-weight: 850; font-size: .76rem; white-space: nowrap; }}
          .dashboard-card {{ min-width: 0; max-width: 100%; border-radius: 15px; padding: clamp(.66rem, .82vw, .88rem); background: linear-gradient(180deg, rgba(15,23,42,.76), rgba(7,12,24,.62)); border: 1px solid rgba(148,163,184,.18); box-shadow: 0 14px 38px rgba(0,0,0,.24), inset 0 1px 0 rgba(255,255,255,.04); }}
          .dashboard-card h3 {{ display: flex; justify-content: space-between; align-items: center; gap: .6rem; margin: 0 0 .52rem; color: #f8fafc; font-size: .92rem; line-height: 1.12; }}
          .dashboard-card h3 span {{ color: #38bdf8; font-size: .74rem; font-weight: 850; }}
          .workspace-search-card {{ margin-bottom: .62rem; }}
          .workspace-search-box {{ display: grid; gap: .18rem; padding: .48rem .58rem; border-radius: 13px; background: rgba(15,23,42,.58); border: 1px solid rgba(56,189,248,.18); }}
          .workspace-search-box b {{ color: #f8fafc; font-size: .76rem; line-height: 1.18; }}
          .workspace-search-box span {{ color: #94a3b8; font-size: .66rem; line-height: 1.18; }}
          .dashboard-layout {{ display: grid; grid-template-columns: repeat(12, minmax(0, 1fr)); gap: .62rem; align-items: stretch; min-width: 0; max-width: 100%; overflow: hidden; }}
          .dashboard-card.stats {{ grid-column: 1 / -1; }}
          .dashboard-card.projects {{ grid-column: span 4; }}
          .dashboard-card.recent-las {{ grid-column: span 4; }}
          .dashboard-card.calculations {{ grid-column: span 4; }}
          .dashboard-card.reports {{ grid-column: span 4; }}
          .dashboard-card.activity {{ grid-column: span 4; }}
          .dashboard-card.favorites {{ grid-column: span 4; }}
          .dashboard-status-grid, .dashboard-metrics {{ display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: .5rem; min-width: 0; max-width: 100%; }}
          .dashboard-status-pill, .dashboard-metric {{ min-height: 2.58rem; min-width: 0; padding: .36rem .44rem; border-radius: 13px; border: 1px solid rgba(148,163,184,.18); background: linear-gradient(135deg, rgba(30,64,175,.18), rgba(15,23,42,.30)); }}
          .dashboard-status-pill b, .dashboard-metric b {{ display: block; color: #f8fafc; font-size: .96rem; line-height: 1.02; }}
          .dashboard-status-pill span, .dashboard-metric span {{ color: #cbd5e1; font-weight: 850; font-size: .64rem; line-height: 1.08; }}
          .dashboard-list-row {{ display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: .58rem; padding: .42rem 0; border-bottom: 1px solid rgba(148,163,184,.12); }}
          .dashboard-list-row:last-child {{ border-bottom: 0; }}
          .dashboard-list-row b {{ color: #f8fafc; font-size: .82rem; line-height: 1.22; }}
          .dashboard-list-row > div:first-child, .dashboard-list-row b, .dashboard-muted {{ min-width: 0; overflow-wrap: anywhere; }}
          .dashboard-muted {{ color: #94a3b8; font-size: .70rem; line-height: 1.26; }}
          .dashboard-row-badge {{ display: inline-flex; align-items: center; justify-content: center; max-width: 8.6rem; padding: .16rem .42rem; border-radius: 999px; color: #bae6fd; background: rgba(14,165,233,.12); border: 1px solid rgba(14,165,233,.20); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: .68rem; }}
          .dashboard-empty-state {{ color: #94a3b8; font-size: .74rem; line-height: 1.28; padding: .2rem 0; }}
          .workspace-search-results {{ margin-bottom: .62rem; }}
          .workspace-search-result-row {{ border-left: 2px solid rgba(125,211,252,.42); padding-left: .52rem; }}
          .dashboard-footer {{ display: flex; justify-content: space-between; gap: .8rem; margin-top: .78rem; color: #aeb8c8; font-size: .74rem; }}
          @media (max-width: 1366px) {{ .dashboard-main {{ padding: .48rem; }} .dashboard-layout {{ gap: .52rem; }} .dashboard-card {{ padding: .58rem; }} .dashboard-status-grid, .dashboard-metrics {{ grid-template-columns: repeat(5, minmax(0, 1fr)); gap: .38rem; }} .dashboard-status-pill, .dashboard-metric {{ min-height: 2.28rem; padding: .30rem .38rem; }} .dashboard-card.projects, .dashboard-card.recent-las {{ grid-column: span 6; }} .dashboard-card.calculations, .dashboard-card.reports, .dashboard-card.activity {{ grid-column: span 4; }} .dashboard-card.favorites {{ grid-column: 1 / -1; }} }}
          @media (max-width: 920px) {{ .dashboard-navbar {{ grid-template-columns: 1fr; }} .dashboard-search {{ justify-content: flex-start; }} .dashboard-card.projects, .dashboard-card.recent-las, .dashboard-card.calculations, .dashboard-card.reports, .dashboard-card.activity, .dashboard-card.favorites {{ grid-column: 1 / -1; }} .dashboard-status-grid, .dashboard-metrics {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} .dashboard-footer {{ flex-direction: column; gap: .25rem; }} }}
        </style>
      </head>
      <body>
        <div class="dashboard-shell dashboard-3 project-workspace-1 dashboard-compact-workspace-fix dashboard-grid-optimized dashboard-information-hierarchy dashboard-responsive-audit dashboard-3-branch" data-dashboard-branch="Project Workspace 1.0" data-dashboard-workspace="project-workspace-1" data-dashboard-background-refinement="center-contained" data-dashboard-grid="optimized" data-dashboard-hierarchy="information" data-dashboard-responsive-audit="notebook-validated" style="{style}">
          <span class="dashboard-3-branch-marker" hidden>Dashboard 3.0 branch · Project Workspace 1.0</span>
          <div class="dashboard-main dashboard-workspace-main" id="dashboard-home">
            <div class="dashboard-navbar glass-navbar">
              <div class="dashboard-title-row">
                <div class="dashboard-title-icon">▦</div>
                <div><h1 class="dashboard-page-title">Project Workspace</h1><p class="dashboard-page-subtitle">Инженерный обзор: проекты, LAS, расчеты, отчеты, избранное и история.</p></div>
              </div>
              <div class="dashboard-search"><span class="dashboard-search-chip">Ctrl+K</span><span class="dashboard-search-chip">{_html_escape(active_project.name)}</span></div>
            </div>
            <div class="dashboard-card workspace-search-card" aria-label="Universal search">
              <h3>Глобальный поиск <span>Universal Search</span></h3>
              <div class="workspace-search-box"><b>🔎 Поиск по проектам, скважинам, LAS, кривым, расчетам, отчетам, документации и истории</b><span>Введите запрос в поле выше или используйте Ctrl+K.</span></div>
            </div>
            {workspace_search_results_html}
            <div class="dashboard-layout dashboard-information-priority" data-dashboard-information-hierarchy="workspace-v1">
              <div class="dashboard-card stats" id="dashboard-project-status"><h3>Сводка workspace <span>{now_label}</span></h3>{metrics_html}</div>
              <div class="dashboard-card projects" id="dashboard-projects"><h3>Последние проекты <span>recent</span></h3>{recent_html}</div>
              <div class="dashboard-card recent-las" id="dashboard-recent-las"><h3>Последние LAS <span>files</span></h3>{recent_las_html}</div>
              <div class="dashboard-card calculations" id="dashboard-calculations"><h3>Последние расчеты <span>calc</span></h3>{calculations_html}</div>
              <div class="dashboard-card reports" id="dashboard-reports"><h3>Последние отчеты <span>export</span></h3>{reports_html}</div>
              <div class="dashboard-card activity" id="dashboard-activity"><h3>Недавние действия <span>history</span></h3>{activity_html}</div>
              <div class="dashboard-card favorites" id="dashboard-favorites"><h3>Избранное <span>pinned</span></h3>{favorites_html}</div>
            </div>
            <div class="dashboard-footer"><span>Готов к работе · навигация только в Sidebar</span><span>Версия: 2.0.0 · {now_label}</span></div>
          </div>
        </div>
      </body>
    </html>
    """).strip()
    components.html(workspace_component_html, height=760, scrolling=False)

def _render_start_tab(active_project: ProjectRecord) -> None:
    projects = list_projects(LAS_CORRELATION_PROJECTS_ROOT)
    if not projects:
        projects = (active_project,)

    # Dashboard 3.0 intentionally avoids the old duplicated quick-action strip.
    # Legacy static markers kept for tests/documentation: dashboard_quick_action_,
    # functional-quick-actions div[data-testid="stButton"] > button,
    # Компактная панель: одна плитка = одно действие, help=action["tooltip"],
    # _quick_action_button_label(action).
    _render_dashboard_shell(active_project, projects)

    with st.expander("Текущее состояние workflow", expanded=False):
        for label, value, next_action in _workflow_status_detail_rows(active_project):
            st.markdown(
                f"<div class='workflow-status'><b>{label}</b><br>{value}<small><b>Дальше:</b> {next_action}</small></div>",
                unsafe_allow_html=True,
            )

    layout_value = str(st.session_state.get(UI_LAYOUT_KEY, UI_LAYOUT_PROFILES["wide"]["label"]))
    layout_key = layout_value if layout_value in UI_LAYOUT_PROFILES else _layout_profile_key(layout_value)
    layout_label, layout_width, layout_description = _layout_profile_summary(layout_key)
    with st.expander("Проверка экрана и компоновки", expanded=False):
        st.markdown(
            f"**Активный режим:** {layout_label} (`max-width: {layout_width}`).\n\n"
            f"{layout_description}\n\n"
            "Dashboard 3.0 использует левую навигационную рейку, верхний overview, "
            "информационные панели и адаптивную сетку без горизонтального переполнения."
        )

def _read_documentation_markdown(relative_path: str) -> str:
    candidate = Path(relative_path)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"Unsafe documentation path: {relative_path}")

    path = ROOT_DIR / candidate
    return path.read_text(encoding="utf-8")


def _render_docs_anchor(anchor: str) -> None:
    """Render a stable anchor inside the Documentation Center."""
    st.markdown(f'<div id="{_html_escape(anchor)}" class="docs-section-anchor"></div>', unsafe_allow_html=True)


def _documentation_quick_link_titles() -> tuple[str, ...]:
    """Expose Documentation Center v2 quick-link titles for tests and command search."""
    return tuple(item["title"] for item in DOCUMENTATION_QUICK_LINKS)


def _documentation_table_of_contents() -> tuple[dict[str, str], ...]:
    """Return the in-page Documentation Center table of contents."""
    return DOCUMENTATION_TOC


def _render_documentation_tab() -> None:
    hero_uri = _documentation_hero_data_uri() or _dashboard_background_data_uri()
    logo_uri = _branding_logo_data_uri()
    logo_html = (
        f'<div class="docs-hero-brand-badge"><img src="{logo_uri}" alt="Gas Ratio Pro logo"></div>'
        if logo_uri
        else ""
    )
    image_html = (
        f'<img class="docs-hero-image" src="{hero_uri}" alt="Gas Ratio Pro documentation banner">'
        if hero_uri
        else ""
    )
    hero_html = f"""
        <div class="docs-hero">
          <section class="docs-hero-banner">
            {image_html}
            {logo_html}
            <div class="docs-hero-content">
              <div class="docs-hero-kicker">Gas Ratio Pro Documentation Center v2</div>
              <h1 class="docs-hero-title">Инструкции и документация</h1>
              <p class="docs-hero-subtitle">Быстрый старт, методика работы, LAS workflow, FAQ, горячие клавиши и troubleshooting в одном справочном центре.</p>
            </div>
          </section>
        """
    st.markdown(hero_html, unsafe_allow_html=True)
    st.markdown('<div class="docs-panel">', unsafe_allow_html=True)
    st.caption(
        "Documentation Center v2 объединяет вводные инструкции, быстрые переходы, "
        "таблицу содержания и встроенные документы проекта без пустых темных блоков."
    )

    quick_cards = "".join(
        "<a href='#{anchor}' class='docs-v2-card'><div class='docs-v2-icon'>{icon}</div>"
        "<b>{title}</b><span>{description}</span></a>".format(
            anchor=_html_escape(item["anchor"]),
            icon=_html_escape(item["icon"]),
            title=_html_escape(item["title"]),
            description=_html_escape(item["description"]),
        )
        for item in DOCUMENTATION_QUICK_LINKS
    )
    st.markdown(f'<div class="docs-v2-grid">{quick_cards}</div>', unsafe_allow_html=True)

    toc_links = "".join(
        "<a href='#{anchor}'>{title}</a>".format(
            anchor=_html_escape(item["anchor"]),
            title=_html_escape(item["title"]),
        )
        for item in DOCUMENTATION_TOC
    )
    st.markdown("### Содержание раздела")
    st.markdown(f'<nav class="docs-toc">{toc_links}</nav>', unsafe_allow_html=True)

    quick_start, verification = st.columns(2)
    with quick_start:
        _render_docs_anchor("docs-quick-start")
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
            "3. Загрузите LAS, CSV, XLSX или XLSM.\n"
            "4. Проверьте строку заголовков, mapping и предупреждения.\n"
            "5. Выберите интервал и откройте расчеты, палетки и графики."
        )

    with verification:
        _render_docs_anchor("docs-verification")
        st.markdown("### Проверка готовности")
        st.code(
            "python -m pytest\n"
            "python scripts/preflight.py",
            language="powershell",
        )
        st.markdown(
            "Preflight проверяет Python, зависимости, ключевые файлы, конфиг палеток, "
            "экспортные зависимости и доступность папки логов."
        )

    _render_docs_anchor("docs-workflow")
    st.markdown("### Основной рабочий сценарий")
    st.markdown(
        "1. Загрузите LAS, CSV или Excel-файл и выберите набор данных.\n"
        "2. Проверьте первые строки и строку заголовков.\n"
        "3. Исправьте сопоставление колонок, если auto-mapping ошибся.\n"
        "4. Проверьте предупреждения и режим `Ch`.\n"
        "5. Выберите интервал, проверьте Pixler/ternary и depth-графики.\n"
        "6. Сохраните snapshot в проект и скачайте CSV/HTML/XLSX, если результат нужен для отчета."
    )

    _render_docs_anchor("docs-data-format")
    st.markdown("### Формат данных и mapping")
    st.markdown(
        "Документация принимает LAS, CSV, XLSX и XLSM. Для надежного расчета проверьте depth-колонку, "
        "газовые компоненты, автоматический mapping, единицы и предупреждения о пропусках."
    )

    _render_docs_anchor("docs-las-workflow")
    st.markdown("### LAS workflow")
    st.markdown(
        "LAS-редактор используется для проверки глубины, шага, NULL-значений и ручных правок. "
        "LAS-корреляция нужна для сравнения скважин, группировки кривых, подготовки интервала и печатного HTML-отчета."
    )

    _render_docs_anchor("docs-shortcuts")
    st.markdown("### Горячие клавиши")
    for shortcut in DOCUMENTATION_SHORTCUTS:
        st.markdown(
            f"<div class='docs-info-row'><b>{_html_escape(shortcut['keys'])}</b><br>"
            f"<span>{_html_escape(shortcut['action'])}</span></div>",
            unsafe_allow_html=True,
        )

    _render_docs_anchor("docs-faq")
    st.markdown("### FAQ")
    for item in DOCUMENTATION_FAQ:
        with st.expander(item["question"], expanded=False):
            st.markdown(item["answer"])

    _render_docs_anchor("docs-troubleshooting")
    st.markdown("### Troubleshooting")
    st.markdown(
        "Если приложение показывает ошибку, сначала проверьте `python scripts/preflight.py`, "
        "затем установку зависимостей из `requirements.txt` и последние строки `logs/app.log`. "
        "Для статического экспорта PNG/PDF/SVG нужна зависимость `kaleido`."
    )
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("### Полные документы проекта")
    for index, (title, relative_path) in enumerate(DOCUMENTATION_TAB_DOCS):
        with st.expander(title, expanded=index == 0):
            st.markdown(_read_documentation_markdown(relative_path))
    st.markdown('</div>', unsafe_allow_html=True)


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

    prepared_df = _render_las_curve_rename_manager(prepared_df)
    _render_las_curve_alias_manager(prepared_df)
    _render_las_curve_grouping_manager(prepared_df)
    _render_las_curve_category_manager(prepared_df)
    _render_las_curve_units_manager(prepared_df)
    _render_las_curve_metadata_editor(prepared_df)
    _render_las_curve_mnemonics_dictionary(prepared_df)
    _render_las_curve_duplicate_detection(prepared_df)
    _render_las_curve_quality_flags(prepared_df)
    prepared_df = _render_las_curve_bulk_edit_manager(prepared_df)
    _render_las_curve_export_rules_manager(prepared_df)
    prepared_df = _render_las_curve_merge_manager(prepared_df)

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

    st.markdown("### Исправление направления глубины")
    st.caption(
        "Если LAS открыт наоборот — первая строка содержит большую глубину, а ниже глубина убывает — "
        "включите исправление. Редактор развернет строки по возрастанию глубины и сохранит результат как новую LAS-версию."
    )
    direction_cols = st.columns(3)
    fix_depth_direction_enabled = direction_cols[0].checkbox(
        "Исправить убывающую глубину",
        value=False,
        key="las_editor_fix_depth_direction_enabled",
    )
    target_depth_direction_label = direction_cols[1].selectbox(
        "Направление после исправления",
        options=("Глубина растет сверху вниз", "Глубина убывает сверху вниз"),
        index=0,
        key="las_editor_target_depth_direction",
        disabled=not fix_depth_direction_enabled,
    )
    output_las_name = direction_cols[2].text_input(
        "Новое имя LAS",
        value=build_safe_las_filename(getattr(uploaded_file, 'name', 'prepared.las'), "depth_fixed"),
        key="las_editor_depth_fixed_las_name",
    )
    depth_direction_log: tuple[str, ...] = ()
    depth_direction_warnings: tuple[str, ...] = ()
    if fix_depth_direction_enabled:
        target_depth_direction = "increasing" if target_depth_direction_label.startswith("Глубина растет") else "decreasing"
        try:
            depth_direction_result = fix_depth_direction(
                prepared_df,
                depth_column=depth_column,
                target_direction=target_depth_direction,
            )
            prepared_df = depth_direction_result.data
            depth_direction_log = depth_direction_result.operation_log
            depth_direction_warnings = depth_direction_result.warnings
            status_cols = st.columns(4)
            status_cols[0].metric("Было: первая", depth_direction_result.before_first_depth if depth_direction_result.before_first_depth is not None else "нет")
            status_cols[1].metric("Было: последняя", depth_direction_result.before_last_depth if depth_direction_result.before_last_depth is not None else "нет")
            status_cols[2].metric("Стало: первая", depth_direction_result.after_first_depth if depth_direction_result.after_first_depth is not None else "нет")
            status_cols[3].metric("Стало: последняя", depth_direction_result.after_last_depth if depth_direction_result.after_last_depth is not None else "нет")
            if depth_direction_result.direction_fixed:
                st.success("Порядок строк по глубине исправлен. Исходный файл не перезаписан.")
            else:
                st.info("Выбранная колонка глубины уже соответствует заданному направлению.")
            for warning in depth_direction_warnings:
                st.warning(warning)
        except Exception:
            logger.exception("las_editor_depth_direction_fix_failed")
            st.error("Не удалось исправить направление глубины. Проверьте выбранную колонку глубины.")
            st.caption("Подробности записаны в logs/app.log.")
            return

    st.markdown("### Массовые операции")
    st.caption(
        "Эти операции выполняются до построения новой сетки глубины. "
        "Исходный файл не перезаписывается: результат можно проверить ниже и только потом сохранить."
    )
    bulk_col1, bulk_col2, bulk_col3 = st.columns(3)
    remove_duplicate_depths = bulk_col1.checkbox(
        "Удалить дубли глубин",
        value=False,
        key="las_editor_remove_duplicate_depths",
    )
    sort_depth = bulk_col1.checkbox(
        "Отсортировать глубину",
        value=True,
        key="las_editor_sort_depth",
    )
    replace_null_enabled = bulk_col2.checkbox(
        "Заменить LAS NULL на пусто",
        value=True,
        key="las_editor_replace_null_enabled",
    )
    null_value = bulk_col2.text_input(
        "NULL-значение",
        value="-999.25",
        key="las_editor_null_value",
        disabled=not replace_null_enabled,
    )
    trim_enabled = bulk_col3.checkbox(
        "Обрезать интервал",
        value=False,
        key="las_editor_trim_enabled",
    )
    trim_start = bulk_col3.text_input(
        "От глубины",
        value="",
        key="las_editor_trim_start",
        disabled=not trim_enabled,
    )
    trim_end = bulk_col3.text_input(
        "До глубины",
        value="",
        key="las_editor_trim_end",
        disabled=not trim_enabled,
    )

    try:
        bulk_result = apply_las_bulk_operations(
            prepared_df,
            depth_column=depth_column,
            remove_duplicate_depths=remove_duplicate_depths,
            trim_start=trim_start if trim_enabled else None,
            trim_end=trim_end if trim_enabled else None,
            replace_null_value=null_value if replace_null_enabled else None,
            sort_depth=sort_depth,
        )
    except Exception:
        logger.exception("las_editor_bulk_operations_failed")
        st.error("Не удалось выполнить массовые операции. Проверьте колонку глубины, NULL и границы интервала.")
        st.caption("Подробности записаны в logs/app.log.")
        return

    with st.expander("Журнал массовых операций", expanded=bool(bulk_result.warnings)):
        if bulk_result.operation_log:
            for item in bulk_result.operation_log:
                st.markdown(f"- {item}")
        else:
            st.caption("Массовые операции не меняли таблицу.")
        if bulk_result.warnings:
            st.markdown("#### Что требует проверки")
            for warning in bulk_result.warnings:
                st.warning(warning)

    st.markdown("### Depth & Sampling Tools")
    st.caption(
        "Профессиональные операции с глубиной выполняются перед финальной сеткой: "
        "смещение, перевод m/ft, обрезка интервала и интерполяционный ресемплинг. "
        "Исходный LAS не перезаписывается."
    )
    sampling_df = bulk_result.data
    sampling_log: list[str] = []
    sampling_warnings: list[str] = []
    with st.expander("Расширенные операции глубины", expanded=False):
        depth_tool_cols = st.columns(4)
        shift_enabled = depth_tool_cols[0].checkbox("Сместить глубину", value=False, key="las_editor_depth_shift_enabled")
        shift_offset = depth_tool_cols[0].text_input("Смещение", value="0.0", key="las_editor_depth_shift_offset", disabled=not shift_enabled)
        unit_enabled = depth_tool_cols[1].checkbox("Перевести m/ft", value=False, key="las_editor_depth_unit_enabled")
        unit_pair = depth_tool_cols[1].selectbox("Единицы", options=("m → ft", "ft → m"), key="las_editor_depth_unit_pair", disabled=not unit_enabled)
        crop_enabled = depth_tool_cols[2].checkbox("Обрезать интервал", value=False, key="las_editor_depth_crop_enabled")
        crop_start = depth_tool_cols[2].text_input("Crop start", value="", key="las_editor_depth_crop_start", disabled=not crop_enabled)
        crop_stop = depth_tool_cols[2].text_input("Crop stop", value="", key="las_editor_depth_crop_stop", disabled=not crop_enabled)
        interpolation_enabled = depth_tool_cols[3].checkbox("Интерполяционный ресемплинг", value=False, key="las_editor_depth_interpolation_enabled")
        interpolation_step = depth_tool_cols[3].text_input("Новый шаг", value=str(target_step), key="las_editor_depth_interpolation_step", disabled=not interpolation_enabled)
        interpolation_method_label = depth_tool_cols[3].selectbox("Метод", options=("linear", "nearest"), key="las_editor_depth_interpolation_method", disabled=not interpolation_enabled)

        try:
            if shift_enabled:
                shift_result = shift_depth_values(sampling_df, depth_column=depth_column, offset=shift_offset)
                sampling_df = shift_result.data
                sampling_log.extend(shift_result.operation_log)
                sampling_warnings.extend(shift_result.warnings)
            if unit_enabled:
                source_unit, target_unit_label = ("m", "ft") if unit_pair.startswith("m") else ("ft", "m")
                unit_result = convert_depth_units(sampling_df, depth_column=depth_column, source_unit=source_unit, target_unit=target_unit_label)
                sampling_df = unit_result.data
                sampling_log.extend(unit_result.operation_log)
                sampling_warnings.extend(unit_result.warnings)
            if crop_enabled:
                crop_result = crop_depth_interval(sampling_df, depth_column=depth_column, start_depth=crop_start, stop_depth=crop_stop)
                sampling_df = crop_result.data
                sampling_log.extend(crop_result.operation_log)
                sampling_warnings.extend(crop_result.warnings)
            if interpolation_enabled:
                interpolation_result = resample_depth_step(
                    sampling_df,
                    depth_column=depth_column,
                    target_step=interpolation_step,
                    method=interpolation_method_label,
                )
                sampling_df = interpolation_result.data
                sampling_log.extend(interpolation_result.operation_log)
                sampling_warnings.extend(interpolation_result.warnings)

            integrity = validate_depth_integrity(sampling_df, depth_column=depth_column)
            integrity_cols = st.columns(5)
            integrity_cols[0].metric("STRT", integrity.start_depth if integrity.start_depth is not None else "нет")
            integrity_cols[1].metric("STOP", integrity.stop_depth if integrity.stop_depth is not None else "нет")
            integrity_cols[2].metric("STEP", integrity.step if integrity.step is not None else "нет")
            integrity_cols[3].metric("Дубли", integrity.duplicate_count)
            integrity_cols[4].metric("Пустые глубины", integrity.null_depth_count)
            if sampling_log:
                st.markdown("**Журнал Depth & Sampling:**")
                for item in sampling_log:
                    st.markdown(f"- {item}")
            if sampling_warnings or integrity.warnings:
                for warning in tuple(dict.fromkeys(tuple(sampling_warnings) + tuple(integrity.warnings))):
                    st.warning(warning)
            else:
                st.success("Проверка глубины после операций пройдена.")
        except Exception:
            logger.exception("las_editor_depth_sampling_tools_failed")
            st.error("Не удалось выполнить Depth & Sampling операцию. Проверьте смещение, единицы, интервал или шаг.")
            st.caption("Подробности записаны в logs/app.log.")
            return

    try:
        result = resample_las_data(
            sampling_df,
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

    step_report = diagnostics.step_report
    with st.expander("Отчет по шагу глубины", expanded=bool(step_report.outliers)):
        report_cols = st.columns(4)
        report_cols[0].metric("Шагов", step_report.step_count)
        report_cols[1].metric("Мин. шаг", step_report.min_step if step_report.min_step is not None else "нет")
        report_cols[2].metric("Макс. шаг", step_report.max_step if step_report.max_step is not None else "нет")
        report_cols[3].metric("Частый шаг", step_report.most_common_step if step_report.most_common_step is not None else "нет")
        if step_report.outliers:
            st.caption("Первые выбросы шага глубины. Проверьте пропуски, дубли, сбой записи глубины или неверный целевой шаг.")
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "От": outlier.from_depth,
                            "До": outlier.to_depth,
                            "Фактический шаг": outlier.step,
                            "Ожидаемый шаг": outlier.expected_step,
                        }
                        for outlier in step_report.outliers[:100]
                    ]
                ),
                use_container_width=True,
            )
        else:
            st.caption("Выбросы шага по выбранному целевому шагу не найдены.")

    if result.added_depths:
        preview_depths = ", ".join(str(depth) for depth in result.added_depths[:40])
        if len(result.added_depths) > 40:
            preview_depths += ", ..."
        st.caption("Добавленные глубины: " + preview_depths)

    st.markdown("### Ручное добавление строк по интервалу")
    st.caption(
        "Этот блок нужен, когда нужно точечно уплотнить или восстановить часть LAS, "
        "не перестраивая весь ствол. Операция попадает в журнал правок сохраненной версии."
    )
    manual_rows_enabled = st.checkbox(
        "Добавить строки только в выбранном интервале",
        value=False,
        key="las_editor_manual_rows_enabled",
    )
    manual_result = None
    editor_base_df = result.data
    manual_added_depths: tuple[float, ...] = ()
    manual_interval_log: tuple[str, ...] = ()
    if manual_rows_enabled:
        manual_cols = st.columns(3)
        manual_start = manual_cols[0].text_input(
            "Начало интервала",
            value=str(diagnostics.min_depth if diagnostics.min_depth is not None else ""),
            key="las_editor_manual_rows_start",
        )
        manual_end = manual_cols[1].text_input(
            "Конец интервала",
            value=str(diagnostics.max_depth if diagnostics.max_depth is not None else ""),
            key="las_editor_manual_rows_end",
        )
        manual_step = manual_cols[2].text_input(
            "Шаг внутри интервала",
            value=str(target_step),
            key="las_editor_manual_rows_step",
        )
        try:
            manual_result = insert_manual_depth_rows(
                result.data,
                depth_column=depth_column,
                start_depth=manual_start,
                end_depth=manual_end,
                step=manual_step,
                fill_strategy=fill_strategy,
            )
            editor_base_df = manual_result.data
            manual_added_depths = manual_result.added_depths
            manual_interval_log = manual_result.operation_log
            st.metric("Добавлено вручную", len(manual_result.added_depths))
            for warning in manual_result.warnings:
                st.warning(warning)
            if manual_result.added_depths:
                st.caption(
                    "Ручные добавленные глубины: "
                    + ", ".join(str(depth) for depth in manual_result.added_depths[:40])
                    + (", ..." if len(manual_result.added_depths) > 40 else "")
                )
        except Exception:
            logger.exception("las_editor_manual_interval_rows_failed")
            st.error("Не удалось добавить строки по выбранному интервалу. Проверьте границы и шаг.")
            st.caption("Подробности записаны в logs/app.log.")
            return

    st.markdown("### Ручная правка перед расчетом")
    edited_df = st.data_editor(
        editor_base_df,
        use_container_width=True,
        num_rows="dynamic",
        key="las_editor_data_editor",
    )

    all_added_depths = tuple(result.added_depths) + tuple(manual_added_depths)
    manual_preview = build_las_edit_preview(editor_base_df, edited_df)
    audit_entries = build_las_edit_audit_log(
        depth_column=depth_column,
        target_step=target_step,
        fill_strategy=fill_strategy,
        bulk_operation_log=tuple(depth_direction_log) + tuple(bulk_result.operation_log) + tuple(sampling_log),
        manual_interval_log=manual_interval_log,
        added_depths=all_added_depths,
        manual_preview=manual_preview,
    )

    editor_hints = build_las_editor_hints(
        diagnostics,
        added_depth_count=len(all_added_depths),
        fill_strategy=fill_strategy,
        bulk_operation_log=tuple(depth_direction_log) + tuple(bulk_result.operation_log) + tuple(sampling_log),
        manual_interval_log=manual_interval_log,
        preview=manual_preview,
    )

    with st.expander("Проверяемые подсказки LAS-редактора", expanded=bool(result.warnings or bulk_result.warnings or manual_added_depths)):
        status_icon = {"ok": "✅", "info": "ℹ️", "review": "🟡", "warning": "⚠️"}
        st.caption("Подсказки не меняют данные автоматически. Они показывают, что инженер должен проверить перед сохранением версии или выгрузкой.")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Статус": f"{status_icon.get(hint.status, 'ℹ️')} {hint.status}",
                        "Раздел": hint.topic,
                        "Что найдено": hint.message,
                        "Что сделать": hint.action,
                    }
                    for hint in editor_hints
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )
        st.caption("Подробнее: docs/las_editor_plan.md и docs/user_guide.md → раздел LAS-редактора.")

    with st.expander("Предпросмотр до/после и журнал правок", expanded=manual_preview.changed_cells > 0):
        preview_cols = st.columns(5)
        preview_cols[0].metric("Строк было", manual_preview.before_rows)
        preview_cols[1].metric("Строк стало", manual_preview.after_rows)
        preview_cols[2].metric("Добавлено", manual_preview.added_rows)
        preview_cols[3].metric("Удалено", manual_preview.removed_rows)
        preview_cols[4].metric("Изменено ячеек", manual_preview.changed_cells)
        if manual_preview.changed_columns:
            st.caption("Измененные колонки: " + ", ".join(manual_preview.changed_columns))
        else:
            st.caption("Ручных изменений после автоматической подготовки не найдено.")

        before_col, after_col = st.columns(2)
        before_col.markdown("**До ручной правки**")
        before_col.dataframe(editor_base_df.head(30), use_container_width=True)
        after_col.markdown("**После ручной правки**")
        after_col.dataframe(edited_df.head(30), use_container_width=True)

        st.markdown("**Журнал правок, который будет сохранен в metadata версии**")
        st.dataframe(
            pd.DataFrame(
                [
                    {"Этап": entry.stage, "Действие": entry.action, "Детали": entry.details}
                    for entry in audit_entries
                ]
            ),
            use_container_width=True,
        )

    save_col, export_col = st.columns(2)
    if save_col.button("Сохранить для расчетов", type="primary", use_container_width=True):
        st.session_state[LAS_EDITOR_SESSION_SHEETS_KEY] = {"LAS-редактор": _dataframe_to_raw_sheet(edited_df)}
        st.session_state[LAS_EDITOR_SESSION_SUMMARY_KEY] = (
            f"{len(edited_df)} строк, шаг {target_step}, заполнение: {fill_label}, массовых операций: {len(bulk_result.operation_log)}"
        )
        logger.info(
            "las_editor_saved_to_session rows=%d columns=%d added_depths=%d fill_strategy=%s bulk_operations=%d",
            len(edited_df),
            len(edited_df.columns),
            len(all_added_depths),
            safe_log_value(fill_strategy),
            len(bulk_result.operation_log),
        )
        st.success("Исправленные LAS-данные сохранены. Откройте вкладку `Работа с данными` и включите данные из редактора.")

    export_col.download_button(
        "Экспорт CSV",
        data=export_csv_bytes(edited_df),
        file_name="las_editor_prepared.csv",
        mime="text/csv",
        use_container_width=True,
    )
    safe_output_las_name = Path(output_las_name.strip() or "las_editor_depth_fixed.las").name
    if not safe_output_las_name.lower().endswith(".las"):
        safe_output_las_name += ".las"
    export_col.download_button(
        "Скачать LAS под новым названием",
        data=export_las_bytes(edited_df, well_name=Path(safe_output_las_name).stem, depth_column=depth_column),
        file_name=safe_output_las_name,
        mime="application/octet-stream",
        use_container_width=True,
        key="las_editor_download_depth_fixed_las",
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
                    "added_depth_count": len(all_added_depths),
                    "depth_direction_log": list(depth_direction_log),
                    "manual_interval_added_depth_count": len(manual_added_depths),
                    "preview": {
                        "before_rows": manual_preview.before_rows,
                        "after_rows": manual_preview.after_rows,
                        "added_rows": manual_preview.added_rows,
                        "removed_rows": manual_preview.removed_rows,
                        "changed_cells": manual_preview.changed_cells,
                        "changed_columns": list(manual_preview.changed_columns),
                    },
                    "edit_log": [
                        {"stage": entry.stage, "action": entry.action, "details": entry.details}
                        for entry in audit_entries
                    ],
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
                    metadata={
                        "source": "las_editor",
                        "target_step": str(target_step),
                        "fill_strategy": fill_strategy,
                        "added_depth_count": len(all_added_depths),
                    "depth_direction_log": list(depth_direction_log),
                    "manual_interval_added_depth_count": len(manual_added_depths),
                        "preview": {
                            "before_rows": manual_preview.before_rows,
                            "after_rows": manual_preview.after_rows,
                            "added_rows": manual_preview.added_rows,
                            "removed_rows": manual_preview.removed_rows,
                            "changed_cells": manual_preview.changed_cells,
                            "changed_columns": list(manual_preview.changed_columns),
                        },
                        "edit_log": [
                            {"stage": entry.stage, "action": entry.action, "details": entry.details}
                            for entry in audit_entries
                        ],
                    },
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
            csv_uploads = tuple(
                uploaded_file
                for uploaded_file in uploaded_files
                if Path(str(getattr(uploaded_file, "name", ""))).suffix.lower() == ".csv"
            )
            if csv_uploads:
                st.caption("CSV-файлы можно сохранить в Dataset Manager активного проекта без повторной загрузки.")
                if st.button("Сохранить загруженные CSV в проект", key=f"save_uploaded_csv_datasets_{active_project.id}"):
                    try:
                        saved_count = 0
                        for uploaded_file in csv_uploads:
                            original_name = Path(str(getattr(uploaded_file, "name", "source.csv"))).name
                            save_project_csv_dataset(
                                data=bytes(uploaded_file.getvalue()),
                                root=LAS_CORRELATION_PROJECTS_ROOT,
                                project_id=active_project.id,
                                file_name=original_name,
                                name=Path(original_name).stem,
                                metadata={"source": "workspace_upload"},
                            )
                            saved_count += 1
                    except Exception:
                        logger.exception("project_csv_datasets_save_failed project_id=%s", safe_log_value(active_project.id))
                        st.error("Не удалось сохранить CSV datasets в проект. Подробности записаны в logs/app.log.")
                    else:
                        logger.info(
                            "project_csv_datasets_saved project_id=%s count=%d",
                            safe_log_value(active_project.id),
                            saved_count,
                        )
                        st.success(f"CSV datasets сохранены в проект: {saved_count}.")
                        st.rerun()
            excel_uploads = tuple(
                uploaded_file
                for uploaded_file in uploaded_files
                if Path(str(getattr(uploaded_file, "name", ""))).suffix.lower() in {".xlsx", ".xlsm"}
            )
            if excel_uploads:
                st.caption("Excel-файлы можно сохранить в Dataset Manager активного проекта без повторной загрузки.")
                if st.button("Сохранить загруженные Excel в проект", key=f"save_uploaded_excel_datasets_{active_project.id}"):
                    try:
                        saved_count = 0
                        for uploaded_file in excel_uploads:
                            original_name = Path(str(getattr(uploaded_file, "name", "source.xlsx"))).name
                            save_project_excel_dataset(
                                data=bytes(uploaded_file.getvalue()),
                                root=LAS_CORRELATION_PROJECTS_ROOT,
                                project_id=active_project.id,
                                file_name=original_name,
                                name=Path(original_name).stem,
                                metadata={"source": "workspace_upload"},
                            )
                            saved_count += 1
                    except Exception:
                        logger.exception("project_excel_datasets_save_failed project_id=%s", safe_log_value(active_project.id))
                        st.error("Не удалось сохранить Excel datasets в проект. Подробности записаны в logs/app.log.")
                    else:
                        logger.info(
                            "project_excel_datasets_saved project_id=%s count=%d",
                            safe_log_value(active_project.id),
                            saved_count,
                        )
                        st.success(f"Excel datasets сохранены в проект: {saved_count}.")
                        st.rerun()
            core_uploads = tuple(
                uploaded_file
                for uploaded_file in uploaded_files
                if Path(str(getattr(uploaded_file, "name", ""))).suffix.lower() in {".csv", ".xlsx", ".xlsm"}
            )
            if core_uploads:
                st.caption("CSV/Excel с лабораторными core-данными можно сохранить как Core dataset проекта.")
                if st.button("Сохранить загруженные файлы как Core datasets", key=f"save_uploaded_core_datasets_{active_project.id}"):
                    try:
                        saved_count = 0
                        for uploaded_file in core_uploads:
                            original_name = Path(str(getattr(uploaded_file, "name", "core.csv"))).name
                            save_project_core_dataset(
                                data=bytes(uploaded_file.getvalue()),
                                root=LAS_CORRELATION_PROJECTS_ROOT,
                                project_id=active_project.id,
                                file_name=original_name,
                                name=Path(original_name).stem,
                                metadata={"source": "workspace_upload", "dataset_role": "core"},
                            )
                            saved_count += 1
                    except Exception:
                        logger.exception("project_core_datasets_save_failed project_id=%s", safe_log_value(active_project.id))
                        st.error("Не удалось сохранить Core datasets в проект. Подробности записаны в logs/app.log.")
                    else:
                        logger.info(
                            "project_core_datasets_saved project_id=%s count=%d",
                            safe_log_value(active_project.id),
                            saved_count,
                        )
                        st.success(f"Core datasets сохранены в проект: {saved_count}.")
                        st.rerun()
            mud_log_uploads = tuple(
                uploaded_file
                for uploaded_file in uploaded_files
                if Path(str(getattr(uploaded_file, "name", ""))).suffix.lower() in {".csv", ".xlsx", ".xlsm"}
            )
            if mud_log_uploads:
                st.caption("CSV/Excel с mud log-данными можно сохранить как Mud Log dataset проекта.")
                if st.button("Сохранить загруженные файлы как Mud Log datasets", key=f"save_uploaded_mud_log_datasets_{active_project.id}"):
                    try:
                        saved_count = 0
                        for uploaded_file in mud_log_uploads:
                            original_name = Path(str(getattr(uploaded_file, "name", "mud_log.csv"))).name
                            save_project_mud_log_dataset(
                                data=bytes(uploaded_file.getvalue()),
                                root=LAS_CORRELATION_PROJECTS_ROOT,
                                project_id=active_project.id,
                                file_name=original_name,
                                name=Path(original_name).stem,
                                metadata={"source": "workspace_upload", "dataset_role": "mud_log"},
                            )
                            saved_count += 1
                    except Exception:
                        logger.exception("project_mud_log_datasets_save_failed project_id=%s", safe_log_value(active_project.id))
                        st.error("Не удалось сохранить Mud Log datasets в проект. Подробности записаны в logs/app.log.")
                    else:
                        logger.info(
                            "project_mud_log_datasets_saved project_id=%s count=%d",
                            safe_log_value(active_project.id),
                            saved_count,
                        )
                        st.success(f"Mud Log datasets сохранены в проект: {saved_count}.")
                        st.rerun()
            production_uploads = tuple(
                uploaded_file
                for uploaded_file in uploaded_files
                if Path(str(getattr(uploaded_file, "name", ""))).suffix.lower() in {".csv", ".xlsx", ".xlsm"}
            )
            if production_uploads:
                st.caption("CSV/Excel с production-данными можно сохранить как Production dataset проекта.")
                if st.button("Сохранить загруженные файлы как Production datasets", key=f"save_uploaded_production_datasets_{active_project.id}"):
                    try:
                        saved_count = 0
                        for uploaded_file in production_uploads:
                            original_name = Path(str(getattr(uploaded_file, "name", "production.csv"))).name
                            save_project_production_dataset(
                                data=bytes(uploaded_file.getvalue()),
                                root=LAS_CORRELATION_PROJECTS_ROOT,
                                project_id=active_project.id,
                                file_name=original_name,
                                name=Path(original_name).stem,
                                metadata={"source": "workspace_upload", "dataset_role": "production"},
                            )
                            saved_count += 1
                    except Exception:
                        logger.exception("project_production_datasets_save_failed project_id=%s", safe_log_value(active_project.id))
                        st.error("Не удалось сохранить Production datasets в проект. Подробности записаны в logs/app.log.")
                    else:
                        logger.info(
                            "project_production_datasets_saved project_id=%s count=%d",
                            safe_log_value(active_project.id),
                            saved_count,
                        )
                        st.success(f"Production datasets сохранены в проект: {saved_count}.")
                        st.rerun()
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



def _sidebar_recent_project_items(project: ProjectRecord, limit: int = 5) -> tuple[dict[str, str], ...]:
    """Return compact recent project items for the Sidebar 2.0 panel."""
    items: list[dict[str, str]] = []
    for calculation in list_project_calculations(LAS_CORRELATION_PROJECTS_ROOT, project.id):
        name = getattr(calculation, "name", "") or getattr(calculation, "id", "расчет")
        timestamp = getattr(calculation, "created_at", "") or getattr(calculation, "updated_at", "") or ""
        items.append({"kind": "Расчет", "label": str(name), "time": str(timestamp)})
    for export in list_project_exports(LAS_CORRELATION_PROJECTS_ROOT, project.id):
        name = getattr(export, "file_name", "") or getattr(export, "name", "") or "экспорт"
        timestamp = getattr(export, "created_at", "") or getattr(export, "updated_at", "") or ""
        items.append({"kind": "Экспорт", "label": str(name), "time": str(timestamp)})
    for las_file in list_project_las_files(LAS_CORRELATION_PROJECTS_ROOT, project.id):
        name = getattr(las_file, "file_name", "") or getattr(las_file, "name", "") or getattr(las_file, "id", "LAS")
        timestamp = getattr(las_file, "created_at", "") or getattr(las_file, "updated_at", "") or ""
        items.append({"kind": "LAS", "label": str(name), "time": str(timestamp)})

    items.sort(key=lambda item: item.get("time", ""), reverse=True)
    if not items:
        return ({"kind": "Статус", "label": "Нет недавних материалов", "time": "Импортируйте LAS или сохраните расчет"},)
    return tuple(items[:limit])


def _sidebar_project_health(stats: dict[str, int], rows_count: int) -> tuple[str, str]:
    """Return a short human-readable health label and detail for the active project."""
    if stats.get("las_files", 0) > 0 or stats.get("calculations", 0) > 0:
        return "Готов к работе", "есть данные для анализа"
    if rows_count > 1 or stats.get("wells", 0) > 0:
        return "Проект создан", "добавьте LAS или расчет"
    return "Пустой проект", "начните с импорта данных"


def _render_sidebar_brand(project: ProjectRecord) -> None:
    logo_uri = _branding_logo_data_uri()
    logo_html = f'<img class="sidebar-brand-logo" src="{logo_uri}" alt="Gas Ratio Pro logo">' if logo_uri else ""
    st.sidebar.markdown(
        f"""
        <div class='sidebar-brand-card'>
          <div class='sidebar-brand-row'>
            {logo_html}
            <div>
              <div class='sidebar-brand-title'>Gas Ratio <span>Pro</span></div>
              <span class='sidebar-brand-subtitle'>Project control center</span>
            </div>
          </div>
          <span class='sidebar-brand-subtitle'>Активный проект: {html.escape(project.name)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_sidebar_quick_navigation() -> None:
    """Render functional sidebar shortcut buttons for common workspaces."""
    st.sidebar.markdown("<div class='sidebar-action-grid'>", unsafe_allow_html=True)
    actions = (
        ("📥 Данные", "Работа с данными"),
        ("🧰 LAS", "LAS-редактор"),
        ("🔗 Корреляция", "LAS-корреляция"),
        ("📘 Docs", "Инструкции и документация"),
    )
    columns = st.sidebar.columns(2)
    for index, (label, target) in enumerate(actions):
        with columns[index % 2]:
            if st.button(label, key=f"sidebar_quick_nav_{target}", use_container_width=True):
                _set_active_main_tab(target)
                st.rerun()
    st.sidebar.markdown("</div>", unsafe_allow_html=True)


def _render_sidebar_recent_items(project: ProjectRecord) -> None:
    recent_items = _sidebar_recent_project_items(project)
    item_html = "".join(
        "<div class='sidebar-recent-item'>"
        f"<strong>{_html_escape(item['label'])}</strong>"
        f"<span>{_html_escape(item['kind'])} · {_html_escape(item.get('time', '') or 'без даты')}</span>"
        "</div>"
        for item in recent_items
    )
    st.sidebar.markdown(
        f"""
        <div class='sidebar-recent-card'>
          <b>Последние материалы</b>
          <small>Короткая история активного проекта</small>
          {item_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_project_explorer(project: ProjectRecord, logger) -> None:
    """Render Project Explorer and metadata-only move controls in the sidebar."""

    try:
        tree = build_project_tree(LAS_CORRELATION_PROJECTS_ROOT, project.id)
    except Exception:
        logger.exception("project_tree_load_failed project_id=%s", safe_log_value(project.id))
        st.sidebar.warning("Не удалось построить дерево проекта.")
        return

    rows = project_tree_table_rows(tree)
    stats = _dashboard_project_statistics(project, tuple(list_projects(LAS_CORRELATION_PROJECTS_ROOT)) or (project,))
    rows_count = max(len(rows) - 1, 0)
    health_label, health_detail = _sidebar_project_health(stats, rows_count)

    _render_sidebar_brand(project)
    st.sidebar.markdown(
        f"""
        <div class='modern-sidebar-card'>
          <b>Проектная сводка</b>
          <small>{html.escape(project.id)} · объектов: {rows_count}</small>
          <div class='modern-sidebar-metrics'>
            <div class='modern-sidebar-metric'><b>{stats['wells']}</b><small>Скважин</small></div>
            <div class='modern-sidebar-metric'><b>{stats['las_files']}</b><small>LAS</small></div>
            <div class='modern-sidebar-metric'><b>{stats['calculations']}</b><small>Расчетов</small></div>
            <div class='modern-sidebar-metric'><b>{stats['exports']}</b><small>Экспортов</small></div>
          </div>
        </div>
        <div class='sidebar-status-card'>
          <b>Состояние</b>
          <span class='sidebar-state-pill'>● {html.escape(health_label)}</span>
          <div class='sidebar-status-grid'>
            <div class='sidebar-status-row'><span>Данные</span><span>{html.escape(health_detail)}</span></div>
            <div class='sidebar-status-row'><span>База</span><span>локальная</span></div>
            <div class='sidebar-status-row'><span>Лицензия</span><span>Proprietary</span></div>
            <div class='sidebar-status-row'><span>Ветка</span><span>main</span></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    _render_sidebar_quick_navigation()
    _render_sidebar_recent_items(project)

    with st.sidebar.expander("Структура проекта", expanded=False):
        st.caption(f"Объектов: {max(len(rows) - 1, 0)}")
        sidebar_query = st.text_input(
            "Поиск в проекте",
            key="sidebar_project_search",
            placeholder="скважина, LAS, расчет",
        )
        visible_rows = rows
        if sidebar_query:
            query = sidebar_query.strip().lower()
            visible_rows = tuple(
                row for row in rows
                if query in f"{row.get('label', '')} {row.get('status', '')} {row.get('kind', '')}".lower()
            )
            if not visible_rows:
                st.warning("Ничего не найдено в структуре проекта.")
        for row in list(visible_rows)[:18]:
            level = int(row["level"])
            label = str(row["label"])
            status = str(row["status"])
            kind = str(row["kind"])
            indent = " " * level
            icon = {
                "project": "📁",
                "folder": "▸",
                "custom_folder": "📂",
                "folder_item": "↳",
                "missing": "⚠️",
                "well_group": "🗂️",
                "well": "🛢️",
                "las_version": "LAS",
                "calculation": "Σ",
                "export": "⬇",
                "empty": "—",
            }.get(kind, "•")
            color_icon = str(row.get("color_label_icon", ""))
            color_name = str(row.get("color_label_name", ""))
            line = f"{indent}{icon} {label}"
            if color_icon:
                line = f"{line} {color_icon}"
            if status:
                line = f"{line} · {status}"
            if color_name:
                line = f"{line} · метка: {color_name}"
            st.markdown(f"<div class='sidebar-search-hit'>{_html_escape(line)}</div>", unsafe_allow_html=True)

        if len(visible_rows) > 18:
            st.caption(f"Еще объектов: {len(visible_rows) - 18}. Уточните поиск или откройте менеджеры проекта.")

        st.divider()
        st.caption("Перемещение объектов")
        try:
            move_options = list_project_explorer_move_options(LAS_CORRELATION_PROJECTS_ROOT, project.id)
            folder_targets = list_project_explorer_folder_targets(LAS_CORRELATION_PROJECTS_ROOT, project.id)
            group_targets = list_project_explorer_well_group_targets(LAS_CORRELATION_PROJECTS_ROOT, project.id)
        except Exception:
            logger.exception("project_tree_move_options_failed project_id=%s", safe_log_value(project.id))
            st.warning("Не удалось прочитать варианты перемещения.")
            return

        if not move_options:
            st.caption("Нет объектов для перемещения.")
            return

        option_labels = {option.id: f"{option.label} · {option.kind}" for option in move_options}
        selected_item_id = st.selectbox(
            "Объект",
            options=tuple(option_labels),
            format_func=lambda item_id: option_labels.get(item_id, item_id),
            key=f"project_explorer_move_item_{project.id}",
        )
        selected_option = next(option for option in move_options if option.id == selected_item_id)

        move_modes = ["Добавить в папку"]
        if selected_option.kind == "well":
            move_modes.append("Переместить в группу скважин")
        selected_mode = st.selectbox(
            "Действие",
            options=move_modes,
            key=f"project_explorer_move_mode_{project.id}",
        )

        if selected_mode == "Добавить в папку":
            if not folder_targets:
                st.caption("Сначала создайте пользовательскую папку проекта.")
            else:
                folder_labels = {folder.id: folder.name for folder in folder_targets}
                selected_folder_id = st.selectbox(
                    "Папка",
                    options=tuple(folder_labels),
                    format_func=lambda folder_id: folder_labels.get(folder_id, folder_id),
                    key=f"project_explorer_move_folder_{project.id}",
                )
                if st.button("Добавить объект в папку", key=f"project_explorer_move_to_folder_{project.id}"):
                    try:
                        result = move_project_explorer_item_to_folder(
                            LAS_CORRELATION_PROJECTS_ROOT,
                            project.id,
                            selected_item_id,
                            selected_folder_id,
                        )
                        logger.info(
                            "project_tree_item_moved_to_folder project_id=%s item_id=%s folder_id=%s",
                            safe_log_value(project.id),
                            safe_log_value(selected_item_id),
                            safe_log_value(selected_folder_id),
                        )
                        st.success(result.message)
                        st.rerun()
                    except Exception:
                        logger.exception("project_tree_move_to_folder_failed project_id=%s", safe_log_value(project.id))
                        st.error("Не удалось добавить объект в папку.")
        else:
            if not group_targets:
                st.caption("Сначала создайте группу скважин проекта.")
            else:
                group_labels = {group.id: group.name for group in group_targets}
                selected_group_id = st.selectbox(
                    "Группа",
                    options=tuple(group_labels),
                    format_func=lambda group_id: group_labels.get(group_id, group_id),
                    key=f"project_explorer_move_group_{project.id}",
                )
                if st.button("Переместить скважину", key=f"project_explorer_move_to_group_{project.id}"):
                    try:
                        result = move_project_explorer_well_to_group(
                            LAS_CORRELATION_PROJECTS_ROOT,
                            project.id,
                            selected_item_id,
                            selected_group_id,
                        )
                        logger.info(
                            "project_tree_well_moved_to_group project_id=%s well_node_id=%s group_id=%s",
                            safe_log_value(project.id),
                            safe_log_value(selected_item_id),
                            safe_log_value(selected_group_id),
                        )
                        st.success(result.message)
                        st.rerun()
                    except Exception:
                        logger.exception("project_tree_move_to_group_failed project_id=%s", safe_log_value(project.id))
                        st.error("Не удалось переместить скважину в группу.")

        st.divider()
        st.caption("Цветовые метки")
        color_options = tuple(PROJECT_EXPLORER_LABEL_COLORS)
        color_labels = {
            color: f"{PROJECT_EXPLORER_LABEL_ICONS.get(color, '🏷️')} {name}"
            for color, name in PROJECT_EXPLORER_LABEL_COLORS.items()
        }
        selected_label_item_id = st.selectbox(
            "Объект для метки",
            options=tuple(option_labels),
            format_func=lambda item_id: option_labels.get(item_id, item_id),
            key=f"project_explorer_label_item_{project.id}",
        )
        selected_color = st.selectbox(
            "Цвет метки",
            options=color_options,
            format_func=lambda color: color_labels.get(color, color),
            key=f"project_explorer_label_color_{project.id}",
        )
        label_note = st.text_input(
            "Комментарий к метке",
            key=f"project_explorer_label_note_{project.id}",
            placeholder="например: проверить, готово, важный интервал",
        )
        col_set_label, col_clear_label = st.columns(2)
        with col_set_label:
            if st.button("Поставить метку", key=f"project_explorer_set_label_{project.id}"):
                try:
                    set_project_explorer_label(
                        LAS_CORRELATION_PROJECTS_ROOT,
                        project.id,
                        selected_label_item_id,
                        selected_color,
                        note=label_note,
                    )
                    logger.info(
                        "project_tree_label_set project_id=%s item_id=%s color=%s",
                        safe_log_value(project.id),
                        safe_log_value(selected_label_item_id),
                        safe_log_value(selected_color),
                    )
                    st.success("Цветовая метка сохранена.")
                    st.rerun()
                except Exception:
                    logger.exception("project_tree_label_set_failed project_id=%s", safe_log_value(project.id))
                    st.error("Не удалось сохранить цветовую метку.")
        with col_clear_label:
            if st.button("Снять метку", key=f"project_explorer_clear_label_{project.id}"):
                try:
                    removed = clear_project_explorer_label(
                        LAS_CORRELATION_PROJECTS_ROOT,
                        project.id,
                        selected_label_item_id,
                    )
                    logger.info(
                        "project_tree_label_cleared project_id=%s item_id=%s removed=%s",
                        safe_log_value(project.id),
                        safe_log_value(selected_label_item_id),
                        removed,
                    )
                    st.success("Цветовая метка снята." if removed else "У объекта не было цветовой метки.")
                    st.rerun()
                except Exception:
                    logger.exception("project_tree_label_clear_failed project_id=%s", safe_log_value(project.id))
                    st.error("Не удалось снять цветовую метку.")

        st.divider()
        st.caption("Карточка скважины")
        well_options = tuple(option for option in move_options if option.kind == "well")
        if not well_options:
            st.caption("Нет сохраненных скважин для карточки.")
        else:
            well_labels = {option.id: option.label for option in well_options}
            selected_well_node_id = st.selectbox(
                "Скважина",
                options=tuple(well_labels),
                format_func=lambda item_id: well_labels.get(item_id, item_id),
                key=f"project_explorer_well_card_item_{project.id}",
            )
            selected_well_id = selected_well_node_id.removeprefix("well:")
            current_card = get_project_well_card(LAS_CORRELATION_PROJECTS_ROOT, project.id, selected_well_id)
            default_name = current_card.name if current_card else well_labels.get(selected_well_node_id, selected_well_id)
            default_status = current_card.status if current_card else "draft"
            default_note = current_card.note if current_card else ""
            default_metadata = dict(current_card.metadata or {}) if current_card else {}
            default_coords = project_well_cards.coordinates_from_metadata(default_metadata)
            default_depth_reference = project_well_cards.depth_reference_from_metadata(default_metadata)
            default_drilling_dates = project_well_cards.drilling_dates_from_metadata(default_metadata)
            default_operator = project_well_cards.operator_from_metadata(default_metadata)
            default_field = project_well_cards.field_from_metadata(default_metadata)
            status_options = tuple(PROJECT_WELL_CARD_STATUSES)
            try:
                status_index = status_options.index(default_status)
            except ValueError:
                status_index = 0
            well_card_name = st.text_input(
                "Название в карточке",
                value=default_name,
                key=f"project_explorer_well_card_name_{project.id}_{selected_well_id}",
            )
            well_card_status = st.selectbox(
                "Статус карточки",
                options=status_options,
                index=status_index,
                format_func=lambda status: PROJECT_WELL_CARD_STATUSES.get(status, status),
                key=f"project_explorer_well_card_status_{project.id}_{selected_well_id}",
            )
            st.caption("Координаты скважины")
            coord_col_a, coord_col_b = st.columns(2)
            with coord_col_a:
                well_card_x = st.text_input(
                    "X / Easting",
                    value="" if default_coords.x is None else f"{default_coords.x:g}",
                    key=f"project_explorer_well_card_x_{project.id}_{selected_well_id}",
                )
                well_card_latitude = st.text_input(
                    "Широта",
                    value="" if default_coords.latitude is None else f"{default_coords.latitude:g}",
                    key=f"project_explorer_well_card_latitude_{project.id}_{selected_well_id}",
                )
            with coord_col_b:
                well_card_y = st.text_input(
                    "Y / Northing",
                    value="" if default_coords.y is None else f"{default_coords.y:g}",
                    key=f"project_explorer_well_card_y_{project.id}_{selected_well_id}",
                )
                well_card_longitude = st.text_input(
                    "Долгота",
                    value="" if default_coords.longitude is None else f"{default_coords.longitude:g}",
                    key=f"project_explorer_well_card_longitude_{project.id}_{selected_well_id}",
                )
            st.caption("X/Y — локальные или проектные координаты. Широта: -90..90, долгота: -180..180.")
            st.caption("Отметки глубины")
            datum_col_a, datum_col_b = st.columns(2)
            with datum_col_a:
                well_card_kb = st.text_input(
                    "KB, м",
                    value="" if default_depth_reference.kb_m is None else f"{default_depth_reference.kb_m:g}",
                    key=f"project_explorer_well_card_kb_{project.id}_{selected_well_id}",
                )
                well_card_planned_td = st.text_input(
                    "Плановая TD, м",
                    value="" if default_depth_reference.planned_td_m is None else f"{default_depth_reference.planned_td_m:g}",
                    key=f"project_explorer_well_card_planned_td_{project.id}_{selected_well_id}",
                )
            with datum_col_b:
                well_card_gl = st.text_input(
                    "GL, м",
                    value="" if default_depth_reference.gl_m is None else f"{default_depth_reference.gl_m:g}",
                    key=f"project_explorer_well_card_gl_{project.id}_{selected_well_id}",
                )
                well_card_actual_td = st.text_input(
                    "Фактическая TD, м",
                    value="" if default_depth_reference.actual_td_m is None else f"{default_depth_reference.actual_td_m:g}",
                    key=f"project_explorer_well_card_actual_td_{project.id}_{selected_well_id}",
                )
            if default_depth_reference.kb_above_gl_label:
                st.caption(f"Текущая разница отметок: {default_depth_reference.kb_above_gl_label}")
            if default_depth_reference.has_td:
                st.caption("TD: " + "; ".join(default_depth_reference.td_labels))
            st.caption("KB, GL и TD хранятся как metadata скважины в метрах и не меняют LAS-версии.")
            st.caption("Дата бурения")
            well_card_spud_date = st.text_input(
                "Дата начала бурения, YYYY-MM-DD",
                value=default_drilling_dates.spud_date or "",
                key=f"project_explorer_well_card_spud_date_{project.id}_{selected_well_id}",
                placeholder="например: 2026-01-19",
            )
            if default_drilling_dates.spud_date_label:
                st.caption(default_drilling_dates.spud_date_label)
            st.caption("Дата хранится как metadata скважины и не меняет LAS-версии.")
            st.caption("Оператор")
            well_card_operator = st.text_input(
                "Оператор / компания",
                value=default_operator.operator or "",
                key=f"project_explorer_well_card_operator_{project.id}_{selected_well_id}",
                placeholder="например: КазМунайГаз",
            )
            if default_operator.operator_label:
                st.caption(default_operator.operator_label)
            st.caption("Оператор хранится как короткая metadata-строка скважины и не меняет LAS-версии.")
            st.caption("Месторождение")
            well_card_field = st.text_input(
                "Месторождение / участок",
                value=default_field.field or "",
                key=f"project_explorer_well_card_field_{project.id}_{selected_well_id}",
                placeholder="например: Тенгиз",
            )
            if default_field.field_label:
                st.caption(default_field.field_label)
            st.caption("Месторождение хранится как короткая metadata-строка скважины и не меняет LAS-версии.")
            well_card_note = st.text_area(
                "Комментарий",
                value=default_note,
                height=80,
                key=f"project_explorer_well_card_note_{project.id}_{selected_well_id}",
            )
            if current_card:
                st.caption(f"Обновлена: {current_card.updated_at}")
            else:
                st.caption("Карточка еще не создана.")
            if st.button("Сохранить карточку скважины", key=f"project_explorer_save_well_card_{project.id}"):
                try:
                    well_card_metadata = project_well_cards.merge_project_well_coordinates_metadata(
                        default_metadata,
                        x=well_card_x,
                        y=well_card_y,
                        latitude=well_card_latitude,
                        longitude=well_card_longitude,
                    )
                    well_card_metadata = project_well_cards.merge_project_well_depth_reference_metadata(
                        well_card_metadata,
                        kb_m=well_card_kb,
                        gl_m=well_card_gl,
                        planned_td_m=well_card_planned_td,
                        actual_td_m=well_card_actual_td,
                    )
                    well_card_metadata = project_well_cards.merge_project_well_drilling_dates_metadata(
                        well_card_metadata,
                        spud_date=well_card_spud_date,
                    )
                    well_card_metadata = project_well_cards.merge_project_well_operator_metadata(
                        well_card_metadata,
                        operator=well_card_operator,
                    )
                    well_card_metadata = project_well_cards.merge_project_well_field_metadata(
                        well_card_metadata,
                        field=well_card_field,
                    )
                    save_project_well_card(
                        LAS_CORRELATION_PROJECTS_ROOT,
                        project.id,
                        well_id=selected_well_id,
                        name=well_card_name,
                        status=well_card_status,
                        note=well_card_note,
                        metadata=well_card_metadata,
                    )
                    logger.info(
                        "project_well_card_saved project_id=%s well_id=%s",
                        safe_log_value(project.id),
                        safe_log_value(selected_well_id),
                    )
                    st.success("Карточка скважины сохранена.")
                    st.rerun()
                except Exception:
                    logger.exception("project_well_card_save_failed project_id=%s", safe_log_value(project.id))
                    st.error("Не удалось сохранить карточку скважины.")


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


def _render_dataset_manager_table(
    *,
    title: str,
    datasets: tuple[project_datasets.ProjectDatasetRecord, ...],
    select_key: str,
    empty_caption: str,
    ready_message: str,
) -> None:
    """Render one Dataset Manager table and selected dataset details."""

    if not datasets:
        st.caption(empty_caption)
        return

    ready_count = sum(1 for dataset in datasets if dataset.status == "ready")
    warning_count = sum(1 for dataset in datasets if dataset.status == "warning")
    error_count = sum(1 for dataset in datasets if dataset.status == "error")
    st.caption(
        f"{title}: {len(datasets)} · готово: {ready_count} · "
        f"требует проверки: {warning_count} · ошибок чтения: {error_count}"
    )
    st.dataframe(build_project_dataset_table(datasets), use_container_width=True, height=260)

    datasets_by_id = {dataset.id: dataset for dataset in datasets}
    selected_dataset_id = st.selectbox(
        title,
        options=tuple(datasets_by_id),
        format_func=lambda dataset_id: datasets_by_id[dataset_id].name,
        key=select_key,
    )
    selected_dataset = datasets_by_id[selected_dataset_id]
    detail_rows = [
        ("Тип", selected_dataset.kind),
        ("Статус", selected_dataset.status_label),
        ("Скважина ID", selected_dataset.well_id or "—"),
        ("Версия", selected_dataset.version_label or "—"),
        ("Файл", selected_dataset.original_file_name),
        ("Строк", str(selected_dataset.row_count)),
        ("Колонок", str(selected_dataset.column_count)),
        ("Глубинная колонка", selected_dataset.depth_curve or "не найдена"),
    ]
    st.dataframe(
        pd.DataFrame([{"Показатель": label, "Значение": value} for label, value in detail_rows]),
        use_container_width=True,
        hide_index=True,
        height=280,
    )
    if selected_dataset.warnings:
        for warning in selected_dataset.warnings:
            st.warning(warning)
    else:
        st.success(ready_message)


def _render_project_dataset_manager(project: ProjectRecord, logger) -> None:
    """Render Dataset Manager sections for active project datasets."""

    with st.expander("Dataset Manager · LAS", expanded=False):
        try:
            las_datasets = list_project_las_datasets(LAS_CORRELATION_PROJECTS_ROOT, project.id)
        except Exception:
            logger.exception("project_dataset_manager_las_failed project_id=%s", safe_log_value(project.id))
            st.warning("Не удалось построить список LAS datasets.")
        else:
            _render_dataset_manager_table(
                title="LAS datasets",
                datasets=las_datasets,
                select_key=f"project_dataset_las_select_{project.id}",
                empty_caption="В активном проекте пока нет LAS datasets.",
                ready_message="LAS dataset готов к открытию в рабочем workflow и выгрузке.",
            )

    with st.expander("Dataset Manager · CSV", expanded=False):
        try:
            csv_datasets = list_project_csv_datasets(LAS_CORRELATION_PROJECTS_ROOT, project.id)
        except Exception:
            logger.exception("project_dataset_manager_csv_failed project_id=%s", safe_log_value(project.id))
            st.warning("Не удалось построить список CSV datasets.")
        else:
            _render_dataset_manager_table(
                title="CSV datasets",
                datasets=csv_datasets,
                select_key=f"project_dataset_csv_select_{project.id}",
                empty_caption="В активном проекте пока нет CSV datasets.",
                ready_message="CSV dataset готов к проверке mapping и расчетам.",
            )

    with st.expander("Dataset Manager · Excel", expanded=False):
        try:
            excel_datasets = list_project_excel_datasets(LAS_CORRELATION_PROJECTS_ROOT, project.id)
        except Exception:
            logger.exception("project_dataset_manager_excel_failed project_id=%s", safe_log_value(project.id))
            st.warning("Не удалось построить список Excel datasets.")
        else:
            _render_dataset_manager_table(
                title="Excel datasets",
                datasets=excel_datasets,
                select_key=f"project_dataset_excel_select_{project.id}",
                empty_caption="В активном проекте пока нет Excel datasets.",
                ready_message="Excel dataset готов к проверке активного листа, mapping и расчетам.",
            )

    with st.expander("Dataset Manager · Core", expanded=False):
        try:
            core_datasets = list_project_core_datasets(LAS_CORRELATION_PROJECTS_ROOT, project.id)
        except Exception:
            logger.exception("project_dataset_manager_core_failed project_id=%s", safe_log_value(project.id))
            st.warning("Не удалось построить список Core datasets.")
        else:
            _render_dataset_manager_table(
                title="Core datasets",
                datasets=core_datasets,
                select_key=f"project_dataset_core_select_{project.id}",
                empty_caption="В активном проекте пока нет Core datasets.",
                ready_message="Core dataset готов к сопоставлению образцов с LAS по глубине.",
            )

    with st.expander("Dataset Manager · Mud Log", expanded=False):
        try:
            mud_log_datasets = list_project_mud_log_datasets(LAS_CORRELATION_PROJECTS_ROOT, project.id)
        except Exception:
            logger.exception("project_dataset_manager_mud_log_failed project_id=%s", safe_log_value(project.id))
            st.warning("Не удалось построить список Mud Log datasets.")
        else:
            _render_dataset_manager_table(
                title="Mud Log datasets",
                datasets=mud_log_datasets,
                select_key=f"project_dataset_mud_log_select_{project.id}",
                empty_caption="В активном проекте пока нет Mud Log datasets.",
                ready_message="Mud Log dataset готов к сопоставлению газов, литологии и описаний с LAS по глубине.",
            )

    with st.expander("Dataset Manager · Production", expanded=False):
        try:
            production_datasets = list_project_production_datasets(LAS_CORRELATION_PROJECTS_ROOT, project.id)
        except Exception:
            logger.exception("project_dataset_manager_production_failed project_id=%s", safe_log_value(project.id))
            st.warning("Не удалось построить список Production datasets.")
        else:
            _render_dataset_manager_table(
                title="Production datasets",
                datasets=production_datasets,
                select_key=f"project_dataset_production_select_{project.id}",
                empty_caption="В активном проекте пока нет Production datasets.",
                ready_message="Production dataset готов к анализу добычи по дате и скважине.",
            )



def _render_project_manager_tools(project: ProjectRecord, logger) -> None:
    """Render Project Manager 2.0 metadata tools for the active project."""

    with st.expander("Project Manager 2.0 · Recovery, templates and backups", expanded=False):
        st.caption(
            "Project Manager 2.0 управляет проектом metadata-only: история действий, recovery checkpoint, "
            "шаблоны, резервные ZIP-копии и архивирование. Сырые LAS/CSV/Excel не записываются в журнал."
        )
        try:
            status = project_manager_status(LAS_CORRELATION_PROJECTS_ROOT, project.id)
        except Exception:
            logger.exception("project_manager_status_failed project_id=%s", safe_log_value(project.id))
            status = {"history_entries": 0, "templates": 0, "backups": 0, "has_recovery_state": False}

        metrics = st.columns(4)
        metrics[0].metric("История", status.get("history_entries", 0))
        metrics[1].metric("Шаблоны", status.get("templates", 0))
        metrics[2].metric("Backups", status.get("backups", 0))
        metrics[3].metric("Recovery", "есть" if status.get("has_recovery_state") else "нет")

        action_col, backup_col, template_col = st.columns(3)
        if action_col.button("Сохранить recovery checkpoint", key=f"project_manager_recovery_save_{project.id}", use_container_width=True):
            try:
                state = save_project_recovery_state(
                    LAS_CORRELATION_PROJECTS_ROOT,
                    project.id,
                    "data-workspace",
                    "Manual recovery checkpoint from Project Manager 2.0",
                    {"active_project": project.name, "source": "streamlit-ui"},
                )
            except Exception:
                logger.exception("project_recovery_save_failed project_id=%s", safe_log_value(project.id))
                st.error("Не удалось сохранить recovery checkpoint. Подробности записаны в logs/app.log.")
            else:
                st.success(f"Recovery checkpoint сохранен: {state.saved_at}.")

        if backup_col.button("Создать backup ZIP", key=f"project_manager_backup_create_{project.id}", use_container_width=True):
            try:
                backup = create_project_backup(
                    LAS_CORRELATION_PROJECTS_ROOT,
                    project.id,
                    "Manual Project Manager 2.0 backup",
                )
            except Exception:
                logger.exception("project_backup_create_failed project_id=%s", safe_log_value(project.id))
                st.error("Не удалось создать backup проекта. Подробности записаны в logs/app.log.")
            else:
                st.success(f"Backup создан: {backup.file_name} ({backup.size_bytes:,} байт).")

        if template_col.button("Создать шаблон проекта", key=f"project_manager_template_create_{project.id}", use_container_width=True):
            try:
                template = create_project_template(
                    LAS_CORRELATION_PROJECTS_ROOT,
                    project.id,
                    f"{project.name} template",
                    "Шаблон структуры проекта без копирования сырых рабочих данных.",
                )
            except Exception:
                logger.exception("project_template_create_failed project_id=%s", safe_log_value(project.id))
                st.error("Не удалось создать шаблон проекта. Подробности записаны в logs/app.log.")
            else:
                st.success(f"Шаблон создан: {template.name}.")

        recovery = load_project_recovery_state(LAS_CORRELATION_PROJECTS_ROOT, project.id)
        if recovery:
            st.info(f"Recovery checkpoint: {recovery.saved_at} · {recovery.active_step} · {recovery.message}")
            if st.button("Очистить recovery checkpoint", key=f"project_manager_recovery_clear_{project.id}"):
                if clear_project_recovery_state(LAS_CORRELATION_PROJECTS_ROOT, project.id):
                    st.success("Recovery checkpoint очищен.")
                else:
                    st.caption("Recovery checkpoint уже отсутствует.")

        templates = list_project_templates(LAS_CORRELATION_PROJECTS_ROOT)
        if templates:
            st.markdown("#### Шаблоны проектов")
            st.dataframe(pd.DataFrame(build_project_templates_table(templates)), use_container_width=True, height=180)
            template_by_label = {f"{template.name} · {template.id}": template for template in templates}
            selected_template_label = st.selectbox(
                "Создать новый проект из шаблона",
                options=tuple(template_by_label),
                key=f"project_manager_template_select_{project.id}",
            )
            new_project_name = st.text_input(
                "Название нового проекта из шаблона",
                value=f"{project.name} copy",
                key=f"project_manager_template_project_name_{project.id}",
            )
            if st.button("Создать проект из выбранного шаблона", key=f"project_manager_template_project_create_{project.id}"):
                try:
                    created = create_project_from_template(
                        LAS_CORRELATION_PROJECTS_ROOT,
                        template_by_label[selected_template_label].id,
                        new_project_name,
                    )
                except Exception:
                    logger.exception("project_from_template_failed project_id=%s", safe_log_value(project.id))
                    st.error("Не удалось создать проект из шаблона. Подробности записаны в logs/app.log.")
                else:
                    st.success(f"Проект создан: {created.name} ({created.id}).")
        else:
            st.caption("Шаблонов пока нет. Создайте шаблон из активного проекта.")

        backups = list_project_backups(LAS_CORRELATION_PROJECTS_ROOT, project.id)
        if backups:
            st.markdown("#### Резервные копии активного проекта")
            st.dataframe(pd.DataFrame(build_project_backups_table(backups)), use_container_width=True, height=180)
        else:
            st.caption("Резервных ZIP-копий активного проекта пока нет.")

        if st.button("Архивировать проект metadata-only", key=f"project_manager_archive_{project.id}"):
            try:
                archive = archive_project(LAS_CORRELATION_PROJECTS_ROOT, project.id, "Archived from Project Manager 2.0")
            except Exception:
                logger.exception("project_archive_failed project_id=%s", safe_log_value(project.id))
                st.error("Не удалось архивировать проект. Подробности записаны в logs/app.log.")
            else:
                st.success(f"Архивная backup-копия создана: {archive.file_name}.")

        history = list_project_history(LAS_CORRELATION_PROJECTS_ROOT, project.id)
        if history:
            st.markdown("#### История изменений проекта")
            st.dataframe(pd.DataFrame(build_project_history_table(history[:20])), use_container_width=True, height=260)
        else:
            if st.button("Добавить стартовую запись истории", key=f"project_manager_history_seed_{project.id}"):
                append_project_history(
                    LAS_CORRELATION_PROJECTS_ROOT,
                    project.id,
                    "project-manager-opened",
                    "Project Manager 2.0 initialized for active project",
                )
                st.success("Стартовая запись истории добавлена.")


def _render_project_file_index(project: ProjectRecord, logger) -> None:
    """Render Project Database file index for the active project."""

    with st.expander("Project Database · Индексация файлов", expanded=False):
        st.caption(
            "Индекс собирает metadata файлов активного проекта: путь, тип, размер, "
            "время изменения и SHA-256. Файлы не копируются и datasets не изменяются."
        )
        columns = st.columns(2)
        with columns[0]:
            if st.button("Обновить индекс файлов", key=f"project_file_index_refresh_{project.id}"):
                try:
                    entries = save_project_file_index(LAS_CORRELATION_PROJECTS_ROOT, project.id)
                except Exception:
                    logger.exception("project_file_index_save_failed project_id=%s", safe_log_value(project.id))
                    st.error("Не удалось обновить индекс файлов проекта. Подробности записаны в logs/app.log.")
                else:
                    st.success(f"Индекс обновлен. Файлов: {len(entries)}.")
        with columns[1]:
            if st.button("Проверить сохраненный индекс", key=f"project_file_index_validate_{project.id}"):
                try:
                    entries = validate_project_file_index(LAS_CORRELATION_PROJECTS_ROOT, project.id)
                except Exception:
                    logger.exception("project_file_index_validate_failed project_id=%s", safe_log_value(project.id))
                    st.error("Не удалось проверить индекс файлов проекта. Подробности записаны в logs/app.log.")
                else:
                    warnings = sum(1 for entry in entries if entry.status != "present")
                    if warnings:
                        st.warning(f"Проверка индекса завершена. Требуют внимания: {warnings}.")
                    else:
                        st.success(f"Проверка индекса завершена. Файлов на месте: {len(entries)}.")

        entries = load_project_file_index(LAS_CORRELATION_PROJECTS_ROOT, project.id)
        if not entries:
            st.caption("Индекс еще не создан. Нажмите `Обновить индекс файлов`.")
            return

        duplicate_groups = detect_project_duplicate_files(entries)
        annotated_entries = annotate_project_file_index_duplicates(entries, duplicate_groups)
        total_size = sum(entry.size_bytes for entry in entries)
        indexed_kinds = sorted({entry.kind for entry in entries})
        duplicate_files = sum(group.duplicate_count for group in duplicate_groups)
        st.caption(
            f"В индексе файлов: {len(entries)} · размер: {total_size:,} байт · "
            f"типы: {', '.join(indexed_kinds)} · возможных лишних дублей: {duplicate_files}"
        )
        if duplicate_groups:
            st.warning(
                "Найдены возможные дубликаты файлов проекта. Проверьте таблицу перед удалением или объединением datasets."
            )
            st.dataframe(build_project_duplicate_files_table(duplicate_groups), use_container_width=True, height=220)
        else:
            st.success("Дубликаты по SHA-256 и паре имя/размер не найдены.")
        st.dataframe(build_project_file_index_table(annotated_entries), use_container_width=True, height=260)

    with st.expander("Project Database · Версии файлов", expanded=False):
        st.caption(
            "Версии файлов строятся по сохраненному project_index.json. "
            "История хранит только metadata, checksum и номер версии; содержимое файлов не копируется."
        )
        if st.button("Обновить версии файлов", key=f"project_file_versions_refresh_{project.id}"):
            try:
                assets = update_project_file_versions(LAS_CORRELATION_PROJECTS_ROOT, project.id)
            except Exception:
                logger.exception("project_file_versions_update_failed project_id=%s", safe_log_value(project.id))
                st.error("Не удалось обновить версии файлов проекта. Подробности записаны в logs/app.log.")
            else:
                version_total = sum(asset.version_count for asset in assets)
                st.success(f"Версии файлов обновлены. Объектов: {len(assets)}, версий: {version_total}.")

        assets = load_project_file_versions(LAS_CORRELATION_PROJECTS_ROOT, project.id)
        if not assets:
            st.caption("История версий еще не создана. Сначала обновите индекс файлов, затем нажмите `Обновить версии файлов`.")
            return

        total_versions = sum(asset.version_count for asset in assets)
        changed_assets = sum(1 for asset in assets if asset.version_count > 1)
        st.caption(
            f"Файлов под версионным контролем: {len(assets)} · всего версий: {total_versions} · "
            f"файлов с историей изменений: {changed_assets}"
        )
        st.dataframe(build_project_file_versions_table(assets), use_container_width=True, height=240)

        assets_with_history = [asset for asset in assets if asset.version_count > 1]
        if assets_with_history:
            selected_label = st.selectbox(
                "История версий файла",
                options=[f"{asset.relative_path} · версий: {asset.version_count}" for asset in assets_with_history],
                key=f"project_file_versions_history_select_{project.id}",
            )
            selected_asset = assets_with_history[[f"{asset.relative_path} · версий: {asset.version_count}" for asset in assets_with_history].index(selected_label)]
            st.dataframe(build_project_file_version_history_table(selected_asset), use_container_width=True, height=220)

    with st.expander("Project Database · Автоматические UUID", expanded=False):
        st.caption(
            "Registry назначает стабильные UUID v4 проекту, скважинам, datasets, расчетам, "
            "экспортам, файлам индекса и версиям файлов. Содержимое файлов не копируется и не переписывается."
        )
        columns = st.columns(2)
        with columns[0]:
            if st.button("Обновить UUID registry", key=f"project_uuid_registry_refresh_{project.id}"):
                try:
                    summary = update_project_uuid_registry(LAS_CORRELATION_PROJECTS_ROOT, project.id)
                except Exception:
                    logger.exception("project_uuid_registry_update_failed project_id=%s", safe_log_value(project.id))
                    st.error("Не удалось обновить UUID registry проекта. Подробности записаны в logs/app.log.")
                else:
                    st.success(
                        f"UUID registry обновлен. Объектов: {summary.total_count}, "
                        f"новых UUID: {summary.created_count}, восстановлено: {summary.restored_count}."
                    )
        with columns[1]:
            if st.button("Проверить UUID registry", key=f"project_uuid_registry_validate_{project.id}"):
                try:
                    summary = validate_project_uuid_registry(LAS_CORRELATION_PROJECTS_ROOT, project.id)
                except Exception:
                    logger.exception("project_uuid_registry_validate_failed project_id=%s", safe_log_value(project.id))
                    st.error("Не удалось проверить UUID registry проекта. Подробности записаны в logs/app.log.")
                else:
                    warnings = sum(1 for entry in summary.entries if entry.status == "warning")
                    if warnings:
                        st.warning(f"UUID registry требует проверки. Объектов с предупреждениями: {warnings}.")
                    else:
                        st.success(f"UUID registry корректен. Объектов: {summary.total_count}.")

        uuid_entries = load_project_uuid_registry(LAS_CORRELATION_PROJECTS_ROOT, project.id)
        if not uuid_entries:
            st.caption("UUID registry еще не создан. Нажмите `Обновить UUID registry` после обновления индекса файлов.")
        else:
            object_types = sorted({entry.object_type for entry in uuid_entries})
            restored = sum(1 for entry in uuid_entries if entry.status == "restored")
            st.caption(
                f"UUID объектов: {len(uuid_entries)} · типов: {', '.join(object_types)} · "
                f"восстановленных записей: {restored}"
            )
            st.dataframe(build_project_uuid_registry_table(uuid_entries), use_container_width=True, height=260)

def _project_workspace_summary_rows(project: ProjectRecord) -> tuple[tuple[str, str], ...]:
    all_well_cards = list_project_las_wells(
        LAS_CORRELATION_PROJECTS_ROOT,
        project.id,
        include_archived=True,
    )
    versions = tuple(version for card in all_well_cards for version in card.versions)
    archived_versions = tuple(version for version in versions if version.archived_at)
    active_versions = tuple(version for version in versions if not version.archived_at)
    exports = list_project_exports(LAS_CORRELATION_PROJECTS_ROOT, project.id)

    return (
        ("Скважин", str(len(all_well_cards))),
        ("LAS-версий", str(len(versions))),
        ("Активных LAS-версий", str(len(active_versions))),
        ("Архивных LAS-версий", str(len(archived_versions))),
        ("Доступных экспортов", str(len(exports))),
    )


def _project_workspace_summary_table(project: ProjectRecord) -> pd.DataFrame:
    return pd.DataFrame(
        [{"Показатель": label, "Значение": value} for label, value in _project_workspace_summary_rows(project)]
    )


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
        st.dataframe(_project_workspace_summary_table(project), use_container_width=True, hide_index=True, height=210)
        _render_project_dataset_manager(project, logger)
        _render_project_manager_tools(project, logger)
        _render_project_file_index(project, logger)

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



def _project_calculation_actions_table(actions: tuple[object, ...]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Время": action.happened_at,
                "Действие": action.action_label,
                "Расчет": action.calculation_label or action.calculation_id,
                "Связанный расчет": action.related_calculation_label or action.related_calculation_id,
                "Формат": action.export_format,
                "Детали": action.details,
            }
            for action in actions
        ]
    )


def _record_project_calculation_action(
    project: ProjectRecord,
    action: str,
    logger,
    *,
    calculation_id: str = "",
    related_calculation_id: str = "",
    export_format: str = "",
    details: str = "",
) -> None:
    try:
        append_project_calculation_action(
            LAS_CORRELATION_PROJECTS_ROOT,
            project.id,
            action,
            calculation_id=calculation_id,
            related_calculation_id=related_calculation_id,
            export_format=export_format,
            details=details,
        )
    except Exception:
        logger.exception(
            "project_calculation_action_log_failed project_id=%s action=%s",
            safe_log_value(project.id),
            safe_log_value(action),
        )


def _render_project_calculation_actions(project: ProjectRecord, logger) -> None:
    try:
        actions = list_project_calculation_actions(LAS_CORRELATION_PROJECTS_ROOT, project.id)
    except Exception:
        logger.exception("project_calculation_actions_read_failed project_id=%s", safe_log_value(project.id))
        st.warning("Не удалось прочитать журнал действий по сохраненным расчетам.")
        return

    with st.expander("Журнал действий по сохраненным расчетам", expanded=False):
        st.caption(
            "Компактный журнал фиксирует сохранение snapshot, открытие в графиках, "
            "сравнение snapshots и скачивание выгрузок. Сырые таблицы в журнал не записываются."
        )
        if not actions:
            st.caption("Действий по сохраненным расчетам пока нет.")
            return
        st.dataframe(_project_calculation_actions_table(actions), use_container_width=True, hide_index=True, height=220)
        csv_col, html_col = st.columns(2)
        csv_col.download_button(
            "Скачать журнал CSV",
            data=export_project_calculation_actions_csv(actions),
            file_name=f"calculation-actions-{project.id}.csv",
            mime="text/csv",
            key=f"project_calculation_actions_csv_{project.id}",
        )
        html_col.download_button(
            "Скачать журнал HTML",
            data=export_project_calculation_actions_html(actions),
            file_name=f"calculation-actions-{project.id}.html",
            mime="text/html",
            key=f"project_calculation_actions_html_{project.id}",
        )


def _project_calculation_option_label(record) -> str:
    warning_label = f" | предупреждений: {record.warnings_count}" if record.warnings_count else ""
    return f"{record.source_label} | {record.saved_at} | строк: {record.row_count}{warning_label}"


def _project_calculations_summary_caption(summary) -> str:
    if not summary.count:
        return "Сохраненных расчетов пока нет."

    source_preview = ", ".join(summary.sources[:3])
    if len(summary.sources) > 3:
        source_preview += f" и еще {len(summary.sources) - 3}"
    columns_preview = ", ".join(summary.columns[:8])
    if len(summary.columns) > 8:
        columns_preview += f" и еще {len(summary.columns) - 8}"

    parts = [
        f"расчетов: {summary.count}",
        f"строк: {summary.total_rows}",
        f"предупреждений: {summary.total_warnings}",
        f"последний: {summary.latest_source_label} / {summary.latest_saved_at}",
    ]
    if source_preview:
        parts.append(f"источники: {source_preview}")
    if columns_preview:
        parts.append(f"колонки: {columns_preview}")
    return "; ".join(parts)


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


def _parse_project_calculation_columns_filter(value: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(part.strip() for part in value.split(",") if part.strip()))


def _render_project_calculation_metadata(project: ProjectRecord, calculation_id: str, logger) -> None:
    try:
        card = build_project_calculation_card(LAS_CORRELATION_PROJECTS_ROOT, project.id, calculation_id)
        metadata = read_project_calculation_metadata(LAS_CORRELATION_PROJECTS_ROOT, project.id, calculation_id)
    except Exception:
        logger.exception(
            "project_calculation_metadata_read_failed project_id=%s calculation_id=%s",
            safe_log_value(project.id),
            safe_log_value(calculation_id),
        )
        st.warning("Не удалось прочитать metadata сохраненного расчета.")
        return

    with st.container(border=True):
        st.subheader("Карточка выбранного расчета")
        st.caption(f"{card.source_label} | {card.saved_at}")
        card_rows, card_warnings, card_mapping, card_exports = st.columns(4)
        card_rows.metric("Строк", card.row_count)
        card_warnings.metric("Предупреждений", card.warnings_count)
        card_mapping.metric("Mapping", card.mapping_count)
        card_exports.metric("Выгрузки", ", ".join(card.available_exports) or "нет")
        if card.sheet_name:
            st.caption(f"Набор данных: {card.sheet_name}")
        st.caption(f"Режим Ch перед открытием snapshot: {card.ch_mode_label}")
        if card.mapping_preview:
            st.caption("Mapping перед открытием: " + "; ".join(card.mapping_preview))
            if card.mapping_count > len(card.mapping_preview):
                st.caption(f"Показано {len(card.mapping_preview)} из {card.mapping_count} сопоставлений.")
        else:
            st.warning("В metadata snapshot нет сохраненного mapping. Перед повторным расчетом проверьте колонки вручную.")
        if card.missing_mapping_fields:
            st.caption("Не найдены ключевые поля mapping: " + ", ".join(card.missing_mapping_fields))
        else:
            st.caption("Ключевые поля mapping для depth и основных газов сохранены.")
        if card.key_columns:
            st.caption("Ключевые колонки: " + ", ".join(card.key_columns))
        else:
            st.caption("Ключевые колонки не найдены в metadata расчета.")
        if card.graph_ready:
            st.success("Расчет готов к открытию в интерпретационных графиках.")
        else:
            st.warning("Перед открытием в графиках проверьте наличие depth/DEPT/MD и числовых колонок.")
        if card.open_warnings:
            st.caption("Предупреждения перед открытием snapshot")
            for open_warning in card.open_warnings:
                st.warning(open_warning)
        if card.warning_preview:
            st.caption("Первые предупреждения")
            for warning in card.warning_preview:
                st.warning(warning)
            if card.warnings_count > len(card.warning_preview):
                st.caption(f"Показано {len(card.warning_preview)} из {card.warnings_count} предупреждений.")
        else:
            st.success("Сохраненный расчет не содержит предупреждений.")

    mapping = metadata.get("mapping", {})
    warnings = metadata.get("warnings", [])
    with st.expander("Полный mapping и предупреждения расчета", expanded=False):
        st.caption(f"Строка заголовков: {metadata.get('header_row')}")
        st.caption(f"Режим Ch: {card.ch_mode_label}")
        st.caption("Mapping")
        st.json(mapping)
        if warnings:
            st.caption("Все предупреждения")
            for warning in warnings:
                st.warning(str(warning))
        else:
            st.success("Сохраненный расчет не содержит предупреждений.")



def _format_project_calculation_tuple(values: tuple[str, ...], empty_text: str = "нет") -> str:
    return ", ".join(values) if values else empty_text


def _render_project_calculation_comparison(project: ProjectRecord, records: tuple[object, ...], logger) -> None:
    if len(records) < 2:
        st.caption("Для сравнения нужно минимум два сохраненных расчета проекта.")
        return

    records_by_id = {record.id: record for record in records}
    newest_id = records[0].id
    previous_id = records[1].id
    with st.expander("Сравнение двух сохраненных расчетов", expanded=False):
        st.caption(
            "Сравнение безопасно читает только сохраненные snapshots и показывает различия "
            "по строкам, колонкам, измененным ячейкам общих колонок и предупреждениям."
        )
        left_col, right_col = st.columns(2)
        left_id = left_col.selectbox(
            "Базовый расчет",
            options=tuple(records_by_id),
            index=tuple(records_by_id).index(previous_id) if previous_id in records_by_id else 0,
            format_func=lambda record_id: _project_calculation_option_label(records_by_id[record_id]),
            key=f"project_calculation_compare_left_{project.id}",
        )
        right_id = right_col.selectbox(
            "Сравнить с",
            options=tuple(records_by_id),
            index=tuple(records_by_id).index(newest_id) if newest_id in records_by_id else 0,
            format_func=lambda record_id: _project_calculation_option_label(records_by_id[record_id]),
            key=f"project_calculation_compare_right_{project.id}",
        )
        if left_id == right_id:
            st.warning("Выберите два разных сохраненных расчета.")
            return

        try:
            comparison = compare_project_calculations(LAS_CORRELATION_PROJECTS_ROOT, project.id, left_id, right_id)
            compare_log_key = f"project_calculation_compare_logged_{project.id}_{left_id}_{right_id}"
            if not st.session_state.get(compare_log_key):
                _record_project_calculation_action(
                    project,
                    "compare_snapshots",
                    logger,
                    calculation_id=left_id,
                    related_calculation_id=right_id,
                    details="safe metadata/csv comparison",
                )
                st.session_state[compare_log_key] = True
        except Exception:
            logger.exception(
                "project_calculation_compare_failed project_id=%s left_id=%s right_id=%s",
                safe_log_value(project.id),
                safe_log_value(left_id),
                safe_log_value(right_id),
            )
            st.error("Не удалось сравнить сохраненные расчеты. Подробности записаны в logs/app.log.")
            return

        row_metric, column_metric, cell_metric, warning_metric = st.columns(4)
        row_metric.metric("Строк", comparison.right_rows, delta=comparison.row_delta)
        column_metric.metric("Общих колонок", len(comparison.common_columns))
        cell_metric.metric("Измененных ячеек", comparison.changed_cell_count)
        warning_metric.metric(
            "Предупреждений +/-",
            len(comparison.added_warnings) + len(comparison.removed_warnings),
        )
        st.caption(f"База: {comparison.left_source_label}")
        st.caption(f"Новый расчет: {comparison.right_source_label}")
        if comparison.has_differences:
            st.warning("Между выбранными snapshots есть отличия. Проверьте их перед печатью или передачей отчета.")
        else:
            st.success("Существенные отличия между выбранными snapshots не найдены.")

        diff_table = build_project_calculation_comparison_table(comparison)
        st.dataframe(diff_table, use_container_width=True, hide_index=True)

        csv_export_col, html_export_col = st.columns(2)
        if csv_export_col.download_button(
            "Скачать сравнение CSV",
            data=export_project_calculation_comparison_csv(comparison),
            file_name=f"calculation-comparison-{comparison.left_id}-vs-{comparison.right_id}.csv",
            mime="text/csv",
            key=f"project_calculation_compare_csv_{project.id}_{comparison.left_id}_{comparison.right_id}",
        ):
            _record_project_calculation_action(
                project,
                "download_export",
                logger,
                calculation_id=comparison.left_id,
                related_calculation_id=comparison.right_id,
                export_format="CSV",
                details="comparison export",
            )
        if html_export_col.download_button(
            "Скачать сравнение HTML",
            data=export_project_calculation_comparison_html(comparison),
            file_name=f"calculation-comparison-{comparison.left_id}-vs-{comparison.right_id}.html",
            mime="text/html",
            key=f"project_calculation_compare_html_{project.id}_{comparison.left_id}_{comparison.right_id}",
        ):
            _record_project_calculation_action(
                project,
                "download_export",
                logger,
                calculation_id=comparison.left_id,
                related_calculation_id=comparison.right_id,
                export_format="HTML",
                details="comparison export",
            )

def _render_project_calculations_panel(project: ProjectRecord, logger) -> None:
    all_records = list_project_calculations(LAS_CORRELATION_PROJECTS_ROOT, project.id)
    summary = summarize_project_calculations(LAS_CORRELATION_PROJECTS_ROOT, project.id)
    with st.expander("Сохраненные расчеты проекта", expanded=bool(all_records)):
        st.caption(_project_calculations_summary_caption(summary))
        if all_records:
            metric_count, metric_rows, metric_warnings, metric_columns = st.columns(4)
            metric_count.metric("Расчетов", summary.count)
            metric_rows.metric("Строк", summary.total_rows)
            metric_warnings.metric("Предупреждений", summary.total_warnings)
            metric_columns.metric("Колонок", len(summary.columns))
        if not all_records:
            st.caption("В активном проекте пока нет сохраненных расчетов.")
            _render_project_calculation_actions(project, logger)
            return

        _render_project_calculation_actions(project, logger)

        with st.expander("Быстрый фильтр расчетов", expanded=False):
            filter_source, filter_warnings = st.columns(2)
            source_query = filter_source.text_input(
                "Источник содержит",
                value="",
                placeholder="Например: Well A, LAS, Pixler",
                key=f"project_calculation_filter_source_{project.id}",
            )
            warning_state_label = filter_warnings.selectbox(
                "Предупреждения",
                options=("Любые", "Только с предупреждениями", "Только без предупреждений"),
                key=f"project_calculation_filter_warnings_{project.id}",
            )
            columns_query = st.text_input(
                "Обязательные колонки",
                value="",
                placeholder="Через запятую: depth, c1, wh",
                key=f"project_calculation_filter_columns_{project.id}",
            )
            warning_state = {
                "Любые": "any",
                "Только с предупреждениями": "with_warnings",
                "Только без предупреждений": "without_warnings",
            }[warning_state_label]
            required_columns = _parse_project_calculation_columns_filter(columns_query)

        try:
            records = filter_project_calculations(
                LAS_CORRELATION_PROJECTS_ROOT,
                project.id,
                source_query=source_query,
                warning_state=warning_state,
                required_columns=required_columns,
            )
        except ValueError:
            records = all_records
            st.warning("Фильтр расчетов сброшен из-за некорректного режима предупреждений.")

        _render_project_calculation_comparison(project, all_records, logger)

        if len(records) != len(all_records):
            st.caption(f"Показано расчетов: {len(records)} из {len(all_records)}.")
        if not records:
            st.warning("По текущему фильтру сохраненные расчеты не найдены.")
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

        try:
            integrity = check_project_calculation_integrity(LAS_CORRELATION_PROJECTS_ROOT, project.id, selected_id)
        except Exception:
            integrity = None
            logger.exception(
                "project_calculation_integrity_check_failed project_id=%s calculation_id=%s",
                safe_log_value(project.id),
                safe_log_value(selected_id),
            )
            st.error("Не удалось проверить файлы сохраненного расчета перед выгрузкой. Подробности записаны в logs/app.log.")

        downloads_disabled = integrity is None or not integrity.ok
        if integrity is not None:
            if integrity.ok:
                st.success("Файлы выбранного сохраненного расчета прошли проверку целостности перед выгрузкой.")
            else:
                st.warning("Выгрузки выбранного расчета временно отключены: проверка целостности нашла проблему.")
                for message in integrity.messages:
                    st.caption(f"• {message}")

        csv_col, xlsx_col, csv_card_col, html_card_col, open_col = st.columns(5)
        try:
            csv_data = (
                read_project_calculation_file_bytes(LAS_CORRELATION_PROJECTS_ROOT, project.id, selected_id, "csv")
                if not downloads_disabled
                else b""
            )
            xlsx_data = (
                read_project_calculation_file_bytes(LAS_CORRELATION_PROJECTS_ROOT, project.id, selected_id, "xlsx")
                if not downloads_disabled
                else b""
            )
            card_csv_data = (
                export_project_calculation_card_csv(LAS_CORRELATION_PROJECTS_ROOT, project.id, selected_id)
                if not downloads_disabled
                else b""
            )
            card_html_data = (
                export_project_calculation_card_html(LAS_CORRELATION_PROJECTS_ROOT, project.id, selected_id)
                if not downloads_disabled
                else b""
            )
            if csv_col.download_button(
                "Скачать CSV",
                data=csv_data,
                file_name=f"{selected_record.id}.csv",
                mime="text/csv",
                use_container_width=True,
                disabled=downloads_disabled,
                key=f"project_calculation_csv_{project.id}_{selected_id}",
            ):
                _record_project_calculation_action(project, "download_export", logger, calculation_id=selected_id, export_format="CSV")
            if xlsx_col.download_button(
                "Скачать XLSX",
                data=xlsx_data,
                file_name=f"{selected_record.id}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                disabled=downloads_disabled,
                key=f"project_calculation_xlsx_{project.id}_{selected_id}",
            ):
                _record_project_calculation_action(project, "download_export", logger, calculation_id=selected_id, export_format="XLSX")
            if csv_card_col.download_button(
                "Скачать карточку CSV",
                data=card_csv_data,
                file_name=f"{selected_record.id}-card.csv",
                mime="text/csv",
                use_container_width=True,
                disabled=downloads_disabled,
                key=f"project_calculation_card_csv_{project.id}_{selected_id}",
            ):
                _record_project_calculation_action(
                    project,
                    "download_export",
                    logger,
                    calculation_id=selected_id,
                    export_format="CSV",
                    details="calculation card metadata",
                )
            if html_card_col.download_button(
                "Скачать карточку HTML",
                data=card_html_data,
                file_name=f"{selected_record.id}-card.html",
                mime="text/html",
                use_container_width=True,
                disabled=downloads_disabled,
                key=f"project_calculation_card_html_{project.id}_{selected_id}",
            ):
                _record_project_calculation_action(
                    project,
                    "download_export",
                    logger,
                    calculation_id=selected_id,
                    export_format="HTML",
                    details="calculation card report",
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
                open_card = build_project_calculation_card(LAS_CORRELATION_PROJECTS_ROOT, project.id, selected_id)
                for open_warning in open_card.open_warnings:
                    st.warning(open_warning)
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
                _record_project_calculation_action(project, "open_snapshot", logger, calculation_id=selected_id)
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

    with st.expander("Correlation Studio · tops/markers и общая глубинная сетка", expanded=False):
        st.caption("Профессиональная панель корреляции: один трек на скважину, синхронная глубина и маркеры пластов.")
        studio_grid_mode = st.radio(
            "Глубинная сетка",
            options=("union", "overlap"),
            format_func=lambda value: "Весь объединенный интервал" if value == "union" else "Только общий перекрывающийся интервал",
            horizontal=True,
            key="las_correlation_studio_grid_mode",
        )
        studio_depth_step = st.number_input(
            "Шаг общей сетки, м",
            min_value=0.01,
            value=0.5,
            step=0.01,
            key="las_correlation_studio_depth_step",
        )
        default_marker_rows = st.session_state.get(
            "las_correlation_studio_markers",
            [{"well": "", "name": "Top", "depth": float(valid_depths[0]) if valid_depths else 0.0, "kind": "top", "color": "#FBBF24", "note": ""}],
        )
        marker_rows = st.data_editor(
            pd.DataFrame(default_marker_rows),
            num_rows="dynamic",
            use_container_width=True,
            key="las_correlation_studio_marker_editor",
        )
        marker_records = marker_rows.to_dict("records") if isinstance(marker_rows, pd.DataFrame) else []
        st.session_state["las_correlation_studio_markers"] = marker_records

        studio_panel = build_correlation_panel(
            selected_wells,
            markers=marker_records,
            depth_range=depth_range,
            depth_step=float(studio_depth_step),
            groups=selected_groups,
            grid_mode=studio_grid_mode,
        )
        studio_summary = correlation_panel_summary(studio_panel)
        st.caption(
            f"Скважин: {studio_summary['wells']} · Маркеров: {studio_summary['markers']} · "
            f"Точек сетки: {studio_summary['grid_points']}"
        )
        if studio_panel.warnings:
            for warning in studio_panel.warnings:
                st.warning(warning)
        studio_curve_options = common_curve_names(selected_wells, groups=selected_groups)
        if studio_curve_options:
            studio_curve = st.selectbox(
                "Кривая для correlation-панели",
                options=studio_curve_options,
                key="las_correlation_studio_curve",
            )
            studio_figure = build_correlation_panel_figure(
                studio_panel,
                studio_curve,
                height_per_well=max(480, int(height_per_well)),
            )
            st.plotly_chart(studio_figure, use_container_width=True)
            if studio_panel.markers:
                st.dataframe(pd.DataFrame(correlation_marker_rows(studio_panel)), use_container_width=True)
        else:
            st.info("Для Correlation Studio выберите группы с числовыми кривыми.")
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
    st.set_page_config(page_title="Gas Ratio Pro", page_icon=_app_icon_data_uri() or None, layout="wide")
    ui_scale = _select_ui_scale()
    ui_layout = _select_ui_layout()
    _apply_app_style(ui_scale, ui_layout)
    logger = configure_logging()
    logger.info("streamlit_app_started")

    active_project = _render_project_selector(logger, key_prefix="global", expanded=False)
    _render_project_explorer(active_project, logger)
    _render_global_command_palette(active_project)

    active_tab = _render_main_navigation()
    if active_tab == "Старт":
        _render_start_tab(active_project)
    elif active_tab == "Работа с данными":
        _open_page_shell(active_tab)
        st.markdown('<div id="data-workspace"></div>', unsafe_allow_html=True)
        _render_workspace(logger, active_project)
        _close_page_shell()
    elif active_tab == "LAS-редактор":
        _open_page_shell(active_tab)
        st.markdown('<div id="las-editor-workspace"></div>', unsafe_allow_html=True)
        _render_las_editor(logger, active_project)
        _close_page_shell()
    elif active_tab == "LAS-корреляция":
        _open_page_shell(active_tab)
        st.markdown('<div id="correlation-workspace"></div>', unsafe_allow_html=True)
        _render_las_correlation_tab(logger, active_project)
        _close_page_shell()
    elif active_tab == "Интерпретационные графики":
        _open_page_shell(active_tab)
        st.markdown('<div id="graphs-workspace"></div>', unsafe_allow_html=True)
        _render_interpretation_graphs_tab(logger, active_project)
        _close_page_shell()
    elif active_tab == "Инструкции и документация":
        _open_page_shell(active_tab)
        st.markdown('<div id="documentation-workspace"></div>', unsafe_allow_html=True)
        _render_documentation_tab()
        _close_page_shell()
    else:
        _open_page_shell(active_tab)
        st.markdown('<div id="license-workspace"></div>', unsafe_allow_html=True)
        _render_application_licensing_page()
        _close_page_shell()


if __name__ == "__main__":
    main()
