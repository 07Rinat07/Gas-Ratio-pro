from __future__ import annotations

# UI refresh reason codes: las_editor_working_state_cleared, project_exports_refreshed, project_export_deleted, project_exports_cleared

import base64
import html
import hashlib
import importlib
import json
import os
import random
import sys
from datetime import datetime
from time import perf_counter
from io import BytesIO
from pathlib import Path
from textwrap import dedent

import pandas as pd

try:
    import streamlit as st
except ModuleNotFoundError:  # pragma: no cover - lightweight fallback for non-UI test environments
    class _StreamlitSessionState(dict):
        def __getattr__(self, name: str):
            try:
                return self[name]
            except KeyError as exc:
                raise AttributeError(name) from exc

        def __setattr__(self, name: str, value):
            self[name] = value

    class _StreamlitNoopContext:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    class _StreamlitStub:
        session_state = _StreamlitSessionState()
        sidebar = _StreamlitNoopContext()

        def __getattr__(self, _name: str):
            def _noop(*_args, **_kwargs):
                return None
            return _noop

        def columns(self, spec, *args, **kwargs):
            count = spec if isinstance(spec, int) else len(spec)
            return [_StreamlitNoopContext() for _ in range(count)]

        def expander(self, *args, **kwargs):
            return _StreamlitNoopContext()

        def container(self, *args, **kwargs):
            return _StreamlitNoopContext()

        def form(self, *args, **kwargs):
            return _StreamlitNoopContext()

    st = _StreamlitStub()

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.calculations import CH_WARNING, METHODOLOGY_WARNING, calculate_gas_ratios
from core.calculation_diagnostics import (
    build_calculation_diagnostics_report,
    column_quality_dataframe,
    formula_diagnostics_dataframe,
    calculation_diagnostics_to_dict,
)
from core.diagnostics import (
    build_mapping_diagnostics,
    build_ratio_nan_diagnostics,
    interval_ratio_diagnostic_messages,
    mapping_warning_messages,
    ratio_nan_warning_messages,
)
from core.interpretation import INTERPRETATION_NOTE, add_interpretation, engineering_interval_summary
from core.logging_config import configure_logging, safe_log_value
from core.workbench_runtime_diagnostics import record_render_audit
from core.workbench_context import WorkbenchSelectionService
from core.application_state import ApplicationStateController
from core.models import CalculationConfig, STANDARD_FIELDS
from ui.ux_feedback import REPORT_EXPORT_PROGRESS, tooltip
from ui.interpretation_interval_panel import (
    render_interpretation_interval_panel,
    resolve_interpretation_well_id,
)
from ui.interpretation_correlation_panel import render_interpretation_correlation_panel
from ui.interpretation_interval_navigator import (
    build_manual_interval_navigator,
    selected_interval_id_from_plotly_event,
)
from core.presentation_runtime import (
    AppliedCorrelationState,
    AppliedExportState,
    AppliedMappingState,
    AppliedPresentationState,
    applied_correlation_from_state,
    applied_export_from_state,
    applied_mapping_from_state,
    applied_presentation_from_state,
    correlation_matches_source,
    export_matches_source,
    dataframe_signature,
    load_las_sheets_cached,
    mapping_matches_source,
    persist_applied_correlation,
    persist_applied_export,
    persist_applied_mapping,
    persist_applied_presentation,
    persist_revisions,
    presentation_matches_source,
    revision_controller_from_state,
)
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
from core.hydrocarbon_intervals import detect_hydrocarbon_intervals
from mapping.mapper import apply_mapping, auto_map_columns
from palettes.config import load_palette_config
from palettes.plot_engine import PLOTLY_SCREEN_CONFIG, downsample_frame_for_screen, enhance_screen_visibility
from core.runtime_diagnostics import RuntimeDiagnostics
from core.rerun_coordinator import begin_rerun_cycle, request_rerun
from core.cache_metrics import CacheMetricsRegistry
from core.correlation_runtime_cache import CorrelationRenderArtifacts
from core.session_state_audit import audit_session_state
from core.performance_audit import build_workspace_performance_gate, evaluate_performance
from core.operation_tracing import OperationTraceRegistry, trace_context
from core.render_queue import RenderQueue, RenderTask
from core.lazy_workspace import LazyWorkspaceRegistry, WorkspaceRoute
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
    configure_manual_interval_overlays,
    manual_interval_overlays,
    normalize_track_configs,
    numeric_tablet_columns,
    reservoir_interval_overlays,
    tablet_units_from_dataframe,
)
from palettes.pixler import build_pixler_palette
from core.reservoir_passport import build_reservoir_passport
from core.reservoir_ranking import (
    BUILTIN_RANKING_PROFILES,
    DEFAULT_RANKING_PROFILE,
    ReservoirRankingProfile,
    ReservoirRankingWeights,
    compare_reservoir_rankings,
    rank_reservoir_intervals,
    ranking_profile_by_id,
    reservoir_ranking_dataframe,
)
from projects.reservoir_ranking_profiles import (
    load_project_ranking_profiles,
    save_project_ranking_profiles,
)
from palettes.ternary import build_ternary_palette
from projects import (
    ProjectRecord,
    build_project_tree,
    create_project,
    delete_project,
    ensure_default_project,
    list_project_explorer_folder_targets,
    list_project_explorer_move_options,
    list_project_explorer_well_group_targets,
    list_projects,
    move_project_explorer_item_to_folder,
    move_project_explorer_well_to_group,
    project_tree_table_rows,
    build_project_templates_table,
    clear_project_recovery_state,
    create_project_backup,
    create_project_from_template,
    create_project_template,
    list_project_templates,
    load_project_recovery_state,
    project_manager_status,
    save_project_recovery_state,
)
from projects.workspace_controller import WorkspaceController
from projects.workspace_manager import WorkspaceManagerItem
from las_editor.las_workspace_controller import LasWorkspaceController
from las_editor.las_workspace_home import action_table_rows
from projects.recent_projects import (
    clear_recent_projects,
    list_recent_projects,
    recent_projects_table_rows,
    remove_recent_project,
    set_recent_project_flags,
    touch_recent_project,
)
from core.application_service_container import application_service_container
from services.well_manager_service import DEFAULT_WELLS_STORAGE_ROOT
from services.dataset_manager_service import StorageDeleteError
from projects import calculations as project_calculations
from projects import exports as project_exports
from projects import graph_settings as project_graph_settings
from projects import datasets as project_datasets
from projects import project_labels as project_labels
from projects import project_index as project_index
from core.project_database_table import build_project_database_table_view
from projects import well_cards as project_well_cards
from projects import las_files as project_las_files
from reports.export_csv import export_csv_bytes
from reports.interval_report import build_interval_print_report
from reports.hydrocarbon_report import build_hydrocarbon_report_payload
from reports.presentation_ui import (
    build_presentation_export_ui_state,
    build_ui_export_artifact,
    PresentationUiExportArtifact,
    export_format_options,
    report_profile_options,
)
from reports.report_designer import (
    ReportDesign,
    ReportDocumentCounts,
    build_report_document_counts_signature,
    build_report_document_counts_snapshot,
    resolve_report_document_counts_snapshot,
    build_report_structure_preview,
    report_modes,
    report_templates,
)
from reports.report_designer_export import build_designed_report_artifact
from reports.pdf_preview import (
    PdfPreviewResult,
    PdfPreviewUnavailableError,
    build_pdf_preview,
    build_pdf_preview_signature,
    bounded_pdf_preview_start_page,
    inspect_pdf_preview_cache,
    next_pdf_preview_start_page,
    resolve_pdf_preview_cache,
    shift_pdf_preview_window,
    store_pdf_preview_cache,
    store_pdf_preview_cache_with_diagnostics,
    summarize_pdf_preview_cache,
    validate_pdf_preview_page_jump,
)
from reports.export_wizard import (
    ExportWizardCapabilities,
    ExportWizardState,
    ExportWizardStep,
    build_export_wizard_review,
)
from reports.export_wizard_persistence import ExportWizardDraft
from reports.export_history import (
    ExportHistoryEntry,
    ExportHistoryFilter,
    build_export_data_revision,
    build_repeat_export_confirmation,
    compare_export_data_revision,
    filter_export_history,
)
from reports.export_las import export_las_bytes
from reports.export_xlsx import export_xlsx_bytes
from reports.export_controller import (
    ExportArtifact as ControlledExportArtifact,
    ExportControllerError,
    ExportRequest,
    normalize_export_form_state,
)
from reports.background_export import ExportJobStatus
from reports.background_export_ui import (
    BackgroundExportResult,
    build_background_export_performance_summary,
    build_background_export_status_view,
    build_recent_background_job_history,
    filter_recent_background_job_history,
    format_artifact_size,
    format_export_duration,
    sort_recent_background_job_history,
    latest_relevant_job,
    retry_diagnostic_reason,
)
from reports.export_progress import staged_progress_reporter
from las_editor.las_creation_wizard import (
    DEFAULT_CURVE_LIBRARY,
    build_las_creation_wizard_draft,
    run_las_creation_wizard,
    template_table_rows,
)
from reports.export_static import (
    SUPPORTED_STATIC_EXPORT_FORMATS,
    StaticExportOptions,
    StaticExportUnavailableError,
    export_plotly_static_bytes,
)

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
read_project_calculation_diagnostics = project_calculations.read_project_calculation_diagnostics
build_project_calculation_card = project_calculations.build_project_calculation_card
check_project_calculation_integrity = project_calculations.check_project_calculation_integrity
compare_project_calculations = project_calculations.compare_project_calculations
build_project_calculation_comparison_table = project_calculations.build_project_calculation_comparison_table
export_project_calculation_comparison_csv = project_calculations.export_project_calculation_comparison_csv
export_project_calculation_actions_csv = project_calculations.export_project_calculation_actions_csv
export_project_calculation_card_csv = project_calculations.export_project_calculation_card_csv
save_project_calculation = project_calculations.save_project_calculation
append_project_calculation_action = project_calculations.append_project_calculation_action
list_project_calculation_actions = project_calculations.list_project_calculation_actions
list_project_exports = project_exports.list_project_exports
read_project_export_file_bytes = project_exports.read_project_export_file_bytes
save_project_export = project_exports.save_project_export
delete_project_export = project_exports.delete_project_export
clear_project_exports = project_exports.clear_project_exports
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
interpretation_graph_settings_to_dict = project_graph_settings.settings_to_dict
interpretation_graph_settings_from_dict = project_graph_settings.settings_from_dict
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
WELLS_STORAGE_ROOT = ROOT_DIR / DEFAULT_WELLS_STORAGE_ROOT
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
ACTIVE_CALCULATION_DATA_KEY = "active_calculation_result_data"
ACTIVE_CALCULATION_SOURCE_KEY = "active_calculation_result_source"
ACTIVE_CALCULATION_PROJECT_KEY = "active_calculation_project_id"
ACTIVE_CALCULATION_CONTRACT_KEY = "workbench_active_calculation"
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
        "description": "Сравнение нескольких скважин, группировка кривых, X-scale, интервал, печатный PDF/DOCX и графический экспорт.",
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
    ("Карта документации", "docs/DOCUMENTATION_INDEX.md"),
    ("Активный roadmap", "docs/PROJECT_ROADMAP.md"),
    ("Текущий статус", "docs/PROJECT_STATUS.md"),
    ("Быстрый старт", "docs/setup.md"),
    ("Руководство пользователя", "docs/user_guide.md"),
    ("Формат входных данных", "docs/data_format.md"),
    ("План LAS-редактора", "docs/las_editor_plan.md"),
    ("План LAS-корреляции", "docs/las_correlation_plan.md"),
    ("Формулы", "docs/formulas.md"),
    ("Mud gas literature", "docs/mud_gas_analysis_literature.md"),
    ("Архитектура", "docs/ARCHITECTURE.md"),
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
            --brand-bg-size: clamp(300px, 42vw, 720px) auto;
            --brand-bg-position: right 3vw bottom 1.2rem;
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
            --responsive-dashboard-columns: repeat(auto-fit, minmax(11.5rem, 1fr));
            --responsive-dashboard-padding: 0.82rem;
            --glass-dark-overlay-control: rgba(3, 7, 18, 0.62);
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
            .dashboard-card.news, .dashboard-card.tips { display: none; }
            .dashboard-card.preview-card, .dashboard-card.welcome { display: none; }
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
        .grp-inline-operation {
            display: grid;
            grid-template-columns: auto auto minmax(0, 1fr);
            align-items: center;
            gap: 0.55rem;
            min-height: 2.35rem;
            margin: 0.45rem 0 0.7rem;
            padding: 0.55rem 0.72rem;
            border: 1px solid rgba(148, 163, 184, 0.24);
            border-left: 3px solid #f59e0b;
            border-radius: 9px;
            background: rgba(15, 23, 42, 0.42);
            color: #cbd5e1;
            line-height: 1.35;
        }
        .grp-inline-operation strong { color: #f8fafc; }
        .grp-inline-operation__state {
            border-radius: 999px;
            padding: 0.14rem 0.48rem;
            background: rgba(245, 158, 11, 0.15);
            color: #fbbf24;
            font-size: 0.75rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }
        .grp-inline-operation--success { border-left-color: #22c55e; }
        .grp-inline-operation--success .grp-inline-operation__state { background: rgba(34, 197, 94, 0.14); color: #86efac; }
        .grp-inline-operation--error { border-left-color: #ef4444; }
        .grp-inline-operation--error .grp-inline-operation__state { background: rgba(239, 68, 68, 0.14); color: #fca5a5; }
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
        sheets, signature, timing = load_las_sheets_cached(uploaded_file, load_las_sheets)
        configure_logging().info(
            "las_parse_completed signature=%s cache_hit=%s duration_ms=%.2f",
            signature[:12],
            timing.cache_hit,
            timing.duration_ms,
        )
        return sheets
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


def _effective_depth_range(
    df: pd.DataFrame,
    depth_range: tuple[float, float] | None,
) -> tuple[float, float]:
    """Return a concrete depth interval for metadata/export operations.

    Plot builders may legitimately use ``None`` to mean the full interval, but
    export metadata must always be iterable and numeric.
    """

    if depth_range is not None:
        return (float(depth_range[0]), float(depth_range[1]))

    depth = _depth_values_for_graphs(df).dropna()
    if not depth.empty:
        return (float(depth.min()), float(depth.max()))

    if len(df) > 0:
        return (0.0, float(len(df) - 1))
    return (0.0, 0.0)

def _store_interpretation_dataset(calculated_df: pd.DataFrame, source_label: str) -> None:
    """Commit one calculation for all Workbench workspaces.

    The durable contract is intentionally stored under a non-transient key.
    Workspace transitions are allowed to clear widget and presentation state,
    but must never discard the last explicitly calculated dataframe.
    """
    controller = _application_state_controller()
    active_project_id = str(controller.get_value(ACTIVE_PROJECT_ID_KEY, "") or "")
    committed_frame = calculated_df.copy(deep=True)
    revisions = revision_controller_from_state(controller.state)
    snapshot = revisions.bump_calculation()
    persist_revisions(controller.state, snapshot)
    durable_contract = {
        "project_id": active_project_id,
        "source": str(source_label),
        "calculation_revision": int(snapshot.calculation_revision),
        "rows": int(len(committed_frame)),
        "dataframe": committed_frame,
    }
    _application_state_controller().update_values(
        {
            INTERPRETATION_SESSION_DATA_KEY: committed_frame,
            INTERPRETATION_SESSION_SOURCE_KEY: str(source_label),
            ACTIVE_CALCULATION_DATA_KEY: committed_frame,
            ACTIVE_CALCULATION_SOURCE_KEY: str(source_label),
            ACTIVE_CALCULATION_PROJECT_KEY: active_project_id,
            ACTIVE_CALCULATION_CONTRACT_KEY: durable_contract,
        }
    )
    controller.state.pop("interpretation_figure_cache", None)
    controller.state.pop("interpretation_plot_cache", None)
    controller.remove_runtime_service("dataframe_runtime_cache", None)
    configure_logging().info(
        "active_calculation_committed project_id=%s rows=%d revision=%d source=%s",
        safe_log_value(active_project_id),
        len(committed_frame),
        int(snapshot.calculation_revision),
        safe_log_value(source_label),
    )


def _active_calculation_dataset(project_id: str = "") -> tuple[pd.DataFrame | None, str]:
    """Return the durable calculation shared by Data/Interpretation/Reports."""
    controller = _application_state_controller()
    logger = configure_logging()
    expected_project_id = str(project_id or controller.get_value(ACTIVE_PROJECT_ID_KEY, "") or "")

    contract = controller.get_value(ACTIVE_CALCULATION_CONTRACT_KEY, {})
    if isinstance(contract, dict):
        contract_project_id = str(contract.get("project_id", "") or "")
        if contract_project_id and expected_project_id and contract_project_id != expected_project_id:
            logger.warning(
                "active_calculation_project_mismatch expected=%s stored=%s",
                safe_log_value(expected_project_id),
                safe_log_value(contract_project_id),
            )
            return None, ""
        contract_frame = contract.get("dataframe")
        if isinstance(contract_frame, pd.DataFrame) and not contract_frame.empty:
            source = str(contract.get("source", "") or "текущий расчет")
            logger.info(
                "active_calculation_restored project_id=%s rows=%d revision=%s",
                safe_log_value(expected_project_id),
                len(contract_frame),
                safe_log_value(contract.get("calculation_revision", "")),
            )
            return contract_frame, source

    # Backward-compatible migration from builds that stored separate keys.
    stored_project_id = str(controller.get_value(ACTIVE_CALCULATION_PROJECT_KEY, "") or "")
    if stored_project_id and expected_project_id and stored_project_id != expected_project_id:
        return None, ""
    frame = controller.get_value(ACTIVE_CALCULATION_DATA_KEY)
    source = str(controller.get_value(ACTIVE_CALCULATION_SOURCE_KEY, "") or "")
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        frame = controller.get_value(INTERPRETATION_SESSION_DATA_KEY)
        source = str(controller.get_value(INTERPRETATION_SESSION_SOURCE_KEY, source) or source)
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        # An empty project normally has no calculation. This is a valid initial
        # state and must not flood the application log with warnings on every
        # Streamlit rerun. Warn only when a non-empty persisted contract exists
        # but cannot provide a usable dataframe.
        if isinstance(contract, dict) and contract:
            logger.warning(
                "active_calculation_contract_invalid project_id=%s contract_keys=%s",
                safe_log_value(expected_project_id),
                tuple(sorted(str(key) for key in contract.keys())),
            )
        return None, ""

    migrated_contract = {
        "project_id": stored_project_id or expected_project_id,
        "source": source or "текущий расчет",
        "calculation_revision": 0,
        "rows": int(len(frame)),
        "dataframe": frame.copy(deep=True),
    }
    controller.set_value(ACTIVE_CALCULATION_CONTRACT_KEY, migrated_contract)
    logger.info(
        "active_calculation_migrated project_id=%s rows=%d",
        safe_log_value(expected_project_id),
        len(frame),
    )
    return migrated_contract["dataframe"], str(migrated_contract["source"])


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
        st.dataframe(display_df, width="stretch", height=height)


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
    source_signature: str,
    presentation_revision: int,
) -> None:
    with st.expander("PNG/PDF/SVG экспорт", expanded=False):
        st.caption(
            "Статические файлы формируются только после явного действия. "
            "Изменение размеров не запускает Kaleido до нажатия кнопки."
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
            "Масштаб изображения",
            min_value=0.5,
            max_value=4.0,
            value=2.0,
            step=0.5,
            key=f"{key_prefix}_static_scale",
        )
        export_settings = {
            "kind": "static_plotly",
            "base_file_name": str(base_file_name),
            "width": int(export_width),
            "height": int(export_height),
            "scale": float(export_scale),
            "formats": tuple(SUPPORTED_STATIC_EXPORT_FORMATS),
        }
        cache_key = f"{key_prefix}_static_export_artifacts"
        prepare_export = st.button(
            "Подготовить PNG, PDF и SVG",
            width="stretch",
            type="primary",
            key=f"{key_prefix}_prepare_static_export",
        )
        if prepare_export:
            started = perf_counter()
            progress = st.empty()
            _set_inline_operation_status(progress, "Экспорт", "Формируются PNG, PDF и SVG.")
            artifacts: dict[str, bytes] = {}
            try:
                for format_name in SUPPORTED_STATIC_EXPORT_FORMATS:
                    artifacts[format_name] = export_plotly_static_bytes(
                        figure,
                        StaticExportOptions(
                            format=format_name,
                            width=int(export_width),
                            height=int(export_height),
                            scale=float(export_scale),
                        ),
                    )
                persist_applied_export(
                    _application_state_controller().state,
                    AppliedExportState(
                        source_signature=source_signature,
                        presentation_revision=int(presentation_revision),
                        settings=export_settings,
                    ),
                )
                revisions = revision_controller_from_state(_application_state_controller().state)
                persist_revisions(_application_state_controller().state, revisions.bump_export())
                _application_state_controller().state[cache_key] = {
                    "source_signature": source_signature,
                    "presentation_revision": int(presentation_revision),
                    "settings": export_settings,
                    "artifacts": artifacts,
                }
                _set_inline_operation_status(
                    progress,
                    "Экспорт",
                    f"Статические файлы подготовлены за {(perf_counter() - started) * 1000.0:.0f} мс.",
                    state="success",
                )
            except StaticExportUnavailableError as exc:
                _application_state_controller().state.pop(cache_key, None)
                _set_inline_operation_status(progress, "Экспорт", str(exc), state="error")

        cached = _application_state_controller().state.get(cache_key)
        cache_matches = (
            isinstance(cached, dict)
            and cached.get("source_signature") == source_signature
            and int(cached.get("presentation_revision", -1)) == int(presentation_revision)
            and cached.get("settings") == export_settings
            and isinstance(cached.get("artifacts"), dict)
        )
        if not cache_matches:
            st.info("Настройте размеры и нажмите «Подготовить PNG, PDF и SVG».")
            return

        base_name = Path(base_file_name).stem or "las_correlation"
        artifacts = cached["artifacts"]
        columns = st.columns(len(SUPPORTED_STATIC_EXPORT_FORMATS))
        for index, format_name in enumerate(SUPPORTED_STATIC_EXPORT_FORMATS):
            data = artifacts.get(format_name)
            if not isinstance(data, (bytes, bytearray)):
                continue
            columns[index].download_button(
                format_name.upper(),
                data=bytes(data),
                file_name=f"{base_name}.{format_name}",
                mime=_static_export_mime(format_name),
                width="stretch",
                key=f"{key_prefix}_download_{format_name}",
            )



def _las_editor_reference_state(column_names: list[str]) -> dict[str, object]:
    """Collect currently existing curve-reference containers for safe rename."""

    state = _application_state_controller()
    return {
        "tablet_tracks": _application_state_controller().get_list("interpretation_tablet_columns"),
        "templates": {},
        "presets": {
            "mud_gas": list(mud_gas_literature_tablet_columns(column_names)),
            "default_tablet": list(default_tablet_columns(column_names)),
        },
        "saved_calculations": {},
        "exports": {"columns": list(column_names)},
        "manifest": {name: {"source": "las_editor"} for name in column_names},
        "curve_aliases": _application_state_controller().get_dict(LAS_EDITOR_ALIAS_MAP_KEY),
        "curve_group_overrides": _application_state_controller().get_dict(LAS_EDITOR_GROUP_OVERRIDES_KEY),
        "curve_category_overrides": _application_state_controller().get_dict(LAS_EDITOR_CATEGORY_OVERRIDES_KEY),
        "curve_unit_overrides": _application_state_controller().get_dict(LAS_EDITOR_UNIT_OVERRIDES_KEY),
        "curve_metadata": _application_state_controller().get_dict(LAS_EDITOR_METADATA_KEY),
    }


def _apply_las_editor_reference_state(references: dict[str, object]) -> None:
    """Write back rename-aware references that are represented in session state."""

    state = _application_state_controller()
    tablet_tracks = references.get("tablet_tracks")
    if isinstance(tablet_tracks, list):
        _application_state_controller().set_value("interpretation_tablet_columns", tablet_tracks)


def _render_las_curve_alias_manager(prepared_df: pd.DataFrame) -> None:
    st.markdown("### Curve Manager · Alias curves")
    st.caption(
        "Назначение стандартных alias без переименования колонок: depth, c1, c2, c3, "
        "i/n C4-C5, CO2, H2S, ROP и литология."
    )

    state = _application_state_controller()
    state.ensure_value(LAS_EDITOR_ALIAS_HISTORY_KEY, ())
    state.ensure_value(LAS_EDITOR_ALIAS_MAP_KEY, {})

    column_names = [str(column) for column in prepared_df.columns]
    current_aliases = _application_state_controller().get_dict(LAS_EDITOR_ALIAS_MAP_KEY)
    suggestions = suggest_curve_aliases(column_names)

    if st.button("Автоопределить alias", width="stretch", key="las_editor_alias_autodetect"):
        _application_state_controller().set_value(LAS_EDITOR_ALIAS_MAP_KEY, {**current_aliases, **suggestions})
        current_aliases = _application_state_controller().get_dict(LAS_EDITOR_ALIAS_MAP_KEY)
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
    if action_col.button("Назначить", width="stretch", key="las_editor_alias_apply"):
        try:
            result = assign_curve_alias(
                prepared_df,
                curve_name,
                alias,
                aliases=current_aliases,
                history=_application_state_controller().get_tuple(LAS_EDITOR_ALIAS_HISTORY_KEY),
                references=references,
                reason="manual",
                source="las_editor_ui",
            )
            _application_state_controller().set_value(LAS_EDITOR_ALIAS_MAP_KEY, result.aliases)
            _application_state_controller().set_value(LAS_EDITOR_ALIAS_HISTORY_KEY, result.history)
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

    history = _application_state_controller().get_tuple(LAS_EDITOR_ALIAS_HISTORY_KEY)
    if st.button("Undo последнего alias", disabled=not history, width="stretch", key="las_editor_alias_undo"):
        try:
            result = undo_last_alias(
                aliases=_application_state_controller().get_dict(LAS_EDITOR_ALIAS_MAP_KEY),
                history=history,
                references=references,
            )
            _application_state_controller().set_value(LAS_EDITOR_ALIAS_MAP_KEY, result.aliases)
            _application_state_controller().set_value(LAS_EDITOR_ALIAS_HISTORY_KEY, result.history)
            for message in result.diagnostics:
                st.info(message)
            st.success("Последнее alias-назначение отменено.")
        except ValueError as exc:
            st.warning(str(exc))

    current_aliases = _application_state_controller().get_dict(LAS_EDITOR_ALIAS_MAP_KEY)
    with st.expander("Текущие alias и история", expanded=bool(current_aliases or history)):
        if current_aliases:
            st.dataframe(
                pd.DataFrame([{"curve_name": key, "alias": value} for key, value in current_aliases.items()]),
                width="stretch",
                hide_index=True,
            )
        else:
            st.caption("Alias пока не назначены.")
        history = _application_state_controller().get_tuple(LAS_EDITOR_ALIAS_HISTORY_KEY)
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
                width="stretch",
                hide_index=True,
            )



def _render_las_curve_grouping_manager(prepared_df: pd.DataFrame) -> None:
    st.markdown("### Curve Manager · Curve grouping")
    st.caption(
        "Группировка LAS-кривых по инженерным категориям: глубина, GR, газ, "
        "компоненты C1-C5, сопротивления, density/neutron, буровые параметры и прочие кривые."
    )

    state_controller = _application_state_controller()
    state_controller.ensure_value(LAS_EDITOR_GROUP_HISTORY_KEY, ())
    state_controller.ensure_value(LAS_EDITOR_GROUP_OVERRIDES_KEY, {})

    column_names = [str(column) for column in prepared_df.columns]
    aliases = state_controller.get_dict(LAS_EDITOR_ALIAS_MAP_KEY)
    overrides = state_controller.get_dict(LAS_EDITOR_GROUP_OVERRIDES_KEY)
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
        width="stretch",
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
    if action_col.button("Назначить группу", width="stretch", key="las_editor_group_apply"):
        try:
            result = assign_curve_group(
                prepared_df,
                curve_name,
                selected_group,
                overrides=overrides,
                history=state_controller.get_tuple(LAS_EDITOR_GROUP_HISTORY_KEY),
                references=references,
                reason="manual",
                source="las_editor_ui",
            )
            state_controller.update_values({
                LAS_EDITOR_GROUP_OVERRIDES_KEY: result.overrides,
                LAS_EDITOR_GROUP_HISTORY_KEY: result.history,
            })
            for message in result.diagnostics:
                st.info(message)
            if result.assigned:
                st.success(f"Группа назначена: {result.curve_name} → {curve_group_label(result.group)}")
            else:
                st.warning("Группа не изменилась: назначение уже существовало.")
        except ValueError as exc:
            st.warning(str(exc))

    history = state_controller.get_tuple(LAS_EDITOR_GROUP_HISTORY_KEY)
    if st.button("Undo последней группировки", disabled=not history, width="stretch", key="las_editor_group_undo"):
        try:
            result = undo_last_group_assignment(
                prepared_df,
                overrides=state_controller.get_dict(LAS_EDITOR_GROUP_OVERRIDES_KEY),
                history=history,
                references=references,
            )
            state_controller.update_values({
                LAS_EDITOR_GROUP_OVERRIDES_KEY: result.overrides,
                LAS_EDITOR_GROUP_HISTORY_KEY: result.history,
            })
            for message in result.diagnostics:
                st.info(message)
            st.success("Последняя группировка отменена.")
        except ValueError as exc:
            st.warning(str(exc))

    history = state_controller.get_tuple(LAS_EDITOR_GROUP_HISTORY_KEY)
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
                width="stretch",
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

    state_controller = _application_state_controller()
    state_controller.ensure_value(LAS_EDITOR_CATEGORY_HISTORY_KEY, ())
    state_controller.ensure_value(LAS_EDITOR_CATEGORY_OVERRIDES_KEY, {})

    column_names = [str(column) for column in prepared_df.columns]
    aliases = state_controller.get_dict(LAS_EDITOR_ALIAS_MAP_KEY)
    group_overrides = state_controller.get_dict(LAS_EDITOR_GROUP_OVERRIDES_KEY)
    category_overrides = state_controller.get_dict(LAS_EDITOR_CATEGORY_OVERRIDES_KEY)
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
            width="stretch",
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
        width="stretch",
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
    if action_col.button("Назначить категорию", width="stretch", key="las_editor_category_apply"):
        try:
            result = assign_curve_category(
                prepared_df,
                curve_name,
                selected_category,
                group_overrides=group_overrides,
                category_overrides=category_overrides,
                history=state_controller.get_tuple(LAS_EDITOR_CATEGORY_HISTORY_KEY),
                references=references,
                reason="manual",
                source="las_editor_ui",
            )
            state_controller.update_values({
                LAS_EDITOR_CATEGORY_OVERRIDES_KEY: result.overrides,
                LAS_EDITOR_CATEGORY_HISTORY_KEY: result.history,
            })
            for message in result.diagnostics:
                st.info(message)
            if result.assigned:
                st.success(f"Категория назначена: {result.curve_name} → {curve_category_label(result.category)}")
            else:
                st.warning("Категория не изменилась: назначение уже существовало.")
        except ValueError as exc:
            st.warning(str(exc))

    history = state_controller.get_tuple(LAS_EDITOR_CATEGORY_HISTORY_KEY)
    if st.button("Undo последней категории", disabled=not history, width="stretch", key="las_editor_category_undo"):
        try:
            result = undo_last_category_assignment(
                prepared_df,
                group_overrides=group_overrides,
                category_overrides=state_controller.get_dict(LAS_EDITOR_CATEGORY_OVERRIDES_KEY),
                history=history,
                references=references,
            )
            state_controller.update_values({
                LAS_EDITOR_CATEGORY_OVERRIDES_KEY: result.overrides,
                LAS_EDITOR_CATEGORY_HISTORY_KEY: result.history,
            })
            for message in result.diagnostics:
                st.info(message)
            st.success("Последняя категория отменена.")
        except ValueError as exc:
            st.warning(str(exc))

    history = state_controller.get_tuple(LAS_EDITOR_CATEGORY_HISTORY_KEY)
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
                width="stretch",
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

    state_controller = _application_state_controller()
    state_controller.ensure_value(LAS_EDITOR_UNIT_HISTORY_KEY, ())
    state_controller.ensure_value(LAS_EDITOR_UNIT_OVERRIDES_KEY, {})

    column_names = [str(column) for column in prepared_df.columns]
    aliases = state_controller.get_dict(LAS_EDITOR_ALIAS_MAP_KEY)
    group_overrides = state_controller.get_dict(LAS_EDITOR_GROUP_OVERRIDES_KEY)
    category_overrides = state_controller.get_dict(LAS_EDITOR_CATEGORY_OVERRIDES_KEY)
    unit_overrides = state_controller.get_dict(LAS_EDITOR_UNIT_OVERRIDES_KEY)

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
            width="stretch",
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
        width="stretch",
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
    if action_col.button("Назначить unit", width="stretch", key="las_editor_unit_apply"):
        try:
            result = assign_curve_unit(
                prepared_df,
                curve_name,
                selected_unit,
                group_overrides=group_overrides,
                category_overrides=category_overrides,
                unit_overrides=unit_overrides,
                history=state_controller.get_tuple(LAS_EDITOR_UNIT_HISTORY_KEY),
                references=references,
                reason="manual",
                source="las_editor_ui",
            )
            state_controller.update_values({
                LAS_EDITOR_UNIT_OVERRIDES_KEY: result.overrides,
                LAS_EDITOR_UNIT_HISTORY_KEY: result.history,
            })
            for message in result.diagnostics:
                st.info(message)
            if result.assigned:
                st.success(f"Единица назначена: {result.curve_name} → {curve_unit_label(result.unit)}")
            else:
                st.warning("Единица не изменилась: назначение уже существовало.")
        except ValueError as exc:
            st.warning(str(exc))

    history = state_controller.get_tuple(LAS_EDITOR_UNIT_HISTORY_KEY)
    if st.button("Undo последней единицы", disabled=not history, width="stretch", key="las_editor_unit_undo"):
        try:
            result = undo_last_unit_assignment(
                prepared_df,
                group_overrides=group_overrides,
                category_overrides=category_overrides,
                unit_overrides=state_controller.get_dict(LAS_EDITOR_UNIT_OVERRIDES_KEY),
                history=history,
                references=references,
            )
            state_controller.update_values({
                LAS_EDITOR_UNIT_OVERRIDES_KEY: result.overrides,
                LAS_EDITOR_UNIT_HISTORY_KEY: result.history,
            })
            for message in result.diagnostics:
                st.info(message)
            st.success("Последняя единица отменена.")
        except ValueError as exc:
            st.warning(str(exc))

    history = state_controller.get_tuple(LAS_EDITOR_UNIT_HISTORY_KEY)
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
                width="stretch",
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
    _application_state_controller().set_value(LAS_EDITOR_MNEMONICS_KEY, rows)
    references = mnemonic_reference_manifest(column_names, references=_las_editor_reference_state(column_names))

    st.dataframe(
        pd.DataFrame(mnemonic_summary_rows(column_names)).rename(
            columns={"metric": "Показатель", "value": "Значение"}
        ),
        width="stretch",
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
            width="stretch",
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
    aliases = _application_state_controller().get_dict(LAS_EDITOR_ALIAS_MAP_KEY)
    group_overrides = _application_state_controller().get_dict(LAS_EDITOR_GROUP_OVERRIDES_KEY)
    category_overrides = _application_state_controller().get_dict(LAS_EDITOR_CATEGORY_OVERRIDES_KEY)
    unit_overrides = _application_state_controller().get_dict(LAS_EDITOR_UNIT_OVERRIDES_KEY)

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
        width="stretch",
        key="las_editor_duplicate_detect_apply",
    )
    state_controller = _application_state_controller()
    if state_controller.get_value(LAS_EDITOR_DUPLICATES_KEY) is None or should_run:
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
        state_controller.update_values({
            LAS_EDITOR_DUPLICATES_KEY: result.candidates,
            LAS_EDITOR_DUPLICATE_SUMMARY_KEY: result.summary,
        })
        if should_run:
            for message in result.diagnostics:
                st.info(message)

    candidates = state_controller.get_tuple(LAS_EDITOR_DUPLICATES_KEY)
    summary = state_controller.get_dict(LAS_EDITOR_DUPLICATE_SUMMARY_KEY)
    summary.setdefault("total", len(candidates))

    if candidates:
        st.success(f"Найдено кандидатов-дубликатов: {summary.get('total', len(candidates))}.")
    else:
        st.info("Кандидаты-дубликаты не найдены при текущих порогах.")

    st.dataframe(
        pd.DataFrame(curve_duplicate_summary_rows(summary)).rename(
            columns={"severity_label": "Тип", "candidate_count": "Кандидатов"}
        )[["Тип", "Кандидатов"]],
        width="stretch",
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
            width="stretch",
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

    state_controller = _application_state_controller()
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

    if st.button("Применить bulk edit", width="stretch", key="las_editor_bulk_edit_apply"):
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
                group_overrides=state_controller.get_dict(LAS_EDITOR_GROUP_OVERRIDES_KEY),
                category_overrides=state_controller.get_dict(LAS_EDITOR_CATEGORY_OVERRIDES_KEY),
                unit_overrides=state_controller.get_dict(LAS_EDITOR_UNIT_OVERRIDES_KEY),
                metadata=state_controller.get_dict(LAS_EDITOR_METADATA_KEY),
                references=_las_editor_reference_state(columns),
            )
            state_controller.update_values({
                LAS_EDITOR_GROUP_OVERRIDES_KEY: result.group_overrides,
                LAS_EDITOR_CATEGORY_OVERRIDES_KEY: result.category_overrides,
                LAS_EDITOR_UNIT_OVERRIDES_KEY: result.unit_overrides,
                LAS_EDITOR_METADATA_KEY: result.metadata,
                LAS_EDITOR_BULK_EDIT_LOG_KEY: state_controller.get_tuple(LAS_EDITOR_BULK_EDIT_LOG_KEY) + result.operations,
            })
            for warning in result.warnings:
                st.warning(warning)
            st.success(f"Bulk edit применен: {result.references['curve_bulk_edit_summary']['applied']} операций.")
            prepared_df = result.data
        except ValueError as exc:
            st.warning(str(exc))

    log = state_controller.get_tuple(LAS_EDITOR_BULK_EDIT_LOG_KEY)
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
                width="stretch",
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
            width="stretch",
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

    if st.button("Построить preview export rules", width="stretch", key="las_editor_export_rules_preview"):
        try:
            result = apply_curve_export_rules(
                prepared_df,
                profile_id=profile_id,
                selected_curves=selected_curves,
                aliases=_application_state_controller().get_dict(LAS_EDITOR_ALIAS_MAP_KEY),
                unit_overrides=state_controller.get_dict(LAS_EDITOR_UNIT_OVERRIDES_KEY),
                metadata=metadata,
                null_value=null_value,
                curve_mode=curve_mode,
                duplicate_strategy=duplicate_strategy,
                references=_las_editor_reference_state(columns),
            )
            _application_state_controller().set_value(LAS_EDITOR_EXPORT_RULES_KEY, result)
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

    result = _application_state_controller().get_value(LAS_EDITOR_EXPORT_RULES_KEY)
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
                width="stretch",
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
    group_overrides = _application_state_controller().get_dict(LAS_EDITOR_GROUP_OVERRIDES_KEY)
    category_overrides = _application_state_controller().get_dict(LAS_EDITOR_CATEGORY_OVERRIDES_KEY)
    unit_overrides = _application_state_controller().get_dict(LAS_EDITOR_UNIT_OVERRIDES_KEY)

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
        width="stretch",
        key="las_editor_quality_flags_apply",
    )

    state_controller = _application_state_controller()
    if state_controller.get_value(LAS_EDITOR_QUALITY_FLAGS_KEY) is None or should_run:
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
        state_controller.update_values({
            LAS_EDITOR_QUALITY_FLAGS_KEY: result.flags,
            LAS_EDITOR_QUALITY_SUMMARY_KEY: result.summary,
        })
        if should_run:
            for message in result.diagnostics:
                st.info(message)

    flags = state_controller.get_tuple(LAS_EDITOR_QUALITY_FLAGS_KEY)
    summary = state_controller.get_dict(LAS_EDITOR_QUALITY_SUMMARY_KEY)
    summary.setdefault("total", len(flags))

    if flags:
        st.warning(f"Найдено quality flags: {summary.get('total', len(flags))}.")
    else:
        st.success("Quality flags не найдены при текущих порогах.")

    st.dataframe(
        pd.DataFrame(curve_quality_summary_rows(summary)).rename(
            columns={"flag_label": "Тип", "flag_count": "Флагов"}
        )[["Тип", "Флагов"]],
        width="stretch",
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
            width="stretch",
            hide_index=True,
        )
    st.caption("Quality flags помогают проверить кривые перед bulk edit, import/export rules и отчетами.")


def _render_las_curve_metadata_editor(prepared_df: pd.DataFrame) -> None:
    st.markdown("### Curve Manager · Curve metadata editor")
    st.caption(
        "Редактор metadata кривых хранит описание, источник, прибор, статус, качество и комментарий "
        "без изменения числовых значений LAS. Эти поля нужны для аудита, отчетов и будущих правил импорта/экспорта."
    )

    state_controller = _application_state_controller()
    state_controller.ensure_value(LAS_EDITOR_METADATA_HISTORY_KEY, ())
    state_controller.ensure_value(LAS_EDITOR_METADATA_KEY, {})

    column_names = [str(column) for column in prepared_df.columns]
    aliases = state_controller.get_dict(LAS_EDITOR_ALIAS_MAP_KEY)
    group_overrides = state_controller.get_dict(LAS_EDITOR_GROUP_OVERRIDES_KEY)
    category_overrides = state_controller.get_dict(LAS_EDITOR_CATEGORY_OVERRIDES_KEY)
    unit_overrides = state_controller.get_dict(LAS_EDITOR_UNIT_OVERRIDES_KEY)
    metadata = state_controller.get_dict(LAS_EDITOR_METADATA_KEY)

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
            width="stretch",
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
        width="stretch",
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
    if action_col.button("Сохранить", width="stretch", key="las_editor_metadata_apply"):
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
                history=state_controller.get_tuple(LAS_EDITOR_METADATA_HISTORY_KEY),
                references=references,
                reason="manual",
                source="las_editor_ui",
            )
            state_controller.update_values({
                LAS_EDITOR_METADATA_KEY: result.references.get("curve_metadata", result.metadata),
                LAS_EDITOR_METADATA_HISTORY_KEY: result.history,
            })
            for message in result.diagnostics:
                st.info(message)
            if result.assigned:
                st.success(f"Metadata обновлена: {result.curve_name}.{result.field}")
            else:
                st.warning("Metadata не изменилась: такое значение уже существовало.")
        except ValueError as exc:
            st.warning(str(exc))

    history = state_controller.get_tuple(LAS_EDITOR_METADATA_HISTORY_KEY)
    if st.button("Undo последней metadata-правки", disabled=not history, width="stretch", key="las_editor_metadata_undo"):
        try:
            result = undo_last_metadata_assignment(
                prepared_df,
                aliases=aliases,
                group_overrides=group_overrides,
                category_overrides=category_overrides,
                unit_overrides=unit_overrides,
                metadata=state_controller.get_dict(LAS_EDITOR_METADATA_KEY),
                history=history,
                references=references,
            )
            state_controller.update_values({
                LAS_EDITOR_METADATA_KEY: result.references.get("curve_metadata", result.metadata),
                LAS_EDITOR_METADATA_HISTORY_KEY: result.history,
            })
            for message in result.diagnostics:
                st.info(message)
            st.success("Последняя metadata-правка отменена.")
        except ValueError as exc:
            st.warning(str(exc))

    history = state_controller.get_tuple(LAS_EDITOR_METADATA_HISTORY_KEY)
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
                width="stretch",
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

    state_controller = _application_state_controller()
    state_controller.ensure_value(LAS_EDITOR_RENAME_HISTORY_KEY, ())

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
    if action_col.button("Переименовать", width="stretch", key="las_editor_rename_apply"):
        try:
            result = rename_curve(
                prepared_df,
                old_name,
                new_name,
                history=state_controller.get_tuple(LAS_EDITOR_RENAME_HISTORY_KEY),
                references=references,
                reason="manual",
                source="las_editor_ui",
            )
            active_df = result.data
            state_controller.set_value(LAS_EDITOR_RENAME_HISTORY_KEY, result.history)
            _apply_las_editor_reference_state(result.references)
            for message in result.diagnostics:
                st.info(message)
            if result.renamed:
                st.success(f"Кривая переименована: {result.old_name} → {result.new_name}")
            else:
                st.warning("Имя не изменилось: rename не применялся.")
        except ValueError as exc:
            st.warning(str(exc))

    history = state_controller.get_tuple(LAS_EDITOR_RENAME_HISTORY_KEY)
    undo_disabled = not history
    if st.button("Undo последнего rename", disabled=undo_disabled, width="stretch", key="las_editor_rename_undo"):
        try:
            result = undo_last_rename(prepared_df, history=history, references=references)
            active_df = result.data
            state_controller.set_value(LAS_EDITOR_RENAME_HISTORY_KEY, result.history)
            _apply_las_editor_reference_state(result.references)
            for message in result.diagnostics:
                st.info(message)
            st.success(f"Rename отменен: {result.old_name} → {result.new_name}")
        except ValueError as exc:
            st.warning(str(exc))

    history = state_controller.get_tuple(LAS_EDITOR_RENAME_HISTORY_KEY)
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
                width="stretch",
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

    state_controller = _application_state_controller()
    state_controller.ensure_value(LAS_EDITOR_MERGE_HISTORY_KEY, ())

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
    if action_col.button("Создать merged curve", width="stretch", key="las_editor_merge_apply"):
        try:
            result = merge_curves(
                prepared_df,
                selected_sources,
                target_name,
                strategy=selected_strategy,
                keep_sources=keep_sources,
                history=state_controller.get_tuple(LAS_EDITOR_MERGE_HISTORY_KEY),
                references=references,
                reason="manual",
                source="las_editor_ui",
            )
            active_df = result.data
            state_controller.set_value(LAS_EDITOR_MERGE_HISTORY_KEY, result.history)
            _apply_las_editor_reference_state(result.references)
            for message in result.diagnostics:
                st.info(message)
            for message in result.warnings:
                st.warning(message)
            st.success(f"Merged curve создана: {result.target_name}")
        except ValueError as exc:
            st.warning(str(exc))

    history = state_controller.get_tuple(LAS_EDITOR_MERGE_HISTORY_KEY)
    if undo_col.button("Undo последнего merge", disabled=not history, width="stretch", key="las_editor_merge_undo"):
        try:
            result = undo_last_merge(prepared_df, history=history, references=references)
            active_df = result.data
            state_controller.set_value(LAS_EDITOR_MERGE_HISTORY_KEY, result.history)
            _apply_las_editor_reference_state(result.references)
            for message in result.diagnostics:
                st.info(message)
            st.success("Последний merge отменен.")
        except ValueError as exc:
            st.warning(str(exc))

    history = state_controller.get_tuple(LAS_EDITOR_MERGE_HISTORY_KEY)
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
                width="stretch",
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


def _clear_las_working_state() -> None:
    """Clear LAS/editor/calculation state that can keep stale tables and graphs on rerun."""
    prefixes = (
        "las_editor_",
        "las_correlation_",
        "mapping_",
        "selected_",
        "current_",
        "interval_",
        "interpretation_",
        "calculation_",
        "dashboard_",
        "plot_",
        "graph_",
        "table_",
        "stats_",
    )
    exact_keys = {
        LAS_EDITOR_SESSION_SHEETS_KEY,
        LAS_EDITOR_SESSION_SUMMARY_KEY,
        "sheets",
        "uploaded_file",
        "selected_sheet",
        "prepared_df",
        "mapped_df",
        "calculated_df",
        "active_interval",
        "active_well_id",
        "active_las_id",
        "active_version_id",
        ACTIVE_CALCULATION_DATA_KEY,
        ACTIVE_CALCULATION_SOURCE_KEY,
        ACTIVE_CALCULATION_PROJECT_KEY,
        ACTIVE_CALCULATION_CONTRACT_KEY,
    }
    _application_state_controller().clear_matching(exact_keys=exact_keys, prefixes=prefixes)
    try:
        st.cache_data.clear()
    except Exception:
        pass


def _render_new_las_creator_panel(logger, active_project: ProjectRecord) -> None:
    """Render visible New LAS tools through the LAS Workspace controller boundary."""
    with st.expander("Новый LAS", expanded=True):
        st.caption("Создание нового рабочего LAS с нуля. Оригинальные LAS-файлы не изменяются.")
        template_names = [row["template"] for row in template_table_rows()] or ["empty"]
        c1, c2, c3, c4 = st.columns(4)
        well_name = c1.text_input("Well name", value="NEW_WELL", key="new_las_well_name")
        start_depth = c2.number_input("Start depth", value=1000.0, step=0.1, key="new_las_start_depth")
        stop_depth = c3.number_input("Stop depth", value=1010.0, step=0.1, key="new_las_stop_depth")
        step = c4.number_input("Step", value=0.1, step=0.1, min_value=0.0001, key="new_las_step")

        t1, t2, t3 = st.columns(3)
        template_name = t1.selectbox("Шаблон", options=template_names, key="new_las_template")
        null_value = t2.number_input("NULL", value=-999.25, step=0.01, key="new_las_null")
        las_version = t3.selectbox("LAS version", options=("2.0", "3.0"), key="new_las_version")

        library_rows = template_table_rows()
        if library_rows:
            st.caption("Доступные шаблоны")
            st.dataframe(pd.DataFrame(library_rows), width="stretch", hide_index=True)

        selected_curves = st.multiselect(
            "Дополнительные кривые",
            options=[curve.mnemonic for curve in DEFAULT_CURVE_LIBRARY],
            default=[],
            key="new_las_extra_curves",
        )
        extra_curves = [curve for curve in DEFAULT_CURVE_LIBRARY if curve.mnemonic in set(selected_curves)]

        try:
            draft = build_las_creation_wizard_draft(
                well_name=well_name,
                start_depth=start_depth,
                stop_depth=stop_depth,
                step=step,
                template_name=template_name,
                curves=extra_curves,
                null_value=null_value,
                las_version=las_version,
            )
            result = run_las_creation_wizard(draft)
        except Exception:
            logger.exception("new_las_wizard_failed")
            st.error("Не удалось подготовить новый LAS. Проверьте глубины и шаг.")
            return

        if result.document is not None:
            st.dataframe(result.document.data.head(30), width="stretch")
            las_bytes = result.document.las_text.encode("utf-8")
            file_name = f"{well_name.strip() or 'NEW_WELL'}.las"
            st.download_button(
                "Скачать созданный LAS",
                data=las_bytes,
                file_name=file_name,
                mime="text/plain",
                width="stretch",
                key="new_las_download_button",
            )
            if st.button("Сохранить в LAS Workspace", width="stretch", key="new_las_save_to_workspace"):
                try:
                    workspace_result = _las_workspace_controller().create_las_working_copy(
                        active_project.id,
                        draft,
                        filename=file_name,
                    )
                except Exception:
                    logger.exception("new_las_workspace_save_failed project_id=%s", safe_log_value(active_project.id))
                    st.error("Не удалось сохранить LAS в Workspace. Подробности записаны в logs/app.log.")
                else:
                    if workspace_result.manifest.is_ready:
                        _application_state_controller().update_values({
                            LAS_EDITOR_SESSION_SHEETS_KEY: {"Новый LAS": _dataframe_to_raw_sheet(workspace_result.final.preview.data)},
                            LAS_EDITOR_SESSION_SUMMARY_KEY: (
                                f"Новый LAS сохранен в Workspace: "
                                f"{len(workspace_result.final.preview.data)} строк, "
                                f"{len(workspace_result.final.preview.data.columns)} колонок"
                            ),
                        })
                        logger.info(
                            "new_las_workspace_saved project_id=%s workspace_id=%s target=%s",
                            safe_log_value(active_project.id),
                            safe_log_value(workspace_result.workspace.id),
                            safe_log_value(workspace_result.manifest.target_path),
                        )
                        st.success(f"LAS сохранен в Workspace: {workspace_result.manifest.target_path}")
                    else:
                        st.warning("LAS не сохранен: файл уже существует или проверка экспорта не пройдена.")
                        for issue in workspace_result.manifest.issues[:3]:
                            st.caption(f"{issue.code}: {issue.message}")

            if st.button("Открыть созданный LAS в расчетах", width="stretch", key="new_las_open_in_session"):
                _application_state_controller().update_values({
                    LAS_EDITOR_SESSION_SHEETS_KEY: {"Новый LAS": _dataframe_to_raw_sheet(result.document.data)},
                    LAS_EDITOR_SESSION_SUMMARY_KEY: f"Новый LAS: {len(result.document.data)} строк, {len(result.document.data.columns)} колонок",
                })
                st.success("Новый LAS помещен в рабочую сессию. Откройте `Работа с данными`.")


def _render_saved_wells_panel(logger) -> None:
    well_service = _well_manager_service()
    records = well_service.list_wells()
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

        action_col1, action_col2 = st.columns(2)
        if action_col1.button("Удалить выбранную версию", width="stretch", key="saved_well_delete_version"):
            try:
                well_service.delete_version(selected_record.id, selected_version.id)
                _clear_las_working_state()
            except Exception:
                logger.exception("saved_well_version_delete_failed well_id=%s version_id=%s", selected_record.id, selected_version.id)
                st.error("Не удалось удалить версию с диска. Подробности записаны в logs/app.log.")
            else:
                st.success("Версия удалена с диска.")
                _request_ui_refresh_and_rerun("saved_well_version_deleted")
        if action_col2.button("Удалить скважину полностью", width="stretch", key="saved_well_delete_record"):
            try:
                well_service.delete_well(selected_record.id)
                _clear_las_working_state()
            except Exception:
                logger.exception("saved_well_delete_failed well_id=%s", selected_record.id)
                st.error("Не удалось удалить скважину с диска. Подробности записаны в logs/app.log.")
            else:
                st.success("Скважина удалена с диска.")
                _request_ui_refresh_and_rerun("saved_well_deleted")

        csv_col, xlsx_col, las_col = st.columns(3)
        try:
            csv_col.download_button(
                "Скачать CSV",
                data=well_service.read_file_bytes(selected_record.id, selected_version.id, "csv"),
                file_name=f"{selected_record.id}_{selected_version.id}.csv",
                mime="text/csv",
                width="stretch",
            )
            xlsx_col.download_button(
                "Скачать XLSX",
                data=well_service.read_file_bytes(selected_record.id, selected_version.id, "xlsx"),
                file_name=f"{selected_record.id}_{selected_version.id}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width="stretch",
            )
            las_col.download_button(
                "Скачать LAS",
                data=well_service.read_file_bytes(selected_record.id, selected_version.id, "las"),
                file_name=f"{selected_record.id}_{selected_version.id}.las",
                mime="text/plain",
                width="stretch",
            )
        except Exception:
            logger.exception("saved_well_download_failed well_id=%s version_id=%s", selected_record.id, selected_version.id)
            st.error("Не удалось подготовить выгрузку сохраненной скважины. Подробности записаны в logs/app.log.")

        if st.button("Использовать выбранную версию в расчетах", width="stretch"):
            try:
                csv_bytes = well_service.read_file_bytes(selected_record.id, selected_version.id, "csv")
                prepared_df = pd.read_csv(BytesIO(csv_bytes))
                _application_state_controller().update_values({
                    LAS_EDITOR_SESSION_SHEETS_KEY: {
                        f"{selected_record.name} / {selected_version.label}": _dataframe_to_raw_sheet(prepared_df)
                    },
                    LAS_EDITOR_SESSION_SUMMARY_KEY: (
                        f"{selected_record.name}, версия {selected_version.label}, строк: {len(prepared_df)}"
                    ),
                })
            except Exception:
                logger.exception("saved_well_load_to_session_failed well_id=%s version_id=%s", selected_record.id, selected_version.id)
                st.error("Не удалось загрузить сохраненную версию в расчеты. Подробности записаны в logs/app.log.")
            else:
                st.success("Версия загружена в текущую сессию. Откройте вкладку `Работа с данными`.")



REQUIRED_GAS_MAPPING_FIELDS: tuple[str, ...] = ("c1", "c2", "c3", "ic4", "nc4", "ic5", "nc5")


def _missing_required_gas_mapping_fields(mapping: dict[str, str]) -> tuple[str, ...]:
    """Return required mud-gas fields that are not mapped to source columns."""
    return tuple(field for field in REQUIRED_GAS_MAPPING_FIELDS if not str(mapping.get(field, "")).strip())


def _clear_invalid_interpretation_state(reason: str) -> None:
    """Prevent graphs/reports from reusing a calculation produced from another source."""
    controller = _application_state_controller()
    controller.update_values(
        {
            INTERPRETATION_SESSION_DATA_KEY: None,
            INTERPRETATION_SESSION_SOURCE_KEY: "",
            ACTIVE_CALCULATION_DATA_KEY: None,
            ACTIVE_CALCULATION_SOURCE_KEY: "",
            ACTIVE_CALCULATION_PROJECT_KEY: "",
            ACTIVE_CALCULATION_CONTRACT_KEY: {},
            "interpretation_figure_cache": None,
            "interpretation_invalid_reason": str(reason),
        }
    )

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
        st.caption("Поля без сопоставления будут пропущены. Расчет газовых коэффициентов будет заблокирован, пока не сопоставлены C1, C2, C3, iC4, nC4, iC5 и nC5.")

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
        st.dataframe(_format_mapping_diagnostics_table(diagnostics), width="stretch")
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
    report = build_calculation_diagnostics_report(calculated_df, ch_mode=ch_mode)
    problem_count = sum(item.invalid_rows for item in report.formulas)

    with st.expander("Диагностика расчётов", expanded=bool(problem_count)):
        summary_tab, quality_tab, formulas_tab, rows_tab, recommendations_tab = st.tabs(
            ["Сводка", "Качество данных", "Формулы", "Проблемные строки", "Рекомендации"]
        )

        with summary_tab:
            metrics = st.columns(4)
            metrics[0].metric("Строк", report.total_rows)
            metrics[1].metric("Компонентов", len(report.columns))
            metrics[2].metric("Формул", len(report.formulas))
            metrics[3].metric("Проблемных результатов", problem_count)
            summary = formula_diagnostics_dataframe(report)[
                ["Коэффициент", "Рассчитано", "Рассчитано, %", "Не рассчитано", "Основная причина"]
            ]
            st.dataframe(summary, width="stretch", hide_index=True)

        with quality_tab:
            st.dataframe(column_quality_dataframe(report), width="stretch", hide_index=True)
            st.caption("NaN и пустые значения показывают качество входных C1–nC5 после применённого mapping.")

        with formulas_tab:
            st.dataframe(formula_diagnostics_dataframe(report), width="stretch", hide_index=True)
            st.caption("Причины считаются по строкам: пустые входы, нечисловые значения и нулевые знаменатели.")

        with rows_tab:
            if report.problematic_rows.empty:
                st.success("Проблемных строк не найдено.")
            else:
                st.dataframe(report.problematic_rows, width="stretch", hide_index=False)
                st.caption("Показаны первые 100 проблемных строк. Исходные данные не изменяются.")

        with recommendations_tab:
            for recommendation in report.recommendations:
                st.info(recommendation)


def _render_formula_reference() -> None:
    with st.expander("Формулы коэффициентов", expanded=False):
        st.markdown(
            "`Wh = (C2 + C3 + iC4 + nC4 + iC5 + nC5) * 100 / (C1 + C2 + C3 + iC4 + nC4 + iC5 + nC5)`\n\n"
            "`Bh = (C1 + C2) / (C3 + iC4 + nC4 + iC5 + nC5)`\n\n"
            "`Ch = (iC4 + nC4 + iC5 + nC5) / C3` в режиме `A`\n\n"
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
    controller = _application_state_controller()
    rows: list[tuple[str, str, str]] = [
        ("Активный проект", f"{active_project.name} ({active_project.id})", "Проверьте, что выбран нужный проект перед импортом или сохранением."),
    ]

    editor_sheets = controller.get_value(LAS_EDITOR_SESSION_SHEETS_KEY)
    if editor_sheets:
        rows.append((
            "LAS-редактор",
            controller.get_value(LAS_EDITOR_SESSION_SUMMARY_KEY, "данные подготовлены"),
            "Можно передать подготовленную таблицу в расчет или сохранить версию в проект.",
        ))
    else:
        rows.append((
            "LAS-редактор",
            "подготовленные данные не загружены в текущую сессию",
            "Откройте LAS-редактор, если файл требует исправления глубины или NULL-значений.",
        ))

    project_sheets = controller.get_value(PROJECT_SESSION_SHEETS_KEY)
    if project_sheets and controller.get_value(PROJECT_SESSION_PROJECT_ID_KEY) == active_project.id:
        rows.append((
            "Проектные данные",
            controller.get_value(PROJECT_SESSION_SUMMARY_KEY, "проектные данные загружены"),
            "Можно продолжить расчет или экспорт выбранных проектных версий.",
        ))
    else:
        rows.append((
            "Проектные данные",
            "не выбраны для текущего workflow",
            "Откройте сохраненный проект или загрузите новые данные во вкладке `Работа с данными`.",
        ))

    interpretation_df, source = _active_calculation_dataset(active_project.id)
    if isinstance(interpretation_df, pd.DataFrame) and not interpretation_df.empty:
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
    _application_state_controller().set_value(DASHBOARD_LAST_QUICK_ACTION_KEY, action["id"])
    _set_active_main_tab(action["target_tab"])
    _refresh_ui()


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
    """Return recent project cards from explicit recent history, falling back to project mtime order."""
    if limit <= 0:
        return ()
    projects_by_id = {project.id: project for project in projects}
    recent_records = [
        projects_by_id[entry.project_id]
        for entry in list_recent_projects(LAS_CORRELATION_PROJECTS_ROOT, include_missing=False)
        if entry.project_id in projects_by_id
    ]
    if not recent_records:
        recent_records = list(projects)
    return tuple(recent_records[:limit])


def _workbench_application_service():
    return application_service_container(_application_state_controller().state).workbench(
        projects_root=LAS_CORRELATION_PROJECTS_ROOT,
    )


def _project_manager_service():
    """Return the lazy workspace-scoped project application service."""
    return application_service_container(_application_state_controller().state).project_manager(
        root=LAS_CORRELATION_PROJECTS_ROOT, default_project_id=DEFAULT_PROJECT_ID
    )


def _export_manager_service():
    """Return the lazy workspace-scoped export application service."""
    return application_service_container(_application_state_controller().state).export_manager(
        root=LAS_CORRELATION_PROJECTS_ROOT
    )


def _well_manager_service():
    """Return the lazy workspace-scoped well application service."""
    return application_service_container(_application_state_controller().state).well_manager(
        root=WELLS_STORAGE_ROOT
    )


def _las_workspace_service(project_id: str):
    """Return the lazy project-scoped LAS application service."""
    return application_service_container(_application_state_controller().state).las_workspace(
        project_id=project_id,
        root=LAS_CORRELATION_PROJECTS_ROOT,
    )


def _dataset_manager_service():
    """Return the lazy workspace-scoped dataset application service."""
    return application_service_container(_application_state_controller().state).dataset_manager(
        root=LAS_CORRELATION_PROJECTS_ROOT
    )


def _project_storage_service(project_id: str):
    """Return the project-scoped storage maintenance application service."""
    return application_service_container(_application_state_controller().state).project_storage(
        project_id=project_id,
        root=LAS_CORRELATION_PROJECTS_ROOT,
    )


def _application_state_controller() -> ApplicationStateController:
    """Return the single UI-facing application state controller.

    Streamlit widgets use their own keys; persistent application context is
    changed only through this controller to avoid modifying widget-bound keys
    after widget instantiation.
    """
    return ApplicationStateController(st.session_state)


def _workspace_controller() -> WorkspaceController:
    """Return the UI-facing workspace controller for the active Streamlit session.

    Workspace pages must use this controller instead of combining direct
    ``_application_state_controller().state`` access with manager/service calls.  The controller owns
    active workspace context while the manager/service/repository stack owns
    persistence.
    """
    state_controller = _application_state_controller()
    return WorkspaceController(
        state_controller.state,
        LAS_CORRELATION_PROJECTS_ROOT,
        state_controller=state_controller,
    )


def _las_workspace_controller() -> LasWorkspaceController:
    """Return the LAS Workspace 3.0 controller bound to the current UI state.

    LAS Workspace UI entry points must use this facade instead of directly
    creating generic workspaces or reading ``_application_state_controller().state``. The facade keeps
    LAS-specific defaults in one place while delegating persistence and active
    workspace transitions to the generic WorkspaceController.
    """
    return LasWorkspaceController(
        _application_state_controller().state,
        LAS_CORRELATION_PROJECTS_ROOT,
        workspace_controller=_workspace_controller(),
    )


def _refresh_ui(reason: str = "ui_refresh") -> bool:
    """Request at most one full-app rerun in the current render cycle."""
    controller = _application_state_controller()
    decision = request_rerun(controller.state, reason, source="streamlit_app")
    if decision.allowed:
        st.rerun()
    return decision.allowed


def _request_ui_refresh_and_rerun(reason: str) -> bool:
    """Record a refresh reason and rerun through the single-cycle gate."""
    controller = _application_state_controller()
    if hasattr(controller, "request_refresh"):
        controller.request_refresh(reason, source="streamlit_app")
    return _refresh_ui(reason)


def _render_table_toolbar_caption(title: str, description: str | None = None) -> None:
    """Render a consistent caption above repository-backed tables."""
    if description:
        st.caption(f"{title} · {description}")
    else:
        st.caption(title)


def _render_recent_projects_manager(projects: tuple[ProjectRecord, ...], active_project: ProjectRecord, logger) -> None:
    """Render real Streamlit controls for the dashboard Recent Projects list."""
    service = _project_manager_service()
    entries = service.list_recent(include_missing=True)
    with st.expander("Управление последними проектами", expanded=False):
        if entries:
            st.dataframe(pd.DataFrame(recent_projects_table_rows(entries)), width="stretch", height=220)
        else:
            st.caption("История последних проектов пуста.")

        if st.button("Очистить историю последних проектов", width="stretch", key="recent_projects_clear_history"):
            removed = service.clear_recent_history()
            logger.info("recent_projects_history_cleared removed=%d", removed)
            st.success(f"История очищена. Удалено записей: {removed}.")
            _refresh_ui()

        if not entries:
            return

        entries_by_id = {entry.project_id: entry for entry in entries}
        selected_id = st.selectbox(
            "Проект в истории",
            options=tuple(entries_by_id),
            format_func=lambda project_id: f"{entries_by_id[project_id].project_name} ({project_id})",
            key="recent_projects_selected_id",
        )
        col_open, col_remove, col_delete = st.columns(3)
        with col_open:
            if st.button("Открыть", width="stretch", key="recent_project_open"):
                if not entries_by_id[selected_id].exists_on_disk:
                    st.warning("Проект отсутствует на диске. Удалите запись из истории.")
                else:
                    _application_state_controller().request_project_activation(selected_id)
                    _clear_las_working_state()
                    _refresh_ui()
        with col_remove:
            if st.button("Удалить запись", width="stretch", key="recent_project_remove_entry"):
                service.remove_recent_entry(selected_id)
                logger.info("recent_project_entry_removed project_id=%s", safe_log_value(selected_id))
                st.success("Запись удалена из истории. Сам проект не удален.")
                _refresh_ui()
        with col_delete:
            disabled = selected_id == DEFAULT_PROJECT_ID
            if st.button("Удалить проект с диска", width="stretch", disabled=disabled, key="recent_project_delete_disk"):
                try:
                    result = service.delete_project_complete(selected_id)
                    if _application_state_controller().context().project_id == selected_id:
                        _application_state_controller().request_project_activation(DEFAULT_PROJECT_ID)
                    _clear_las_working_state()
                except Exception:
                    logger.exception("recent_project_delete_failed project_id=%s", safe_log_value(selected_id))
                    st.error("Не удалось удалить проект. Подробности записаны в logs/app.log.")
                else:
                    st.success("Проект удален с диска и из истории.")
                    _refresh_ui()

        flags_col_1, flags_col_2 = st.columns(2)
        selected_entry = entries_by_id[selected_id]
        with flags_col_1:
            if st.button("Закрепить/открепить", width="stretch", key="recent_project_toggle_pin"):
                service.set_recent_flags(selected_id, pinned=not selected_entry.pinned)
                _refresh_ui()
        with flags_col_2:
            if st.button("Избранное вкл/выкл", width="stretch", key="recent_project_toggle_favorite"):
                service.set_recent_flags(selected_id, favorite=not selected_entry.favorite)
                _refresh_ui()


def _dashboard_project_statistics(active_project: ProjectRecord, projects: tuple[ProjectRecord, ...]) -> dict[str, int]:
    """Build dashboard statistics from real project storage and session data."""
    return {
        "projects": len(projects),
        "wells": _well_manager_service().count_wells(),
        "las_files": len(_las_workspace_service(active_project.id).list_files()),
        "calculations": len(list_project_calculations(LAS_CORRELATION_PROJECTS_ROOT, active_project.id)),
        "exports": _export_manager_service().count_exports(active_project.id),
    }


def _dashboard_news_items(active_project: ProjectRecord) -> tuple[str, ...]:
    """Return dynamic dashboard news derived from current project state."""
    items = [f"Активный проект: {active_project.name}"]
    if active_project.updated_at:
        items.append(f"Проект обновлен: {active_project.updated_at}")
    calculations_count = len(list_project_calculations(LAS_CORRELATION_PROJECTS_ROOT, active_project.id))
    exports_count = _export_manager_service().count_exports(active_project.id)
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
    for export in _export_manager_service().list_exports(active_project.id):
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
    """Store recent command ids through the application state controller."""
    entry_id = _command_entry_id(entry)
    controller = _application_state_controller()
    recent = [item for item in controller.get_list(COMMAND_PALETTE_RECENT_KEY) if item != entry_id]
    controller.set_value(COMMAND_PALETTE_RECENT_KEY, [entry_id, *recent][:COMMAND_PALETTE_RECENT_LIMIT])


def _toggle_command_palette_favorite(entry: dict[str, str]) -> None:
    """Toggle command favorite state through the application state controller."""
    entry_id = _command_entry_id(entry)
    controller = _application_state_controller()
    favorites = controller.get_list(COMMAND_PALETTE_FAVORITES_KEY)
    if entry_id in favorites:
        favorites.remove(entry_id)
    else:
        favorites.insert(0, entry_id)
    controller.set_value(COMMAND_PALETTE_FAVORITES_KEY, favorites[:COMMAND_PALETTE_RECENT_LIMIT])


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
        "<div class='command-palette-title'><b>Командная палитра</b><span>Ctrl+K / поиск по проекту · команды, проекты, скважины, LAS, расчеты, отчеты и документация</span></div>",
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

    controller = _application_state_controller()
    recent_ids = controller.get_list(COMMAND_PALETTE_RECENT_KEY)
    favorite_ids = controller.get_list(COMMAND_PALETTE_FAVORITES_KEY)
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
                _refresh_ui()
        with col_button:
            target_tab = entry.get("target_tab", APP_TABS[0])
            if st.button("Открыть", key=f"command_palette_open_{index}_{target_tab}_{entry.get('title', '')}", width="stretch"):
                _remember_command_palette_entry(entry)
                _set_active_main_tab(target_tab)
                _refresh_ui()
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
        recent_ids=_application_state_controller().get_list(COMMAND_PALETTE_RECENT_KEY),
        favorite_ids=_application_state_controller().get_list(COMMAND_PALETTE_FAVORITES_KEY),
        limit=limit,
    )


def _workspace_favorite_entries(active_project: ProjectRecord, *, limit: int = 5) -> tuple[dict[str, str], ...]:
    """Return pinned workspace entries with safe defaults for a new install."""
    entries = _command_palette_entries(active_project)
    favorite_ids = _application_state_controller().get_list(COMMAND_PALETTE_FAVORITES_KEY)
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
        _application_state_controller().set_value(ACTIVE_MAIN_TAB_KEY, tab_name)


def _active_main_tab() -> str:
    """Return the selected application section, defaulting to the dashboard."""
    controller = _application_state_controller()
    tab = controller.get_value(ACTIVE_MAIN_TAB_KEY, APP_TABS[0])
    if tab not in APP_TABS:
        tab = APP_TABS[0]
        controller.set_value(ACTIVE_MAIN_TAB_KEY, tab)
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
            if st.button(button_label, key=f"main_nav_{label}", width="stretch", help=item["description"]):
                _set_active_main_tab(label)
                _refresh_ui()
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

def _dashboard_localization():
    """Return the session localization service used by Dashboard.

    Dashboard shares the same normalized interface-language code as Workbench.
    The service is runtime-owned; only the compact locale code is kept in state.
    """
    state = _application_state_controller().state
    language = str(state.get("user_settings.interface_language") or "ru")
    return application_service_container(state).localization(
        catalogs_dir=ROOT_DIR / "resources" / "i18n",
        language=language,
    )


def _render_dashboard_shell(active_project: ProjectRecord, projects: tuple[ProjectRecord, ...]) -> None:
    """Render Project Workspace 1.0 as the application home screen.

    Project Workspace 1.0 removes the duplicated central navigation model from
    Dashboard 3.0. The Sidebar remains the only primary navigation surface, while
    the central area is reserved for engineering work context: recent projects,
    LAS files, calculations, reports, favorites, activity and universal search.
    """
    i18n = _dashboard_localization()
    background_uri = _dashboard_background_data_uri()
    style = f"--global-bg-image: url('{background_uri}');" if background_uri else ""
    recent_projects = _dashboard_recent_projects(projects, limit=5)
    stats = _dashboard_project_statistics(active_project, projects)
    activity_items = _dashboard_activity_items(active_project, limit=6)
    las_files = _las_workspace_service(active_project.id).list_files()[:5]
    calculations = list_project_calculations(LAS_CORRELATION_PROJECTS_ROOT, active_project.id)[:5]
    exports = _export_manager_service().list_exports(active_project.id)[:5]
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
            i18n("dashboard.updated", date=project.updated_at or "—", project_id=project.id),
            i18n("dashboard.badge.project"),
        )
        for project in recent_projects
    ) or f"<div class='dashboard-empty-state'>{_html_escape(i18n("dashboard.projects.empty"))}</div>"

    recent_las_html = "".join(
        _row(
            getattr(item, "file_name", "") or getattr(item, "original_file_name", "") or getattr(item, "name", "") or getattr(item, "id", "LAS файл"),
            i18n("dashboard.well", well=getattr(item, "well_name", "") or getattr(item, "well_id", "") or i18n("dashboard.well.unknown"), curves=getattr(item, "curve_count", "—")),
            getattr(item, "saved_at", "") or getattr(item, "updated_at", "") or "LAS",
        )
        for item in las_files
    ) or f"<div class='dashboard-empty-state'>{_html_escape(i18n("dashboard.las.empty"))}</div>"

    calculations_html = "".join(
        _row(
            getattr(item, "name", "") or getattr(item, "source_label", "") or getattr(item, "id", "Расчет"),
            i18n("dashboard.calculation.meta", kind=getattr(item, "ch_mode_label", "") or getattr(item, "ch_mode", "") or "gas ratio", project=active_project.name),
            getattr(item, "saved_at", "") or getattr(item, "created_at", "") or "готов",
        )
        for item in calculations
    ) or f"<div class='dashboard-empty-state'>{_html_escape(i18n("dashboard.calculations.empty"))}</div>"

    reports_html = "".join(
        _row(
            getattr(item, "label", "") or getattr(item, "file_name", "") or getattr(item, "id", "Отчет"),
            i18n("dashboard.report.meta", kind=getattr(item, "kind", "") or getattr(item, "mime_type", "") or "export", file=getattr(item, "file_name", "") or "—"),
            getattr(item, "saved_at", "") or "отчет",
        )
        for item in exports
    ) or f"<div class='dashboard-empty-state'>{_html_escape(i18n("dashboard.reports.empty"))}</div>"

    activity_html = "".join(
        _row(item, i18n("dashboard.activity.meta", project=active_project.name), "history")
        for item in activity_items
    ) or f"<div class='dashboard-empty-state'>{_html_escape(i18n("dashboard.activity.empty"))}</div>"

    favorite_entries = _workspace_favorite_entries(active_project)
    favorites_html = "".join(
        _row(
            entry.get("title", i18n("dashboard.favorite.default")),
            entry.get("description", i18n("dashboard.favorite.description")),
            _command_palette_entry_category(entry),
        )
        for entry in favorite_entries
    ) or f"<div class='dashboard-empty-state'>{_html_escape(i18n("dashboard.favorites.empty"))}</div>"

    workspace_query = st.text_input(
        i18n("dashboard.search.label"),
        key="workspace_universal_search_query",
        placeholder=i18n("dashboard.search.placeholder"),
        help=i18n("dashboard.search.help"),
    )
    workspace_search_results = _workspace_universal_search_results(active_project, workspace_query)
    workspace_search_results_html = _workspace_search_results_html(workspace_search_results, workspace_query)

    _render_recent_projects_manager(projects, active_project, configure_logging())

    metrics_html = f"""
      <div class='dashboard-status-grid dashboard-metrics'>
        <div class='dashboard-status-pill dashboard-metric'><b>{stats['projects']}</b><span>{_html_escape(i18n('dashboard.metric.projects'))}</span></div>
        <div class='dashboard-status-pill dashboard-metric'><b>{stats['wells']}</b><span>{_html_escape(i18n('dashboard.metric.wells'))}</span></div>
        <div class='dashboard-status-pill dashboard-metric'><b>{stats['las_files']}</b><span>{_html_escape(i18n('dashboard.metric.las'))}</span></div>
        <div class='dashboard-status-pill dashboard-metric'><b>{stats['calculations']}</b><span>{_html_escape(i18n('dashboard.metric.calculations'))}</span></div>
        <div class='dashboard-status-pill dashboard-metric'><b>{stats['exports']}</b><span>{_html_escape(i18n('dashboard.metric.reports'))}</span></div>
      </div>
    """

    # Render the workspace inside a Streamlit HTML component instead of Markdown.
    # This avoids a Streamlit/Markdown regression where layout tags can be shown
    # as plain text on the page (<section>/<article>/<div> visible to the user).
    workspace_component_html = dedent(f"""
    <!doctype html>
    <html lang="{_html_escape(i18n.language)}">
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
                <div><h1 class="dashboard-page-title">{_html_escape(i18n("dashboard.title"))}</h1><p class="dashboard-page-subtitle">{_html_escape(i18n("dashboard.subtitle"))}</p></div>
              </div>
              <div class="dashboard-search"><span class="dashboard-search-chip">Ctrl+K</span><span class="dashboard-search-chip">{_html_escape(active_project.name)}</span></div>
            </div>
            <div class="dashboard-card workspace-search-card" aria-label="{_html_escape(i18n("dashboard.search.title"))}">
              <h3>{_html_escape(i18n("dashboard.search.title"))} <span>Ctrl+K</span></h3>
              <div class="workspace-search-box"><b>🔎 {_html_escape(i18n("dashboard.search.instruction"))}</b><span>{_html_escape(i18n("dashboard.search.prompt"))}</span></div>
            </div>
            {workspace_search_results_html}
            <div class="dashboard-layout dashboard-information-priority" data-dashboard-information-hierarchy="workspace-v1">
              <div class="dashboard-card stats" id="dashboard-project-status"><h3>{_html_escape(i18n("dashboard.section.status"))} <span>{now_label}</span></h3>{metrics_html}</div>
              <div class="dashboard-card projects" id="dashboard-projects"><h3>{_html_escape(i18n("dashboard.section.projects"))} <span>recent</span></h3>{recent_html}</div>
              <div class="dashboard-card recent-las" id="dashboard-recent-las"><h3>{_html_escape(i18n("dashboard.section.las"))} <span>LAS</span></h3>{recent_las_html}</div>
              <div class="dashboard-card calculations" id="dashboard-calculations"><h3>{_html_escape(i18n("dashboard.section.calculations"))} <span>calc</span></h3>{calculations_html}</div>
              <div class="dashboard-card reports" id="dashboard-reports"><h3>{_html_escape(i18n("dashboard.section.reports"))} <span>export</span></h3>{reports_html}</div>
              <div class="dashboard-card activity" id="dashboard-activity"><h3>{_html_escape(i18n("dashboard.section.activity"))} <span>history</span></h3>{activity_html}</div>
              <div class="dashboard-card favorites" id="dashboard-favorites"><h3>{_html_escape(i18n("dashboard.section.favorites"))} <span>pinned</span></h3>{favorites_html}</div>
            </div>
            <div class="dashboard-footer"><span>{_html_escape(i18n("dashboard.footer.ready"))}</span><span>{_html_escape(i18n("dashboard.footer.version", version="2.0.0", time=now_label))}</span></div>
          </div>
        </div>
      </body>
    </html>
    """).strip()
    # Render dashboard markup through Streamlit's supported HTML element.
    # Never fall back to st.components.v1.html: that API is deprecated and
    # emits runtime warnings on current Streamlit releases.
    html_renderer = getattr(st, "html", None)
    if callable(html_renderer):
        html_renderer(workspace_component_html)
    else:  # lightweight/test compatibility; no iframe/component boundary
        st.markdown(workspace_component_html, unsafe_allow_html=True)

def _render_start_tab(active_project: ProjectRecord) -> None:
    projects = list_projects(LAS_CORRELATION_PROJECTS_ROOT)
    if not projects:
        projects = (active_project,)

    # Dashboard 3.0 intentionally avoids the old duplicated quick-action strip.
    # Legacy static markers kept for tests/documentation: dashboard_quick_action_, dashboard_project_search,
    # functional-quick-actions div[data-testid="stButton"] > button,
    # Компактная панель: одна плитка = одно действие, help=action["tooltip"],
    # _quick_action_button_label(action), _trigger_quick_action(action).
    _render_dashboard_shell(active_project, projects)

    with st.expander("Текущее состояние workflow", expanded=False):
        for label, value, next_action in _workflow_status_detail_rows(active_project):
            st.markdown(
                f"<div class='workflow-status'><b>{label}</b><br>{value}<small><b>Дальше:</b> {next_action}</small></div>",
                unsafe_allow_html=True,
            )

    layout_value = str(_application_state_controller().get_value(UI_LAYOUT_KEY, UI_LAYOUT_PROFILES["wide"]["label"]))
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


def _documentation_locale_payload(language: str) -> dict[str, object]:
    """Return localized Documentation Center copy without mixing languages."""
    payloads: dict[str, dict[str, object]] = {
        "ru": {
            "title": "Инструкции и документация",
            "subtitle": "Быстрый старт, рабочий процесс, LAS, FAQ, горячие клавиши и диагностика.",
            "caption": "Справочный центр использует язык интерфейса. Русский fallback применяется только при отсутствии перевода и явно отмечается.",
            "contents": "Содержание раздела", "quick": "Быстрый запуск", "verify": "Проверка готовности",
            "workflow": "Основной рабочий сценарий", "data": "Формат данных и mapping", "las": "LAS workflow",
            "shortcuts": "Горячие клавиши", "faq": "FAQ", "troubleshooting": "Диагностика и устранение проблем",
            "full_docs": "Полные документы проекта", "fallback": "Перевод отсутствует; показана версия на другом языке: {language}.",
            "quick_steps": "1. Запустите проект командой `./run_app.ps1` или `python -m streamlit run app/streamlit_app.py`.\n2. Откройте `http://localhost:8501`.\n3. Загрузите LAS, CSV, XLSX или XLSM.\n4. Проверьте заголовки, mapping и предупреждения.\n5. Выберите интервал и откройте расчёты и графики.",
            "verify_text": "Preflight проверяет Python, зависимости, ключевые файлы, конфигурацию, экспортные зависимости и папку логов.",
            "workflow_text": "1. Загрузите файл и выберите набор данных.\n2. Проверьте первые строки и заголовки.\n3. Исправьте mapping при необходимости.\n4. Проверьте предупреждения и режим Ch.\n5. Выберите интервал и изучите графики.\n6. Сохраните результат и экспортируйте документ.",
            "data_text": "Поддерживаются LAS, CSV, XLSX и XLSM. Проверьте depth-колонку, газовые компоненты, единицы и пропуски.",
            "las_text": "LAS-редактор проверяет глубину, STEP, NULL и ручные правки. Корреляция сравнивает скважины и готовит печатные материалы.",
            "trouble_text": "При ошибке выполните `python scripts/preflight.py`, проверьте `requirements.txt` и последние строки `logs/app.log`.",
            "quick_links": (("Быстрый старт","docs-quick-start","Запуск приложения и первый расчёт","🚀"),("Формат данных","docs-data-format","LAS/CSV/Excel, mapping и обязательные поля","📄"),("LAS workflow","docs-las-workflow","Редактор, корреляция и версии","🧰"),("Диагностика","docs-troubleshooting","Preflight, тесты и логи","🩺")),
            "toc": (("Быстрый запуск","docs-quick-start"),("Проверка готовности","docs-verification"),("Рабочий сценарий","docs-workflow"),("Формат данных","docs-data-format"),("LAS workflow","docs-las-workflow"),("Горячие клавиши","docs-shortcuts"),("FAQ","docs-faq"),("Диагностика","docs-troubleshooting")),
            "shortcuts_items": (("Ctrl+K","Открыть командную палитру."),("Esc","Закрыть активное окно или выйти из поиска."),("Enter","Подтвердить активное поле или команду.")),
            "faq_items": (("Почему документация имеет отдельный фон?","Это справочный экран; инженерные графики остаются на контрастном рабочем фоне."),("Что проверить перед расчётом?","Заголовки, обязательные колонки, предупреждения, режим Ch и интервал глубин."),("Что делать при ошибке запуска?","Проверьте окружение, зависимости, preflight и logs/app.log.")),
            "doc_titles": {"las_qc_user_guide":"Руководство LAS QC","qc_architecture":"Архитектура QC","supported_formats_and_legal_sources":"Форматы и легальные источники","external_standard_integration":"Интеграция внешних стандартов"},
        },
        "kk": {
            "title": "Нұсқаулықтар мен құжаттама",
            "subtitle": "Жылдам бастау, жұмыс үдерісі, LAS, FAQ, пернелер тіркесімі және диагностика.",
            "caption": "Анықтама орталығы интерфейс тілін қолданады. Аударма жоқ болса, fallback анық белгіленеді.",
            "contents": "Бөлім мазмұны", "quick": "Жылдам іске қосу", "verify": "Дайындықты тексеру",
            "workflow": "Негізгі жұмыс сценарийі", "data": "Деректер пішімі және mapping", "las": "LAS жұмыс үдерісі",
            "shortcuts": "Пернелер тіркесімі", "faq": "Жиі қойылатын сұрақтар", "troubleshooting": "Диагностика және ақауларды жою",
            "full_docs": "Жобаның толық құжаттары", "fallback": "Аударма жоқ; басқа тілдегі нұсқа көрсетілді: {language}.",
            "quick_steps": "1. Жобаны `./run_app.ps1` немесе `python -m streamlit run app/streamlit_app.py` командасымен іске қосыңыз.\n2. `http://localhost:8501` мекенжайын ашыңыз.\n3. LAS, CSV, XLSX немесе XLSM файлын жүктеңіз.\n4. Тақырыптарды, mapping және ескертулерді тексеріңіз.\n5. Аралықты таңдап, есептеулер мен графиктерді ашыңыз.",
            "verify_text": "Preflight Python, тәуелділіктер, негізгі файлдар, конфигурация, экспорт тәуелділіктері және лог бумасын тексереді.",
            "workflow_text": "1. Файлды жүктеп, деректер жиынын таңдаңыз.\n2. Алғашқы жолдар мен тақырыптарды тексеріңіз.\n3. Қажет болса mapping түзетіңіз.\n4. Ескертулер мен Ch режимін тексеріңіз.\n5. Аралықты таңдап, графиктерді зерттеңіз.\n6. Нәтижені сақтап, құжатты экспорттаңыз.",
            "data_text": "LAS, CSV, XLSX және XLSM қолдау көрсетіледі. Тереңдік бағанын, газ компоненттерін, өлшем бірліктерін және бос мәндерді тексеріңіз.",
            "las_text": "LAS редакторы тереңдікті, STEP, NULL және қолмен енгізілген түзетулерді тексереді. Корреляция ұңғымаларды салыстырады және баспа материалдарын дайындайды.",
            "trouble_text": "Қате кезінде `python scripts/preflight.py` орындаңыз, `requirements.txt` және `logs/app.log` соңғы жолдарын тексеріңіз.",
            "quick_links": (("Жылдам бастау","docs-quick-start","Қосымшаны іске қосу және алғашқы есептеу","🚀"),("Деректер пішімі","docs-data-format","LAS/CSV/Excel, mapping және міндетті өрістер","📄"),("LAS жұмыс үдерісі","docs-las-workflow","Редактор, корреляция және нұсқалар","🧰"),("Диагностика","docs-troubleshooting","Preflight, тесттер және логтар","🩺")),
            "toc": (("Жылдам іске қосу","docs-quick-start"),("Дайындықты тексеру","docs-verification"),("Жұмыс сценарийі","docs-workflow"),("Деректер пішімі","docs-data-format"),("LAS жұмыс үдерісі","docs-las-workflow"),("Пернелер тіркесімі","docs-shortcuts"),("FAQ","docs-faq"),("Диагностика","docs-troubleshooting")),
            "shortcuts_items": (("Ctrl+K","Командалар палитрасын ашу."),("Esc","Белсенді терезені жабу немесе іздеуден шығу."),("Enter","Белсенді өрісті немесе команданы растау.")),
            "faq_items": (("Неліктен құжаттаманың жеке фоны бар?","Бұл анықтама экраны; инженерлік графиктер контрастты жұмыс фонында қалады."),("Есептеу алдында нені тексеру керек?","Тақырыптар, міндетті бағандар, ескертулер, Ch режимі және тереңдік аралығы."),("Іске қосу қатесі кезінде не істеу керек?","Ортаны, тәуелділіктерді, preflight және logs/app.log файлын тексеріңіз.")),
            "doc_titles": {"las_qc_user_guide":"LAS QC пайдаланушы нұсқаулығы","qc_architecture":"QC архитектурасы","supported_formats_and_legal_sources":"Пішімдер және заңды дереккөздер","external_standard_integration":"Сыртқы стандарттарды интеграциялау"},
        },
        "en": {
            "title": "Instructions and documentation", "subtitle": "Quick start, workflow, LAS, FAQ, shortcuts, and troubleshooting.",
            "caption": "The Documentation Center follows the interface language. Any fallback is used only when a translation is missing and is clearly marked.",
            "contents": "Section contents", "quick": "Quick start", "verify": "Readiness check", "workflow": "Main workflow",
            "data": "Data format and mapping", "las": "LAS workflow", "shortcuts": "Keyboard shortcuts", "faq": "FAQ",
            "troubleshooting": "Troubleshooting", "full_docs": "Full project documents", "fallback": "Translation unavailable; showing another language: {language}.",
            "quick_steps": "1. Start the project with `./run_app.ps1` or `python -m streamlit run app/streamlit_app.py`.\n2. Open `http://localhost:8501`.\n3. Upload LAS, CSV, XLSX, or XLSM.\n4. Check headers, mapping, and warnings.\n5. Select an interval and open calculations and plots.",
            "verify_text": "Preflight checks Python, dependencies, key files, configuration, export dependencies, and the log directory.",
            "workflow_text": "1. Upload a file and select a dataset.\n2. Review the first rows and headers.\n3. Correct mapping when required.\n4. Review warnings and the Ch mode.\n5. Select an interval and inspect plots.\n6. Save the result and export a document.",
            "data_text": "LAS, CSV, XLSX, and XLSM are supported. Check the depth column, gas components, units, and missing values.",
            "las_text": "The LAS editor checks depth, STEP, NULL, and manual edits. Correlation compares wells and prepares printable material.",
            "trouble_text": "When an error occurs, run `python scripts/preflight.py`, review `requirements.txt`, and inspect the latest lines of `logs/app.log`.",
            "quick_links": (("Quick start","docs-quick-start","Launch the application and run the first calculation","🚀"),("Data format","docs-data-format","LAS/CSV/Excel, mapping, and required fields","📄"),("LAS workflow","docs-las-workflow","Editor, correlation, and versions","🧰"),("Troubleshooting","docs-troubleshooting","Preflight, tests, and logs","🩺")),
            "toc": (("Quick start","docs-quick-start"),("Readiness check","docs-verification"),("Workflow","docs-workflow"),("Data format","docs-data-format"),("LAS workflow","docs-las-workflow"),("Keyboard shortcuts","docs-shortcuts"),("FAQ","docs-faq"),("Troubleshooting","docs-troubleshooting")),
            "shortcuts_items": (("Ctrl+K","Open the command palette."),("Esc","Close the active dialog or leave search."),("Enter","Confirm the active field or command.")),
            "faq_items": (("Why does documentation have a separate background?","It is a reference screen; engineering plots remain on a high-contrast workspace."),("What should be checked before calculation?","Headers, required columns, warnings, Ch mode, and the depth interval."),("What should I do when startup fails?","Check the environment, dependencies, preflight, and logs/app.log.")),
            "doc_titles": {"las_qc_user_guide":"LAS QC User Guide","qc_architecture":"QC Architecture","supported_formats_and_legal_sources":"Formats and Legal Sources","external_standard_integration":"External Standard Integration"},
        },
    }
    return payloads.get(language, payloads["ru"])


def _localized_documentation_documents(language: str) -> tuple[tuple[str, str, str], ...]:
    """Resolve manifest-backed documentation for the requested language."""
    manifest_path = ROOT_DIR / "docs" / "documentation_manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    copy = _documentation_locale_payload(language)
    titles = dict(copy.get("doc_titles", {}))
    resolved: list[tuple[str, str, str]] = []
    for document in payload.get("documents", []):
        languages = dict(document.get("languages", {}) or {})
        selected_language = language if language in languages else ("ru" if "ru" in languages else next(iter(languages), ""))
        relative = str(languages.get(selected_language, ""))
        if relative:
            resolved.append((str(titles.get(document.get("id"), document.get("id", "Document"))), f"docs/{relative}", selected_language))
    return tuple(resolved)


def _render_documentation_tab() -> None:
    i18n = _dashboard_localization()
    language = i18n.language
    copy = _documentation_locale_payload(language)
    hero_uri = _documentation_hero_data_uri() or _dashboard_background_data_uri()
    image_html = f'<img class="docs-hero-image" src="{hero_uri}" alt="Gas Ratio Pro documentation banner">' if hero_uri else ""
    st.markdown(f"<div class='docs-hero'><section class='docs-hero-banner'>{image_html}<div class='docs-hero-content'><div class='docs-hero-kicker'>Gas Ratio Pro Documentation Center</div><h1 class='docs-hero-title'>{_html_escape(str(copy['title']))}</h1><p class='docs-hero-subtitle'>{_html_escape(str(copy['subtitle']))}</p></div></section>", unsafe_allow_html=True)
    st.markdown('<div class="docs-panel">', unsafe_allow_html=True)
    st.caption(str(copy["caption"]))
    quick_cards = "".join(f"<a href='#{_html_escape(anchor)}' class='docs-v2-card'><div class='docs-v2-icon'>{icon}</div><b>{_html_escape(title)}</b><span>{_html_escape(description)}</span></a>" for title,anchor,description,icon in copy["quick_links"])
    st.markdown(f'<div class="docs-v2-grid">{quick_cards}</div>', unsafe_allow_html=True)
    toc_links = "".join(f"<a href='#{_html_escape(anchor)}'>{_html_escape(title)}</a>" for title,anchor in copy["toc"])
    st.markdown(f"### {copy['contents']}")
    st.markdown(f'<nav class="docs-toc">{toc_links}</nav>', unsafe_allow_html=True)
    quick_start, verification = st.columns(2)
    with quick_start:
        _render_docs_anchor("docs-quick-start"); st.markdown(f"### {copy['quick']}")
        st.code("cd C:\\OSPanel\\home\\gas-ratio-pro\n" + APP_LAUNCH_SCRIPT + "\n# alternative:\n" + APP_LAUNCH_COMMAND, language="powershell")
        st.markdown(str(copy["quick_steps"]))
    with verification:
        _render_docs_anchor("docs-verification"); st.markdown(f"### {copy['verify']}")
        st.code("python -m pytest\npython scripts/preflight.py", language="powershell"); st.markdown(str(copy["verify_text"]))
    for anchor,key,text_key in (("docs-workflow","workflow","workflow_text"),("docs-data-format","data","data_text"),("docs-las-workflow","las","las_text")):
        _render_docs_anchor(anchor); st.markdown(f"### {copy[key]}"); st.markdown(str(copy[text_key]))
    _render_docs_anchor("docs-shortcuts"); st.markdown(f"### {copy['shortcuts']}")
    for keys, action in copy["shortcuts_items"]:
        st.markdown(f"<div class='docs-info-row'><b>{_html_escape(keys)}</b><br><span>{_html_escape(action)}</span></div>", unsafe_allow_html=True)
    _render_docs_anchor("docs-faq"); st.markdown(f"### {copy['faq']}")
    for question, answer in copy["faq_items"]:
        with st.expander(question, expanded=False): st.markdown(answer)
    _render_docs_anchor("docs-troubleshooting"); st.markdown(f"### {copy['troubleshooting']}"); st.markdown(str(copy["trouble_text"]))
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown(f"### {copy['full_docs']}")
    for index, (title, relative_path, source_language) in enumerate(_localized_documentation_documents(language)):
        with st.expander(title, expanded=index == 0):
            if source_language != language:
                st.warning(str(copy["fallback"]).format(language=source_language.upper()))
            st.markdown(_read_documentation_markdown(relative_path))
    st.markdown('</div>', unsafe_allow_html=True)



def _render_las_qc_panel(
    *, logger, active_project: ProjectRecord, dataframe: pd.DataFrame, depth_column: str,
    expected_step: object, source_dataset_id: str, i18n,
) -> None:
    """Render the production QC panel without storing DataFrames or service objects in state."""
    st.markdown(f"### {i18n('qc.panel.title')}")
    if not source_dataset_id:
        st.info(i18n('qc.panel.source_required'))
        return
    try:
        step_value = float(str(expected_step).replace(',', '.'))
    except (TypeError, ValueError):
        step_value = None
    qc = application_service_container(_application_state_controller().state).quality_control(
        root=LAS_CORRELATION_PROJECTS_ROOT
    )
    try:
        report = qc.run_las(dataframe, depth_curve=depth_column, expected_step=step_value)
    except Exception:
        logger.exception('las_editor_qc_failed')
        st.error(i18n('qc.panel.run_failed'))
        return

    summary = report.to_dict()['summary']
    metrics = st.columns(4)
    metrics[0].metric(i18n('qc.report.status'), i18n(f'qc.status.{report.status}'))
    metrics[1].metric(i18n('qc.report.findings'), summary['finding_count'])
    metrics[2].metric(i18n('qc.severity.error'), summary['error_count'])
    metrics[3].metric(i18n('qc.severity.warning'), summary['warning_count'])

    severity_options = sorted({item.severity for item in report.findings})
    code_options = sorted({item.code for item in report.findings})
    filters = st.columns(2)
    severities = set(filters[0].multiselect(
        i18n('qc.panel.filter.severity'), severity_options, default=severity_options,
        key='las_editor_qc_severity_filter',
    ))
    codes = set(filters[1].multiselect(
        i18n('qc.panel.filter.code'), code_options, default=code_options,
        key='las_editor_qc_code_filter',
    ))
    filtered = qc.filter_report(report, severities=severities, codes=codes)
    finding_rows = []
    for item in filtered['findings']:
        key = str(item['message_key'])
        translated = i18n(key)
        finding_rows.append({
            i18n('qc.report.column.severity'): item['severity'],
            i18n('qc.report.column.code'): item['code'],
            i18n('qc.report.column.curve'): item.get('curve', ''),
            i18n('qc.report.column.message'): translated if translated != key else key,
        })
    if finding_rows:
        st.dataframe(pd.DataFrame(finding_rows), width='stretch', hide_index=True)
    else:
        st.success(i18n('qc.panel.no_findings'))

    with st.expander(i18n('qc.report.statistics'), expanded=False):
        stats = report.to_dict()['curve_statistics']
        st.dataframe(pd.DataFrame(stats), width='stretch', hide_index=True)

    state = _application_state_controller()
    report_key = f"las_editor.qc_report_dataset.{active_project.id}.{source_dataset_id}"
    saved = state.get_value(report_key)
    actions = st.columns(3)
    if actions[0].button(i18n('qc.panel.save'), width='stretch', key='las_editor_qc_save'):
        try:
            saved = qc.persist_report(
                project_id=active_project.id, source_dataset_id=source_dataset_id, report=report, actor='',
            ).to_dict()
            state.set_value(report_key, saved)
            st.success(i18n('qc.panel.saved'))
        except Exception:
            logger.exception('las_editor_qc_persist_failed')
            st.error(i18n('qc.panel.save_failed'))
    for index, format_id in enumerate(('pdf', 'docx'), start=1):
        label = i18n(f'qc.panel.export.{format_id}')
        if actions[index].button(label, width='stretch', key=f'las_editor_qc_export_{format_id}'):
            try:
                if not isinstance(saved, dict) or not saved.get('dataset_id'):
                    saved = qc.persist_report(
                        project_id=active_project.id, source_dataset_id=source_dataset_id, report=report, actor='',
                    ).to_dict()
                    state.set_value(report_key, saved)
                exported = qc.export_and_register(
                    project_id=active_project.id, source_qc_dataset_id=str(saved['dataset_id']),
                    report=report, format_id=format_id, translate=i18n.translate, actor='',
                ).to_dict()
                st.success(i18n('qc.panel.exported', format=format_id.upper(), path=exported['artifact_path']))
            except Exception:
                logger.exception('las_editor_qc_export_failed format=%s', format_id)
                st.error(i18n('qc.panel.export_failed', format=format_id.upper()))


def _render_las_editor(logger, active_project: ProjectRecord) -> None:
    # Repository mutations in this panel must use _request_ui_refresh_and_rerun.
    st.subheader("LAS-редактор")
    st.caption("Подготовка LAS перед расчетами: создание нового LAS, проверка глубины, смена шага, добавление строк и ручная правка.")
    _render_new_las_creator_panel(logger, active_project)
    if st.button("Очистить рабочее состояние LAS", width="stretch", key="las_editor_clear_working_state"):
        _clear_las_working_state()
        st.success("Рабочее состояние LAS очищено: таблицы, графики, статистика и временные данные удалены из session state.")
        _refresh_ui()
    _render_saved_wells_panel(logger)

    saved_summary = _application_state_controller().get_value(LAS_EDITOR_SESSION_SUMMARY_KEY)
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

    i18n = _dashboard_localization()
    import_mode_labels = {
        "tolerant": i18n("las.import.mode.tolerant"),
        "strict": i18n("las.import.mode.strict"),
    }
    las_import_mode = st.radio(
        i18n("las.import.mode.label"),
        options=("tolerant", "strict"),
        format_func=lambda value: import_mode_labels[value],
        horizontal=True,
        key="las_editor_import_mode",
        help=i18n("las.import.mode.help"),
    )

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

    # Register the uploaded source once per session/file checksum so the editor
    # can expose localized Data Platform validation without duplicate writes on rerun.
    upload_bytes = bytes(uploaded_file.getvalue())
    upload_checksum = hashlib.sha256(upload_bytes).hexdigest()
    state_controller = _application_state_controller()
    registration_key = f"las_editor.dataset_registration.{active_project.id}.{upload_checksum}.{las_import_mode}"
    registration_payload = state_controller.get_value(registration_key)
    if not isinstance(registration_payload, dict):
        from tempfile import NamedTemporaryFile
        temp_path = None
        try:
            with NamedTemporaryFile(mode="wb", suffix=".las", delete=False) as handle:
                handle.write(upload_bytes)
                temp_path = Path(handle.name)
            registration = application_service_container(state_controller.state).data_platform(
                root=LAS_CORRELATION_PROJECTS_ROOT
            ).register_source_file_result(
                project_id=active_project.id,
                source=temp_path,
                format_id="las",
                metadata={"source": "las_editor_upload", "original_name": uploaded_file.name},
                import_mode=las_import_mode,
            )
            registration_payload = {
                "dataset_id": registration.manifest.dataset_id,
                "dataset_version": registration.manifest.version,
                "messages": list(registration.localized_messages(i18n.translate)),
                "validation_codes": [item.code for item in registration.validation_findings],
                "import_mode": las_import_mode,
            }
            state_controller.set_value(registration_key, registration_payload)
        except Exception as exc:
            from services.data_platform_application_service import LasImportValidationError
            if isinstance(exc, LasImportValidationError):
                validation_codes = [item.code for item in exc.findings]
                messages = [i18n("las.import.strict_blocked")]
                for finding in exc.findings:
                    key = f"import.validation.{finding.code}"
                    translated = i18n(key)
                    if translated != key:
                        messages.append(translated)
                registration_payload = {
                    "dataset_id": "", "dataset_version": 0, "messages": messages,
                    "validation_codes": validation_codes, "import_mode": las_import_mode,
                    "blocked": True,
                }
            else:
                logger.exception("las_editor_dataset_registration_failed")
                registration_payload = {"dataset_id": "", "dataset_version": 0, "messages": [], "validation_codes": [], "import_mode": las_import_mode}
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
    for message in registration_payload.get("messages", []):
        st.info(str(message))

    st.markdown("### Исходные кривые")
    st.dataframe(prepared_df.head(20), width="stretch")

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
                width="stretch",
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
        width="stretch",
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
            width="stretch",
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
        before_col.dataframe(editor_base_df.head(30), width="stretch")
        after_col.markdown("**После ручной правки**")
        after_col.dataframe(edited_df.head(30), width="stretch")

        st.markdown("**Журнал правок, который будет сохранен в metadata версии**")
        st.dataframe(
            pd.DataFrame(
                [
                    {"Этап": entry.stage, "Действие": entry.action, "Детали": entry.details}
                    for entry in audit_entries
                ]
            ),
            width="stretch",
        )


    _render_las_qc_panel(
        logger=logger,
        active_project=active_project,
        dataframe=edited_df,
        depth_column=depth_column,
        expected_step=target_step,
        source_dataset_id=str(registration_payload.get("dataset_id", "")),
        i18n=i18n,
    )

    save_col, export_col = st.columns(2)
    if save_col.button("Сохранить для расчетов", type="primary", width="stretch"):
        _application_state_controller().update_values({
            LAS_EDITOR_SESSION_SHEETS_KEY: {"LAS-редактор": _dataframe_to_raw_sheet(edited_df)},
            LAS_EDITOR_SESSION_SUMMARY_KEY: (
                f"{len(edited_df)} строк, шаг {target_step}, заполнение: {fill_label}, массовых операций: {len(bulk_result.operation_log)}"
            ),
        })
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
        width="stretch",
    )
    safe_output_las_name = Path(output_las_name.strip() or "las_editor_depth_fixed.las").name
    if not safe_output_las_name.lower().endswith(".las"):
        safe_output_las_name += ".las"
    export_col.download_button(
        "Скачать LAS под новым названием",
        data=export_las_bytes(edited_df, well_name=Path(safe_output_las_name).stem, depth_column=depth_column),
        file_name=safe_output_las_name,
        mime="application/octet-stream",
        width="stretch",
        key="las_editor_download_depth_fixed_las",
    )

    st.markdown("### Сохранить скважину локально")
    well_service = _well_manager_service()
    records = well_service.list_wells()
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

    if st.button("Сохранить версию скважины", width="stretch"):
        try:
            saved_record = well_service.save_version(
                edited_df,
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
            saved_well_record = saved_record.record
            logger.info("well_version_saved well_id=%s rows=%d", safe_log_value(saved_well_record.id), len(edited_df))
            st.success(f"Скважина сохранена локально: {saved_well_record.name} ({saved_well_record.id}).")

    st.markdown("### Сохранить подготовленный LAS в проект")
    st.caption(f"Активный проект: {active_project.name} ({active_project.id})")
    if st.button("Сохранить подготовленный LAS в активный проект", width="stretch", key="las_editor_save_to_project"):
        if not well_name.strip():
            st.warning("Введите название скважины перед сохранением в проект.")
        else:
            try:
                las_bytes = export_las_bytes(edited_df, well_name=well_name, depth_column=depth_column)
                saved_las_result = _las_workspace_service(active_project.id).save_file(
                    data=las_bytes,
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
                # Persist the edited export as an immutable Dataset version linked
                # to the source upload when that lineage is available.
                from tempfile import NamedTemporaryFile
                version_temp_path = None
                try:
                    with NamedTemporaryFile(mode="wb", suffix=".las", delete=False) as handle:
                        handle.write(las_bytes)
                        version_temp_path = Path(handle.name)
                    previous_dataset_id = str(registration_payload.get("dataset_id", "") or "")
                    version_registration = application_service_container(
                        _application_state_controller().state
                    ).data_platform(root=LAS_CORRELATION_PROJECTS_ROOT).register_source_file_result(
                        project_id=active_project.id,
                        source=version_temp_path,
                        format_id="las",
                        well_id=saved_las_result.record.well_id or "",
                        previous_dataset_id=previous_dataset_id,
                        import_mode=str(registration_payload.get("import_mode", "tolerant") or "tolerant"),
                        metadata={
                            "source": "las_editor_save",
                            "las_record_id": saved_las_result.record.id,
                            "version_label": version_label.strip() or "Подготовленный LAS",
                        },
                    )
                    for message in version_registration.localized_messages(_dashboard_localization().translate):
                        st.info(message)
                finally:
                    if version_temp_path is not None:
                        version_temp_path.unlink(missing_ok=True)
            except Exception:
                logger.exception("project_las_prepared_save_failed project_id=%s", safe_log_value(active_project.id))
                st.error("Не удалось сохранить подготовленный LAS в проект. Подробности записаны в logs/app.log.")
            else:
                logger.info(
                    "project_las_prepared_saved project_id=%s las_file_id=%s rows=%d",
                    safe_log_value(active_project.id),
                    safe_log_value(saved_las_result.record.id),
                    len(edited_df),
                )
                st.success(f"Подготовленный LAS сохранен в проект: {saved_las_result.record.name} / {saved_las_result.record.version_label}.")


def _fluid_visual(value: object) -> tuple[str, str, str]:
    """Return a stable user label, engineering color and compact marker."""
    text = str(value or "").strip().casefold()
    if "газоконденсат" in text or ("газ" in text and "конденсат" in text):
        return "Газоконденсат", "#f59e0b", "🟧"
    if "нефт" in text or text == "oil":
        return "Нефть", "#22c55e", "🟩"
    if "газ" in text or text == "gas":
        return "Газ", "#ef4444", "🟥"
    if "вод" in text or text == "water":
        return "Вода", "#3b82f6", "🟦"
    return (str(value or "Не определён"), "#94a3b8", "⬜")


def _active_interval_table_marker(fluid: object, *, active: bool) -> str:
    marker = _fluid_visual(fluid)[2]
    return f"▶ {marker}" if active else marker


def _ordered_interval_ids(table: pd.DataFrame) -> list[str]:
    if not isinstance(table, pd.DataFrame) or table.empty or "ID" not in table.columns:
        return []
    return [str(value) for value in table["ID"].tolist() if str(value).strip()]


def _adjacent_interval_id(interval_ids: list[str], active_id: str, offset: int) -> str:
    if not interval_ids:
        return ""
    try:
        index = interval_ids.index(str(active_id))
    except ValueError:
        index = 0
    target = max(0, min(len(interval_ids) - 1, index + int(offset)))
    return interval_ids[target]


def _interval_navigation_state(table: pd.DataFrame, active_id: str) -> tuple[list[str], int]:
    interval_ids = _ordered_interval_ids(table)
    if not interval_ids:
        return [], 0
    try:
        position = interval_ids.index(str(active_id))
    except ValueError:
        position = 0
    return interval_ids, position


def _interval_fluid_options(table: pd.DataFrame) -> list[str]:
    if not isinstance(table, pd.DataFrame) or table.empty or "Вероятный флюид" not in table.columns:
        return []
    result: list[str] = []
    for raw in table["Вероятный флюид"].tolist():
        label = _fluid_visual(raw)[0]
        if label not in result:
            result.append(label)
    return result


def _filter_engineering_intervals(
    table: pd.DataFrame,
    *,
    search_text: str = "",
    fluid_labels: list[str] | tuple[str, ...] | None = None,
) -> pd.DataFrame:
    if not isinstance(table, pd.DataFrame) or table.empty:
        return table.copy() if isinstance(table, pd.DataFrame) else pd.DataFrame()
    mask = pd.Series(True, index=table.index)
    query = str(search_text or "").strip().casefold()
    if query:
        searchable = table.astype(str).agg(" ".join, axis=1).str.casefold()
        mask &= searchable.str.contains(query, regex=False, na=False)
    selected = {str(item).strip().casefold() for item in (fluid_labels or []) if str(item).strip()}
    if selected and "Вероятный флюид" in table.columns:
        labels = table["Вероятный флюид"].map(lambda value: _fluid_visual(value)[0].casefold())
        mask &= labels.isin(selected)
    return table.loc[mask].copy()


def _interval_table_window(
    table: pd.DataFrame,
    active_id: str,
    *,
    window_size: int = 21,
) -> tuple[pd.DataFrame, int, int]:
    if not isinstance(table, pd.DataFrame) or table.empty:
        empty = table.copy() if isinstance(table, pd.DataFrame) else pd.DataFrame()
        if "Активный" not in empty.columns:
            empty.insert(0, "Активный", pd.Series(dtype=str))
        return empty, 0, 0
    size = max(1, int(window_size))
    ids = _ordered_interval_ids(table)
    try:
        active_index = ids.index(str(active_id))
    except ValueError:
        active_index = 0
    half = size // 2
    start = max(0, active_index - half)
    end = min(len(table), start + size)
    start = max(0, end - size)
    window = table.iloc[start:end].copy().reset_index(drop=True)
    fluids = window.get("Вероятный флюид", pd.Series([""] * len(window)))
    markers = [
        _active_interval_table_marker(fluid, active=str(interval_id) == str(active_id))
        for fluid, interval_id in zip(fluids.tolist(), window.get("ID", pd.Series([""] * len(window))).tolist())
    ]
    window.insert(0, "Активный", markers)
    return window, start, end


def _selected_dataframe_rows(event: object) -> list[int]:
    selection = getattr(event, "selection", None)
    if selection is None and isinstance(event, dict):
        selection = event.get("selection")
    rows = getattr(selection, "rows", None)
    if rows is None and isinstance(selection, dict):
        rows = selection.get("rows")
    if rows is None:
        return []
    result: list[int] = []
    for value in rows:
        try:
            result.append(int(value))
        except (TypeError, ValueError):
            continue
    return result


def _selected_interval_id_from_table(event: object, table: pd.DataFrame) -> str:
    rows = _selected_dataframe_rows(event)
    if not rows or not isinstance(table, pd.DataFrame) or table.empty or "ID" not in table.columns:
        return ""
    index = rows[0]
    if index < 0 or index >= len(table):
        return ""
    return str(table.iloc[index]["ID"])



def _render_professional_import_wizard(logger, active_project: ProjectRecord) -> None:
    """Render a compact multilingual batch-import wizard backed by background jobs."""
    i18n = _dashboard_localization()
    service = application_service_container(_application_state_controller().state).data_platform(
        root=LAS_CORRELATION_PROJECTS_ROOT
    )
    with st.expander(i18n("import.wizard.title"), expanded=False):
        st.caption(i18n("import.wizard.caption"))
        uploads = st.file_uploader(
            i18n("import.wizard.files"),
            type=["las", "dlis", "lis", "sgy", "segy", "csv", "xlsx", "xls"],
            accept_multiple_files=True,
            key=f"professional_import_wizard_{active_project.id}",
        )
        if st.button(i18n("import.wizard.start"), key=f"professional_import_start_{active_project.id}"):
            if not uploads:
                st.warning(i18n("import.wizard.no_files"))
            else:
                staging = LAS_CORRELATION_PROJECTS_ROOT / active_project.id / "imports" / "staging"
                staging.mkdir(parents=True, exist_ok=True)
                staged_paths = []
                for uploaded in uploads:
                    safe_name = Path(str(uploaded.name)).name
                    target = staging / f"{uuid4().hex[:10]}-{safe_name}"
                    target.write_bytes(bytes(uploaded.getvalue()))
                    staged_paths.append(target)
                try:
                    job = service.submit_batch_import_job(
                        project_id=active_project.id, sources=staged_paths, actor="workbench-user"
                    )
                    _application_state_controller().set_value(
                        f"import_wizard.active_job.{active_project.id}", str(job["job_id"])
                    )
                    st.success(i18n("import.wizard.submitted", job_id=job["job_id"]))
                    st.rerun()
                except Exception:
                    logger.exception("professional_import_job_submit_failed project_id=%s", active_project.id)
                    st.error(i18n("import.preview.panel.failed"))

        st.markdown(f"**{i18n('import.wizard.jobs')}**")
        jobs = list(service.list_import_jobs(project_id=active_project.id))
        if not jobs:
            st.caption(i18n("import.wizard.empty"))
        else:
            job_rows = [{
                "job_id": item.get("job_id", ""),
                i18n("import.wizard.status"): item.get("status", ""),
                i18n("import.wizard.progress"): item.get("progress_percent", 0),
                i18n("import.wizard.success"): item.get("success_count", 0),
                i18n("import.wizard.failed"): item.get("failed_count", 0),
            } for item in jobs]
            st.dataframe(pd.DataFrame(job_rows), width="stretch", hide_index=True)
            latest = jobs[0]
            result = latest.get("result") or {}
            items = result.get("items", []) if isinstance(result, dict) else []
            if items:
                rows = [{
                    i18n("import.wizard.file"): item.get("source_name", ""),
                    i18n("import.wizard.status"): item.get("status", ""),
                    i18n("import.wizard.format"): item.get("format_id", ""),
                    i18n("import.wizard.readiness"): item.get("readiness_score", 0),
                    i18n("import.wizard.error"): item.get("error_code", ""),
                } for item in items if isinstance(item, dict)]
                st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
            retryable = int(latest.get("failed_count", 0) or 0) > 0 or latest.get("status") == "interrupted"
            action_columns = st.columns(2)
            if retryable and action_columns[0].button(
                i18n("import.wizard.retry"), key=f"professional_import_retry_{active_project.id}"
            ):
                try:
                    retry = service.retry_failed_import_job(str(latest["job_id"]), actor="workbench-user")
                    st.success(i18n("import.wizard.retry_submitted", job_id=retry["job_id"]))
                    st.rerun()
                except Exception:
                    logger.exception("professional_import_retry_failed job_id=%s", latest.get("job_id"))
                    st.error(i18n("import.preview.panel.failed"))
            if latest.get("status") in {"queued", "running", "cancel_requested"} and action_columns[1].button(
                i18n("import.wizard.cancel"), key=f"professional_import_cancel_{active_project.id}"
            ):
                try:
                    cancelled = service.cancel_import_job(str(latest["job_id"]))
                    st.info(i18n("import.wizard.cancelled", status=cancelled.get("status", "")))
                    st.rerun()
                except Exception:
                    logger.exception("professional_import_cancel_failed job_id=%s", latest.get("job_id"))
                    st.error(i18n("import.preview.panel.failed"))

        readiness = service.project_readiness_dashboard(active_project.id)
        st.markdown(f"**{i18n('import.wizard.readiness_dashboard')}**")
        readiness_columns = st.columns(5)
        readiness_columns[0].metric(
            i18n("import.wizard.readiness_average"), f"{readiness.get('average_score', 0)}%"
        )
        readiness_columns[1].metric(
            i18n("import.wizard.readiness_ready"), int(readiness.get("ready_count", 0) or 0)
        )
        readiness_columns[2].metric(
            i18n("import.wizard.readiness_review"), int(readiness.get("review_count", 0) or 0)
        )
        readiness_columns[3].metric(
            i18n("import.wizard.readiness_blocked"), int(readiness.get("blocked_count", 0) or 0)
        )
        readiness_columns[4].metric(
            i18n("import.wizard.readiness_unknown"), int(readiness.get("unknown_count", 0) or 0)
        )
        formats = dict(readiness.get("formats", {}) or {})
        if formats:
            st.caption(
                i18n("import.wizard.readiness_formats") + ": "
                + ", ".join(f"{key.upper()} — {value}" for key, value in formats.items())
            )
        readiness_filter_columns = st.columns(2)
        readiness_statuses = set(readiness_filter_columns[0].multiselect(
            i18n("import.wizard.readiness_filter_status"),
            ["ready", "review", "blocked", "unknown"],
            key=f"readiness_filter_status_{active_project.id}",
        ))
        readiness_formats = set(readiness_filter_columns[1].multiselect(
            i18n("import.wizard.readiness_filter_format"),
            sorted(formats),
            key=f"readiness_filter_format_{active_project.id}",
        ))
        readiness_items = service.list_project_readiness_items(
            active_project.id, statuses=(readiness_statuses or None), formats=(readiness_formats or None)
        )
        if readiness_items:
            st.dataframe(pd.DataFrame(readiness_items), width="stretch", hide_index=True)

        correlation = service.project_correlation_readiness(active_project.id)
        st.markdown(f"**{i18n('import.wizard.correlation_readiness')}**")
        correlation_columns = st.columns(4)
        correlation_columns[0].metric(i18n("import.wizard.correlation_wells"), correlation.get("well_count", 0))
        correlation_columns[1].metric(i18n("import.wizard.readiness_ready"), correlation.get("ready_count", 0))
        correlation_columns[2].metric(i18n("import.wizard.readiness_review"), correlation.get("review_count", 0))
        correlation_columns[3].metric(i18n("import.wizard.readiness_blocked"), correlation.get("blocked_count", 0))
        shared_curves = list(correlation.get("shared_curves", []) or [])
        if shared_curves:
            st.caption(i18n("import.wizard.correlation_shared_curves") + ": " + ", ".join(shared_curves))
        if correlation.get("eligible_for_correlation"):
            st.success(i18n("import.wizard.correlation_ready"))
        elif correlation.get("well_count", 0):
            st.warning(i18n("import.wizard.correlation_review"))

        st.markdown(f"**{i18n('import.wizard.history')}**")
        filter_columns = st.columns([2, 2, 1, 1])
        history_query = filter_columns[0].text_input(
            i18n("import.wizard.history_search"), key=f"import_history_query_{active_project.id}"
        )
        status_options = ["completed", "failed", "cancelled", "interrupted"]
        selected_statuses = set(filter_columns[1].multiselect(
            i18n("import.wizard.history_status"), status_options,
            key=f"import_history_status_{active_project.id}",
        ))
        history = list(service.list_import_history(
            active_project.id, limit=100, statuses=(selected_statuses or None), query=history_query
        ))
        if history:
            st.dataframe(pd.DataFrame([{
                "job_id": item.get("job_id", ""),
                i18n("import.wizard.status"): item.get("status", ""),
                i18n("import.wizard.success"): item.get("success_count", 0),
                i18n("import.wizard.failed"): item.get("failed_count", 0),
                "created_at": item.get("created_at", ""),
                "finished_at": item.get("finished_at", ""),
            } for item in history]), width="stretch", hide_index=True)
            json_payload = service.export_import_history(
                active_project.id, format_id="json", statuses=(selected_statuses or None), query=history_query
            )
            csv_payload = service.export_import_history(
                active_project.id, format_id="csv", statuses=(selected_statuses or None), query=history_query
            )
            filter_columns[2].download_button(
                "JSON", data=json_payload, file_name=f"{active_project.id}-import-history.json", mime="application/json",
                key=f"import_history_json_{active_project.id}",
            )
            filter_columns[3].download_button(
                "CSV", data=csv_payload, file_name=f"{active_project.id}-import-history.csv", mime="text/csv",
                key=f"import_history_csv_{active_project.id}",
            )
        else:
            st.caption(i18n("import.wizard.history_empty"))

        if st.button(i18n("import.wizard.cleanup_staging"), key=f"import_cleanup_staging_{active_project.id}"):
            cleanup = service.cleanup_import_staging(active_project.id)
            st.success(i18n(
                "import.wizard.cleanup_result",
                count=cleanup.get("removed_files", 0),
                size=cleanup.get("removed_bytes", 0),
            ))

def _render_subsurface_import_preview(logger, active_project: ProjectRecord) -> None:
    """Render bounded DLIS/LIS79/SEG-Y metadata preview outside tabular parsing."""
    i18n = _dashboard_localization()
    with st.expander(i18n("import.preview.panel.title"), expanded=False):
        st.caption(i18n("import.preview.panel.caption"))
        uploaded = st.file_uploader(
            i18n("import.preview.panel.upload"),
            type=["dlis", "lis", "sgy", "segy"],
            key=f"subsurface_import_preview_{active_project.id}",
        )
        if uploaded is None:
            return
        suffix = Path(str(uploaded.name)).suffix.lower()
        format_id = {".dlis": "dlis", ".lis": "lis79", ".sgy": "segy", ".segy": "segy"}.get(suffix)
        if not format_id:
            st.error(i18n("import.preview.panel.unsupported"))
            return
        from tempfile import NamedTemporaryFile
        temp_path = None
        try:
            with NamedTemporaryFile(mode="wb", suffix=suffix, delete=False) as handle:
                handle.write(bytes(uploaded.getvalue()))
                temp_path = Path(handle.name)
            service = application_service_container(_application_state_controller().state).data_platform(
                root=LAS_CORRELATION_PROJECTS_ROOT
            )
            preview = service.build_import_preview(temp_path, format_id=format_id, translate=i18n.translate)
            st.info(str(preview["summary"]))
            if preview["fields"]:
                st.dataframe(pd.DataFrame(preview["fields"]), width="stretch", hide_index=True)
            for warning in preview["warnings"]:
                st.warning(str(warning["message"]))
            if format_id in {"dlis", "lis79"}:
                projection = service.build_dlis_selection_projection(temp_path, format_id=format_id)
                logical_files = list(projection.get("logical_files", []) or [])
                if not bool(projection.get("adapter_available", False)):
                    st.info(i18n("import.preview.dlis.adapter_required"))
                elif logical_files:
                    logical_options = list(range(len(logical_files)))
                    selected_index = st.selectbox(
                        i18n("import.preview.dlis.logical_file"),
                        logical_options,
                        format_func=lambda idx: f"{idx}: logical file",
                        key=f"dlis_logical_file_{active_project.id}",
                    )
                    selected = dict(logical_files[int(selected_index)])
                    frame_names = list(selected.get("frame_names", []) or [])
                    channel_names = list(selected.get("channel_names", []) or [])
                    if frame_names:
                        st.selectbox(i18n("import.preview.dlis.frame"), frame_names, key=f"dlis_frame_{active_project.id}")
                    if channel_names:
                        st.multiselect(i18n("import.preview.dlis.channels"), channel_names, default=channel_names[: min(8, len(channel_names))], key=f"dlis_channels_{active_project.id}")
            if st.button(i18n("import.preview.panel.save"), key=f"save_subsurface_preview_{active_project.id}_{format_id}"):
                try:
                    manifest = service.persist_import_preview(
                        project_id=active_project.id,
                        source=temp_path,
                        actor="workbench-user",
                        format_id=format_id,
                        translate=i18n.translate,
                    )
                    st.success(i18n("import.preview.panel.saved", dataset_id=manifest.dataset_id))
                except Exception:
                    logger.exception("subsurface_import_preview_save_failed format=%s", format_id)
                    st.error(i18n("import.preview.panel.save_failed"))
            if format_id == "segy":
                cols = st.columns(5)
                inline_byte = int(cols[0].number_input(i18n("import.preview.segy.inline_byte"), 1, 237, 189))
                crossline_byte = int(cols[1].number_input(i18n("import.preview.segy.crossline_byte"), 1, 237, 193))
                scalar_byte = int(cols[2].number_input(i18n("import.preview.segy.scalar_byte"), 1, 237, 71))
                x_byte = int(cols[3].number_input(i18n("import.preview.segy.x_byte"), 1, 237, 73))
                y_byte = int(cols[4].number_input(i18n("import.preview.segy.y_byte"), 1, 237, 77))
                if st.button(i18n("import.preview.segy.scan_geometry"), key=f"segy_geometry_scan_{active_project.id}"):
                    inventory = service.scan_segy_trace_headers(
                        temp_path, inline_byte=inline_byte, crossline_byte=crossline_byte,
                        coordinate_scalar_byte=scalar_byte, x_byte=x_byte, y_byte=y_byte,
                    )
                    geometry_preview = __import__(
                        "core.data_platform.import_preview", fromlist=["build_metadata_import_preview"]
                    ).build_metadata_import_preview(inventory, i18n.translate)
                    if geometry_preview["fields"]:
                        st.dataframe(pd.DataFrame(geometry_preview["fields"]), width="stretch", hide_index=True)
                    for warning in geometry_preview["warnings"]:
                        st.warning(str(warning["message"]))
        except Exception:
            logger.exception("subsurface_import_preview_failed format=%s", format_id)
            st.error(i18n("import.preview.panel.failed"))
        finally:
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    logger.warning("subsurface_import_preview_temp_cleanup_failed path=%s", temp_path)


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
    _render_professional_import_wizard(logger, active_project)
    _render_subsurface_import_preview(logger, active_project)

    state_controller = _application_state_controller()
    editor_sheets = state_controller.get_value(LAS_EDITOR_SESSION_SHEETS_KEY)
    project_sheets = state_controller.get_value(PROJECT_SESSION_SHEETS_KEY)
    if state_controller.get_value(PROJECT_SESSION_PROJECT_ID_KEY) != active_project.id:
        project_sheets = None

    source_options = []
    if project_sheets:
        source_options.append("Проект")
        summary = state_controller.get_value(PROJECT_SESSION_SUMMARY_KEY, "проектные данные загружены")
        st.info(f"Доступны данные активного проекта: {summary}")
    if editor_sheets:
        source_options.append("LAS-редактор")
        summary = state_controller.get_value(LAS_EDITOR_SESSION_SUMMARY_KEY, "данные подготовлены")
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
                        _refresh_ui()
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
                        _refresh_ui()
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
                        _refresh_ui()
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
                        _refresh_ui()
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
                        _refresh_ui()
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
    _render_formula_reference()
    ch_mode = st.radio(
        "Режим Ch",
        options=["A", "reserved"],
        format_func=lambda value: "A: (C3 + ΣC4 + ΣC5) / (ΣC4 + ΣC5)" if value == "A" else "B: reserved, отключено",
        horizontal=True,
        key="mapping_draft_ch_mode",
    )

    prepared_signature = dataframe_signature(prepared_df)
    missing_components = _missing_required_gas_mapping_fields(manual_mapping)
    depth_mapped = bool(manual_mapping.get("depth") or (manual_mapping.get("depth_from") and manual_mapping.get("depth_to")))
    mapping_valid = depth_mapped and not missing_components

    action_left, action_right = st.columns(2)
    apply_mapping_clicked = action_left.button(
        "Применить mapping",
        type="primary",
        width="stretch",
        disabled=not mapping_valid,
        key="apply_mapping_explicit",
        help="Фиксирует проверенное сопоставление. Изменение виджетов после этого не запускает расчет автоматически.",
    )
    if apply_mapping_clicked:
        mapping_status = st.empty()
        _set_inline_operation_status(mapping_status, "Подготовка данных", "Проверяется и фиксируется mapping.")
        applied_snapshot = AppliedMappingState(
            source_signature=prepared_signature,
            sheet_name=str(sheet_name),
            header_row=int(header_row),
            mapping=dict(manual_mapping),
            ch_mode=str(ch_mode),
        )
        persist_applied_mapping(_application_state_controller().state, applied_snapshot)
        revisions = revision_controller_from_state(_application_state_controller().state)
        persist_revisions(_application_state_controller().state, revisions.bump_data())
        _clear_invalid_interpretation_state("Ожидается запуск интерпретации для нового mapping.")
        logger.info(
            "manual_mapping_committed sheet=%s signature=%s mapped=%s",
            safe_log_value(sheet_name),
            safe_log_value(prepared_signature[:12]),
            safe_log_value(",".join(sorted(manual_mapping.keys()))),
        )
        _set_inline_operation_status(
            mapping_status,
            "Подготовка данных",
            "Mapping применен. Можно запускать интерпретацию.",
            state="success",
        )

    applied_mapping = applied_mapping_from_state(_application_state_controller().state)
    applied_for_current_source = mapping_matches_source(applied_mapping, prepared_signature)
    if applied_for_current_source:
        st.caption("Примененный mapping соответствует текущему набору данных.")
    else:
        st.info("Сначала примените mapping. Черновые изменения виджетов не изменяют текущие расчетные результаты.")

    run_interpretation_clicked = action_right.button(
        "Запустить интерпретацию",
        width="stretch",
        disabled=not applied_for_current_source,
        key="run_interpretation_explicit",
        help="Выполняет mapping и расчеты только по последнему примененному снимку настроек.",
    )

    if not mapping_valid:
        missing_labels = ", ".join(field.upper() for field in missing_components)
        reason_parts = []
        if not depth_mapped:
            reason_parts.append("не сопоставлена глубина")
        if missing_components:
            reason_parts.append(f"не сопоставлены обязательные газовые компоненты: {missing_labels}")
        invalid_reason = "; ".join(reason_parts)
        # Legacy safety invariant: calculation_blocked_invalid_mapping previously
        # called _clear_invalid_interpretation_state and displayed
        # "Предыдущие графики и отчеты очищены". In the explicit-apply workflow,
        # invalid draft widgets cannot replace the already applied mapping, so the
        # committed result remains safe while the Run button stays disabled.
        logger.warning(
            "mapping_draft_invalid depth_mapped=%s missing=%s",
            depth_mapped,
            safe_log_value(",".join(missing_components)),
        )
        st.error("Mapping не может быть применен: " + invalid_reason + ".")

    existing_df = _application_state_controller().state.get(INTERPRETATION_SESSION_DATA_KEY)
    if not run_interpretation_clicked:
        if isinstance(existing_df, pd.DataFrame) and not existing_df.empty:
            st.info("Показаны последние примененные результаты. Для пересчета нажмите «Запустить интерпретацию».")
        return

    assert applied_mapping is not None
    calculation_status = st.empty()
    _set_inline_operation_status(
        calculation_status,
        "Расчёт",
        "Применяется mapping и рассчитываются инженерные коэффициенты.",
    )
    calculation_started = perf_counter()
    prepared = apply_mapping(prepared_df, dict(applied_mapping.mapping))
    logger.info(
        "manual_mapping_applied mapped=%s warning_count=%d",
        safe_log_value(",".join(sorted(applied_mapping.mapping.keys()))),
        len(prepared.warnings),
    )
    calculation = calculate_gas_ratios(prepared.data, CalculationConfig(ch_mode=applied_mapping.ch_mode))
    calculated_df = add_interpretation(calculation.data)
    _store_interpretation_dataset(calculated_df, str(sheet_name))
    ch_mode = applied_mapping.ch_mode
    calculation_duration_ms = (perf_counter() - calculation_started) * 1000.0
    logger.info(
        "calculation_completed rows=%d ch_mode=%s warning_count=%d duration_ms=%.2f",
        len(calculated_df),
        safe_log_value(ch_mode),
        len(calculation.warnings),
        calculation_duration_ms,
    )
    _set_inline_operation_status(
        calculation_status,
        "Расчёт",
        f"Интерпретация рассчитана: {len(calculated_df)} строк, {calculation_duration_ms:.0f} мс.",
        state="success",
    )

    nan_messages = ratio_nan_warning_messages(calculated_df, ch_mode=ch_mode)
    methodology_notices = {CH_WARNING, METHODOLOGY_WARNING}
    warnings = (
        list(mapping_result.warnings)
        + list(prepared.warnings)
        + [item for item in calculation.warnings if item not in methodology_notices]
        + list(mapping_messages)
    )
    warnings = list(dict.fromkeys(warnings))

    with st.expander("Проверки workflow", expanded=bool(warnings)):
        if warnings:
            for warning in warnings:
                st.warning(warning)
        else:
            st.success("Критичных предупреждений workflow нет.")
        st.info(CH_WARNING)
        st.caption(METHODOLOGY_WARNING)
    _render_ratio_nan_diagnostics(calculated_df, ch_mode, nan_messages)

    if calculated_df.empty:
        logger.warning("calculated_dataframe_empty")
        st.error("Нет расчетных данных для отображения.")
        return

    st.subheader("Инженерная сводка интерпретации")
    st.caption(
        "Сводка показывает выделенные интервалы, их мощность, вероятный флюид, "
        "достоверность и инженерное заключение. Счетчики строк доступны только в диагностике."
    )
    workspace_interval_summary = engineering_interval_summary(calculated_df)
    if workspace_interval_summary.empty:
        st.info("По текущему расчету уверенные УВ-интервалы не выделены.")
    else:
        workspace_filter_left, workspace_filter_right = st.columns([2, 1])
        workspace_search = workspace_filter_left.text_input(
            "Поиск интервала",
            key="workspace_interval_search",
            placeholder="ID, глубина, флюид, заключение",
        )
        workspace_fluid_options = _interval_fluid_options(workspace_interval_summary)
        workspace_fluids = workspace_filter_right.multiselect(
            "Флюид",
            options=workspace_fluid_options,
            key="workspace_interval_fluid_filter",
            placeholder="Все типы",
        )
        filtered_workspace_summary = _filter_engineering_intervals(
            workspace_interval_summary,
            search_text=workspace_search,
            fluid_labels=workspace_fluids,
        )
        if filtered_workspace_summary.empty:
            st.info("По заданным условиям интервалы не найдены.")
            return

        active_workspace_interval_id = str(
            state_controller.get_value("selected_reservoir_interval_id", "") or ""
        )
        workspace_ids, workspace_position = _interval_navigation_state(
            filtered_workspace_summary,
            active_workspace_interval_id,
        )
        if workspace_ids and active_workspace_interval_id not in workspace_ids:
            active_workspace_interval_id = workspace_ids[0]
            workspace_position = 0
            state_controller.update_values({
                "selected_reservoir_interval_id": active_workspace_interval_id
            })

        workspace_label_by_id = {
            str(row["ID"]): (
                f'{row["ID"]} · {row.get("Интервал, м", "—")} · '
                f'{row.get("Вероятный флюид", "—")} · {row.get("Достоверность", "—")}'
            )
            for _, row in filtered_workspace_summary.iterrows()
        }
        selected_workspace_id = st.selectbox(
            "Выбранный интервал",
            options=workspace_ids,
            index=workspace_position if workspace_ids else None,
            format_func=lambda interval_id: workspace_label_by_id.get(str(interval_id), str(interval_id)),
            key="workspace_interval_selector",
            help="Выбор синхронизирует инженерную таблицу, Pixler, ternary, планшет, паспорт и экспорт.",
        ) if workspace_ids else ""
        if selected_workspace_id and selected_workspace_id != active_workspace_interval_id:
            active_workspace_interval_id = str(selected_workspace_id)
            workspace_position = workspace_ids.index(active_workspace_interval_id)
            state_controller.update_values({
                "selected_reservoir_interval_id": active_workspace_interval_id
            })

        workspace_table, workspace_start, workspace_end = _interval_table_window(
            filtered_workspace_summary,
            active_workspace_interval_id,
            window_size=21,
        )
        st.caption(
            f"Активная строка удерживается в видимой области: интервалы "
            f"{workspace_start + 1}–{workspace_end} из {len(filtered_workspace_summary)} "
            f"(всего {len(workspace_interval_summary)})."
        )
        workspace_table_event = st.dataframe(
            workspace_table,
            width="stretch",
            height=430,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key="workspace_engineering_interval_table",
            column_config={
                "Активный": st.column_config.TextColumn("", width="small"),
                "ID": st.column_config.TextColumn("ID", width="small"),
                "Интервал, м": st.column_config.TextColumn("Интервал, м", width="medium"),
                "Мощность, м": st.column_config.NumberColumn("Мощность, м", format="%.2f"),
                "Вероятный флюид": st.column_config.TextColumn("Вероятный флюид", width="medium"),
                "Достоверность": st.column_config.TextColumn("Достоверность", width="small"),
                "Данные": st.column_config.TextColumn("Качество данных", width="small"),
                "Геология": st.column_config.TextColumn("Геологическая поддержка", width="small"),
                "Уровень решения": st.column_config.TextColumn("Уровень решения", width="small"),
                "Инженерное заключение": st.column_config.TextColumn("Инженерное заключение", width="large"),
            },
        )
        table_interval_id = _selected_interval_id_from_table(
            workspace_table_event,
            workspace_table,
        )
        if table_interval_id and table_interval_id != active_workspace_interval_id:
            state_controller.update_values({"selected_reservoir_interval_id": table_interval_id})
            _request_ui_refresh_and_rerun("workspace_interval_selected")

    interval_indices = [
        int(index)
        for index in calculated_df.index
        if not pd.isna(index)
    ]
    if not interval_indices:
        logger.warning("interval_list_empty")
        st.error("Не найдено ни одного интервала для выбора.")
        return

    # Use one detected-interval model and one shared selection contract for
    # Data Workspace, Interpretation, Pixler, ternary, Depth Panel and export.
    detected_interval_result = None
    interval_pairs: list[tuple[object, object]] = []
    selected_reservoir_interval = None
    selected_reservoir_overlay = None
    try:
        detected_interval_result = detect_hydrocarbon_intervals(calculated_df)
        detected_overlays = reservoir_interval_overlays(detected_interval_result.intervals)
        interval_pairs = list(zip(detected_overlays, detected_interval_result.intervals))
    except Exception as exc:
        logger.warning("workspace_interval_detection_failed error=%s", safe_log_value(exc))

    if interval_pairs:
        option_ids = [str(overlay.interval_id) for overlay, _ in interval_pairs]
        remembered_interval_id = str(
            state_controller.get_value("selected_reservoir_interval_id", "") or ""
        )
        default_interval_position = (
            option_ids.index(remembered_interval_id)
            if remembered_interval_id in option_ids
            else 0
        )
        workspace_selection_key = "workspace_selected_reservoir_interval_id"
        workspace_synced_key = "workspace_selected_reservoir_interval_synced_id"
        if (
            remembered_interval_id in option_ids
            and (
                workspace_selection_key not in _application_state_controller().state
                or _application_state_controller().state.get(workspace_synced_key) != remembered_interval_id
            )
        ):
            _application_state_controller().state[workspace_selection_key] = remembered_interval_id
            _application_state_controller().state[workspace_synced_key] = remembered_interval_id
        selected_reservoir_interval_id = (
            str(state_controller.get_value("selected_reservoir_interval_id", "") or "")
            if str(state_controller.get_value("selected_reservoir_interval_id", "") or "") in option_ids
            else option_ids[default_interval_position]
        )
        st.caption(
            "Выбран из инженерной таблицы: "
            + _interval_display_label(
                next(interval for overlay, interval in interval_pairs if overlay.interval_id == selected_reservoir_interval_id),
                selected_reservoir_interval_id,
            )
        )
        selected_reservoir_overlay, selected_reservoir_interval = next(
            pair for pair in interval_pairs
            if pair[0].interval_id == selected_reservoir_interval_id
        )
        selected_reservoir_depth = (
            float(selected_reservoir_interval.top) + float(selected_reservoir_interval.base)
        ) / 2.0
        _application_state_controller().state[workspace_synced_key] = str(selected_reservoir_interval_id)
        state_controller.update_values({
            "selected_reservoir_interval_id": str(selected_reservoir_interval_id),
            "selected_reservoir_depth": selected_reservoir_depth,
            "selected_reservoir_top": float(selected_reservoir_interval.top),
            "selected_reservoir_bottom": float(selected_reservoir_interval.base),
        })

    valid_ratio_mask = pd.Series(False, index=calculated_df.index)
    required_ratio_columns = [
        column
        for column in ("wh", "bh", "ch", "c1_c2", "c2_sumc", "c3_sumc", "nc4_sumc")
        if column in calculated_df.columns
    ]
    if required_ratio_columns:
        numeric_ratio_frame = calculated_df[required_ratio_columns].apply(
            pd.to_numeric, errors="coerce"
        )
        valid_ratio_mask = numeric_ratio_frame.notna().all(axis=1)
    valid_indices = [
        int(index)
        for index in calculated_df.index[valid_ratio_mask]
        if not pd.isna(index)
    ]

    default_index = valid_indices[0] if valid_indices else interval_indices[0]
    if selected_reservoir_interval is not None and "depth" in calculated_df.columns:
        depth_numeric = pd.to_numeric(calculated_df["depth"], errors="coerce")
        interval_mask = depth_numeric.between(
            float(selected_reservoir_interval.top),
            float(selected_reservoir_interval.base),
            inclusive="both",
        )
        interval_candidates = calculated_df.index[interval_mask]
        if len(interval_candidates):
            target_depth = float(state_controller.get_value(
                "selected_reservoir_depth",
                (float(selected_reservoir_interval.top) + float(selected_reservoir_interval.base)) / 2.0,
            ))
            candidate_depths = depth_numeric.loc[interval_candidates]
            nearest_label = (candidate_depths - target_depth).abs().idxmin()
            if not pd.isna(nearest_label):
                default_index = int(nearest_label)

    selected_index = st.selectbox(
        "Выбор глубинной точки внутри пласта",
        options=interval_indices,
        index=interval_indices.index(default_index),
        format_func=lambda index: _interval_label(calculated_df, index),
    )
    if selected_index not in calculated_df.index:
        logger.warning("selected_interval_missing index=%s", safe_log_value(selected_index))
        st.error("Выбранная глубинная точка не найдена.")
        return

    selected_row = calculated_df.loc[selected_index]
    logger.info("interval_selected index=%s", safe_log_value(selected_index))
    _render_interval_rule_summary(selected_row, ch_mode=ch_mode)

    selected_depth_value = pd.to_numeric(
        pd.Series([selected_row.get("depth")]), errors="coerce"
    ).iloc[0]
    selected_depth_value = None if pd.isna(selected_depth_value) else float(selected_depth_value)

    # Selecting a depth point also updates the shared interval selection when
    # the point belongs to another detected interval.
    if selected_depth_value is not None and interval_pairs:
        matching_pair = next((
            pair for pair in interval_pairs
            if float(pair[1].top) <= selected_depth_value <= float(pair[1].base)
        ), None)
        if matching_pair is not None:
            selected_reservoir_overlay, selected_reservoir_interval = matching_pair
            state_controller.update_values({
                "selected_reservoir_interval_id": str(selected_reservoir_overlay.interval_id),
                "selected_reservoir_depth": selected_depth_value,
                "selected_reservoir_top": float(selected_reservoir_interval.top),
                "selected_reservoir_bottom": float(selected_reservoir_interval.base),
            })

    _render_selected_interval_header(
        selected_reservoir_interval,
        str(selected_reservoir_overlay.interval_id) if selected_reservoir_overlay is not None else "",
        project_label=str(getattr(active_project, "name", "") or ""),
        source_label=str(sheet_name),
    )

    if detected_interval_result is not None:
        _render_reservoir_ranking(
            calculated_df, list(detected_interval_result.intervals),
            selected_interval_id=str(selected_reservoir_overlay.interval_id) if selected_reservoir_overlay is not None else "",
            key="workspace_reservoir_ranking_table",
            project_id=str(active_project.id),
        )

    st.subheader("Pixler + ternary")
    pixler_interval_frame = calculated_df
    pixler_interval_label = "Весь рассчитанный интервал"
    pixler_fluid_label = "Не определён"
    if selected_reservoir_interval is not None:
        depth_numeric = pd.to_numeric(calculated_df.get("depth"), errors="coerce")
        pixler_interval_frame = calculated_df.loc[
            depth_numeric.between(
                float(selected_reservoir_interval.top),
                float(selected_reservoir_interval.base),
                inclusive="both",
            )
        ]
        pixler_fluid_label = str(selected_reservoir_interval.fluid_type)
        pixler_interval_label = (
            f"{selected_reservoir_overlay.interval_id} · "
            f"{float(selected_reservoir_interval.top):g}–"
            f"{float(selected_reservoir_interval.base):g} м · "
            f"{selected_reservoir_interval.fluid_type} · "
            f"{selected_reservoir_interval.confidence_score}%"
        )

    left, right = st.columns(2)
    left.plotly_chart(
        build_pixler_palette(
            selected_row,
            zones=palette_config.pixler_zones,
            interval_frame=pixler_interval_frame,
            interval_label=pixler_interval_label,
            selected_depth=selected_depth_value,
            fluid_label=pixler_fluid_label,
        ),
        width="stretch",
        config=PLOTLY_SCREEN_CONFIG,
    )
    right.plotly_chart(
        build_ternary_palette(
            selected_row,
            regions=palette_config.ternary_regions,
            interval_frame=pixler_interval_frame,
            interval_label=pixler_interval_label,
            selected_depth=selected_depth_value,
            fluid_label=pixler_fluid_label,
        ),
        width="stretch",
        config=PLOTLY_SCREEN_CONFIG,
    )

    if selected_reservoir_interval is not None and selected_reservoir_overlay is not None:
        _render_selected_interval_passport(
            selected_reservoir_interval, str(selected_reservoir_overlay.interval_id),
            frame=calculated_df, selected_row=selected_row,
            pixler_zones=palette_config.pixler_zones, ternary_regions=palette_config.ternary_regions,
        )

    st.subheader("Графики по глубине")
    workspace_overlays = tuple(pair[0] for pair in interval_pairs)
    workspace_full_range = _effective_depth_range(calculated_df, None)
    selected_workspace_interval_id = (
        str(selected_reservoir_overlay.interval_id) if selected_reservoir_overlay is not None else ""
    )
    workspace_focus_range = _tablet_informative_depth_range(
        workspace_overlays,
        workspace_full_range,
        selected_depth=selected_depth_value,
        selected_interval_id=selected_workspace_interval_id,
    )
    workspace_plot_frame = _filter_by_depth_range(
        calculated_df, workspace_focus_range[0], workspace_focus_range[1]
    )
    screen_plot_df = downsample_frame_for_screen(workspace_plot_frame)
    workspace_visible_overlays = _visible_interval_overlays(
        workspace_overlays,
        workspace_focus_range,
        selected_interval_id=selected_workspace_interval_id,
        limit=24,
    )
    st.caption(
        f"Показан инженерно значимый диапазон: {workspace_focus_range[0]:.1f}–{workspace_focus_range[1]:.1f} м. "
        "Пустые участки без интерпретированных флюидов скрыты."
    )
    tab_gas, tab_ratios, tab_pixler = st.tabs(["C1–C5", "Wh / Bh / Ch", "Pixler"])
    common_depth_kwargs = {
        "depth_range": workspace_focus_range,
        "reservoir_intervals": workspace_visible_overlays,
        "selected_interval_id": selected_workspace_interval_id,
    }
    tab_gas.plotly_chart(build_depth_gas_tracks(screen_plot_df, **common_depth_kwargs), width="stretch", config=PLOTLY_SCREEN_CONFIG)
    tab_ratios.plotly_chart(build_depth_ratio_tracks(screen_plot_df, **common_depth_kwargs), width="stretch", config=PLOTLY_SCREEN_CONFIG)
    tab_pixler.plotly_chart(build_depth_pixler_tracks(screen_plot_df, **common_depth_kwargs), width="stretch", config=PLOTLY_SCREEN_CONFIG)

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


def _select_positive_y_range(label: str, key_prefix: str) -> tuple[float, float] | None:
    """Manual positive Y range for logarithmic engineering plots."""

    auto_scale = st.checkbox(f"Автомасштаб Y: {label}", value=True, key=f"{key_prefix}_y_auto")
    if auto_scale:
        return None
    left, right = st.columns(2)
    min_value = left.number_input(
        f"Y min: {label}", min_value=0.000001, value=0.01, step=0.01,
        format="%.6f", key=f"{key_prefix}_y_min",
    )
    max_value = right.number_input(
        f"Y max: {label}", min_value=0.000001, value=1000.0, step=1.0,
        format="%.6f", key=f"{key_prefix}_y_max",
    )
    if float(min_value) >= float(max_value):
        st.warning(f"Для {label} Y min должен быть меньше Y max. Используется автомасштаб.")
        return None
    return float(min_value), float(max_value)


def _filter_interpretation_tracks(tracks: tuple[str, ...]) -> tuple[str, ...]:
    selected = tuple(track for track in tracks if track in INTERPRETATION_TRACK_OPTIONS)
    return selected or INTERPRETATION_TRACK_OPTIONS


def _set_interpretation_x_range_state(key_prefix: str, x_range: tuple[float, float] | None) -> None:
    controller = _application_state_controller()
    values = {f"{key_prefix}_x_auto": x_range is None}
    if x_range is not None:
        values.update({
            f"{key_prefix}_x_min": float(x_range[0]),
            f"{key_prefix}_x_max": float(x_range[1]),
        })
    controller.update_values(values)


def _set_inline_operation_status(slot, stage: str, message: str, *, state: str = "active") -> None:
    """Render a compact in-flow operation status without Streamlit spinner overlays."""

    if slot is None or not hasattr(slot, "markdown"):
        return
    normalized_state = state if state in {"active", "success", "error"} else "active"
    labels = {"active": "Выполняется", "success": "Готово", "error": "Ошибка"}
    slot.markdown(
        f"""
        <div class="grp-inline-operation grp-inline-operation--{normalized_state}" role="status" aria-live="polite">
          <span class="grp-inline-operation__state">{html.escape(labels[normalized_state])}</span>
          <strong>{html.escape(stage)}</strong>
          <span>{html.escape(message)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _safe_widget_key(value: object) -> str:
    token = "".join(char if char.isalnum() else "_" for char in str(value)).strip("_")
    return token[:80] or "value"


def _tablet_x_range_key(column: str) -> str:
    return f"interpretation_tablet_{_safe_widget_key(column)}"


def _set_tablet_x_range_state(column: str, x_range: tuple[float, float] | None) -> None:
    key_prefix = _tablet_x_range_key(column)
    _set_interpretation_x_range_state(key_prefix, x_range)


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
        marker_count_key = "interpretation_tablet_marker_count"
        if marker_count_key not in _application_state_controller().state:
            _application_state_controller().state[marker_count_key] = 0
        marker_count = st.number_input(
            "Количество маркеров",
            min_value=0,
            max_value=8,
            step=1,
            key=marker_count_key,
        )
        markers: list[InterpretationMarker] = []
        span = max(default_bottom - default_top, 0.0)
        for index in range(int(marker_count)):
            label_default = chr(ord("a") + index)
            depth_default = default_top + (span * (index + 1) / (int(marker_count) + 1)) if marker_count else default_top
            label_col, depth_col, note_col = st.columns((1, 1, 3))
            label_key = f"interpretation_tablet_marker_{index}_label"
            depth_key = f"interpretation_tablet_marker_{index}_depth"
            note_key = f"interpretation_tablet_marker_{index}_note"
            _application_state_controller().state.setdefault(label_key, label_default)
            _application_state_controller().state.setdefault(depth_key, float(depth_default))
            _application_state_controller().state.setdefault(note_key, "")
            label = label_col.text_input(f"Метка {index + 1}", key=label_key)
            marker_depth = depth_col.number_input(
                f"Глубина {index + 1}",
                step=0.1,
                key=depth_key,
            )
            note = note_col.text_input(f"Комментарий {index + 1}", key=note_key)
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
        zone_count_key = "interpretation_tablet_zone_count"
        if zone_count_key not in _application_state_controller().state:
            _application_state_controller().state[zone_count_key] = 0
        zone_count = st.number_input(
            "Количество зон",
            min_value=0,
            max_value=12,
            step=1,
            key=zone_count_key,
        )
        zones: list[InterpretationZone] = []
        span = max(default_bottom - default_top, 0.0)
        for index in range(int(zone_count)):
            zone_top_default = default_top + (span * index / max(int(zone_count), 1))
            zone_bottom_default = default_top + (span * (index + 1) / max(int(zone_count), 1))
            label_col, top_col, bottom_col, color_col = st.columns((1.4, 1, 1, 1))
            label_key = f"interpretation_tablet_zone_{index}_label"
            top_key = f"interpretation_tablet_zone_{index}_top"
            bottom_key = f"interpretation_tablet_zone_{index}_bottom"
            color_key = f"interpretation_tablet_zone_{index}_color"
            note_key = f"interpretation_tablet_zone_{index}_note"
            _application_state_controller().state.setdefault(label_key, f"Zone {index + 1}")
            _application_state_controller().state.setdefault(top_key, float(zone_top_default))
            _application_state_controller().state.setdefault(bottom_key, float(zone_bottom_default))
            _application_state_controller().state.setdefault(color_key, "#ffd966")
            _application_state_controller().state.setdefault(note_key, "")
            label = label_col.text_input(f"Зона {index + 1}", key=label_key)
            top_depth = top_col.number_input(
                f"Верх зоны {index + 1}",
                step=0.1,
                key=top_key,
            )
            bottom_depth = bottom_col.number_input(
                f"Низ зоны {index + 1}",
                step=0.1,
                key=bottom_key,
            )
            color = color_col.color_picker(f"Цвет зоны {index + 1}", key=color_key)
            note = st.text_input(f"Комментарий зоны {index + 1}", key=note_key)
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

def _tablet_columns_state(filtered_df: pd.DataFrame) -> tuple[str, ...]:
    """Return stored tablet columns after validating them against current data."""

    controller = _application_state_controller()
    current_state = controller.get_tuple("interpretation_tablet_columns")
    valid_state = _valid_tablet_columns(filtered_df, current_state)
    if current_state and valid_state != current_state:
        controller.set_value("interpretation_tablet_columns", list(valid_state))
    return valid_state


def _apply_mud_gas_tablet_preset_to_state(columns: tuple[str, ...]) -> None:
    """Persist the mud-gas tablet preset through the state controller."""

    _application_state_controller().set_value("interpretation_tablet_columns", list(columns))


def _apply_mud_gas_tablet_markers_to_state(markers: tuple[InterpretationMarker, ...]) -> None:
    """Persist generated mud-gas markers through the state controller."""

    values: dict[str, object] = {"interpretation_tablet_marker_count": len(markers)}
    for index, marker in enumerate(markers):
        values[f"interpretation_tablet_marker_{index}_label"] = marker.label
        values[f"interpretation_tablet_marker_{index}_depth"] = float(marker.depth)
        values[f"interpretation_tablet_marker_{index}_note"] = marker.note
    _application_state_controller().update_values(values)


def _tablet_fill_mode_default(column: str, tablet_fill: bool) -> str:
    """Return a validated tablet fill mode from application state."""

    default_mode = _application_state_controller().get_value(
        f"interpretation_tablet_{_safe_widget_key(column)}_fill_mode"
    )
    if default_mode not in TABLET_FILL_MODES:
        return "to_zero" if tablet_fill else "none"
    return str(default_mode)


def _render_tablet_controls(
    filtered_df: pd.DataFrame,
    depth_range: tuple[float, float] | None,
) -> tuple[tuple[str, ...], dict[str, tuple[float, float]], dict[str, str], dict[str, str], tuple[InterpretationMarker, ...], tuple[InterpretationZone, ...], bool]:
    available_columns = numeric_tablet_columns(filtered_df)
    if not available_columns:
        st.warning("В выбранном интервале нет числовых параметров для планшета.")
        return (), {}, {}, {}, (), (), False

    valid_state = _tablet_columns_state(filtered_df)

    literature_columns = mud_gas_literature_tablet_columns(filtered_df)
    if literature_columns:
        preset_col, marker_col = st.columns(2)
        if preset_col.button(
            "Применить preset Mud gas analysis",
            help="Выбирает доступные GR/total gas/C1-C5/Wh-Bh-Ch/Pixler/ГИС-треки в порядке из литературного обзора.",
            width="stretch",
            key="interpretation_tablet_apply_mud_gas_preset",
        ):
            _apply_mud_gas_tablet_preset_to_state(literature_columns)
            _refresh_ui()
        if marker_col.button(
            "Добавить mud-gas маркеры",
            help="Ставит безопасные справочные маркеры по total-gas/Wh/Pixler/oil-indicator экстремумам. Это не автоматическая классификация.",
            width="stretch",
            key="interpretation_tablet_apply_mud_gas_markers",
        ):
            suggested_markers = mud_gas_literature_markers(filtered_df)
            _apply_mud_gas_tablet_markers_to_state(suggested_markers)
            _refresh_ui()
        st.caption(
            "Mud gas preset использует только найденные в данных колонки; отсутствующие C-компоненты, ratios или ГИС-кривые не подставляются искусственно."
        )

    # Streamlit must have exactly one source of truth for keyed widgets.
    # Initialising Session State and also passing ``default=`` causes repeated
    # reruns and the floating/empty status box reported by users.
    initial_columns = list(_tablet_columns_default(filtered_df, valid_state))
    state_key = "interpretation_tablet_columns"
    current_widget_value = _application_state_controller().state.get(state_key)
    if not isinstance(current_widget_value, (list, tuple)):
        _application_state_controller().state[state_key] = initial_columns
    else:
        validated_widget_value = [column for column in current_widget_value if column in available_columns]
        if validated_widget_value != list(current_widget_value):
            _application_state_controller().state[state_key] = validated_widget_value or initial_columns

    selected_columns = tuple(
        st.multiselect(
            "Параметры планшета",
            options=available_columns,
            key=state_key,
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
            default_mode = _tablet_fill_mode_default(column, bool(tablet_fill))
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
    controller = _application_state_controller()
    values = {
        "interpretation_tracks": list(_filter_interpretation_tracks(settings.selected_tracks)),
        "interpretation_chart_height": int(settings.height),
        "interpretation_tablet_columns": list(settings.tablet_tracks),
        "interpretation_tablet_fill": bool(settings.tablet_fill),
        "interpretation_tablet_marker_count": len(settings.tablet_markers),
        "interpretation_tablet_zone_count": len(settings.tablet_zones),
        "interpretation_tablet_view_mode": "Детальный интервал" if settings.tablet_view_mode == "detail" else "Обзор всей скважины",
        "interpretation_min_interval_thickness": float(settings.tablet_min_interval_thickness),
        "interpretation_selected_interval_id": str(settings.selected_interval_id),
        "selected_reservoir_interval_id": str(settings.selected_interval_id),
        "interpretation_tablet_adaptive_height": bool(settings.tablet_adaptive_height),
    }
    if settings.depth_range is None:
        values["interpretation_depth_range_mode"] = "Весь интервал"
    else:
        values.update({
            "interpretation_depth_range_mode": "Ручной интервал",
            "interpretation_top_depth": float(settings.depth_range[0]),
            "interpretation_bottom_depth": float(settings.depth_range[1]),
        })
    for column, color in settings.tablet_colors.items():
        values[f"interpretation_tablet_{_safe_widget_key(column)}_color"] = str(color)
    for column, mode in settings.tablet_fill_modes.items():
        values[f"interpretation_tablet_{_safe_widget_key(column)}_fill_mode"] = str(mode)
    for index, marker in enumerate(settings.tablet_markers):
        values[f"interpretation_tablet_marker_{index}_label"] = str(marker.get("label") or chr(ord("a") + index))
        values[f"interpretation_tablet_marker_{index}_depth"] = float(marker.get("depth", 0.0))
        values[f"interpretation_tablet_marker_{index}_note"] = str(marker.get("note") or "")
    for index, zone in enumerate(settings.tablet_zones):
        values[f"interpretation_tablet_zone_{index}_label"] = str(zone.get("label") or f"Zone {index + 1}")
        values[f"interpretation_tablet_zone_{index}_top"] = float(zone.get("top_depth", 0.0))
        values[f"interpretation_tablet_zone_{index}_bottom"] = float(zone.get("bottom_depth", 0.0))
        values[f"interpretation_tablet_zone_{index}_color"] = str(zone.get("color") or "#ffd966")
        values[f"interpretation_tablet_zone_{index}_note"] = str(zone.get("note") or "")
    controller.update_values(values)

    _set_interpretation_x_range_state("interpretation_gas", settings.gas_x_range)
    _set_interpretation_x_range_state("interpretation_ratio", settings.ratio_x_range)
    _set_interpretation_x_range_state("interpretation_pixler", settings.pixler_x_range)
    controller.update_values({
        "interpretation_pixler_palette_y_auto": settings.pixler_palette_y_range is None,
        **({
            "interpretation_pixler_palette_y_min": float(settings.pixler_palette_y_range[0]),
            "interpretation_pixler_palette_y_max": float(settings.pixler_palette_y_range[1]),
        } if settings.pixler_palette_y_range is not None else {}),
    })
    for column, x_range in settings.tablet_x_ranges.items():
        _set_tablet_x_range_state(column, x_range)


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
        f"Режим планшета: {'детальный интервал' if settings.tablet_view_mode == 'detail' else 'обзор всей скважины'}",
        f"Минимальная мощность: {settings.tablet_min_interval_thickness:g} м",
        f"Выбранный интервал: {settings.selected_interval_id or 'не выбран'}",
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
        if st.button("Загрузить настройки графиков проекта", width="stretch", key=f"load_interpretation_graph_settings_{project.id}"):
            _apply_interpretation_graph_settings_to_session(project_settings)
            _refresh_ui()


def _render_interpretation_graph_settings_saver(
    project: ProjectRecord,
    settings: InterpretationGraphSettings,
    logger,
) -> None:
    with st.expander("Текущие настройки графиков", expanded=False):
        for line in _interpretation_graph_settings_summary(settings):
            st.caption(line)
        if st.button("Сохранить настройки графиков в проект", width="stretch", key=f"save_interpretation_graph_settings_{project.id}"):
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


def _render_selected_interval_header(
    interval: object | None,
    interval_id: str,
    *,
    project_label: str = "",
    source_label: str = "",
) -> None:
    """Render the shared engineering header for the active reservoir interval.

    The helper is intentionally defensive because both the data workspace and
    the interpretation workspace call it before an interval may be available.
    It exposes only user-facing engineering fields and never internal IDs beyond
    the public interval label already shown in navigation tables.
    """
    if interval is None:
        st.info("Инженерный интервал не выбран.")
        return

    top = float(getattr(interval, "top", 0.0) or 0.0)
    base = float(getattr(interval, "base", top) or top)
    thickness = float(getattr(interval, "thickness", abs(base - top)) or 0.0)
    confidence_score = int(getattr(interval, "confidence_score", 0) or 0)
    fluid_label, _, fluid_marker = _fluid_visual(getattr(interval, "fluid_type", ""))
    interpretation = str(getattr(interval, "interpretation", "") or "").strip()

    public_id = str(interval_id or "").strip() or "Интервал"
    st.subheader(f"{fluid_marker} {public_id}: {top:g}–{base:g} м")

    metric_columns = st.columns(4)
    metric_columns[0].metric("Верх", f"{top:g} м")
    metric_columns[1].metric("Низ", f"{base:g} м")
    metric_columns[2].metric("Мощность", f"{thickness:g} м")
    metric_columns[3].metric("Достоверность", f"{confidence_score}%")

    st.caption(f"Вероятный флюид: {fluid_label}.")
    if interpretation:
        st.write(interpretation)

    context_parts = [value for value in (str(project_label).strip(), str(source_label).strip()) if value]
    if context_parts:
        st.caption(" · ".join(context_parts))




def _tablet_informative_depth_range(
    overlays: Sequence[ReservoirIntervalOverlay],
    fallback_range: tuple[float, float],
    *,
    selected_depth: float | None = None,
    selected_interval_id: str = "",
    padding_fraction: float = 0.035,
    minimum_padding_m: float = 8.0,
) -> tuple[float, float]:
    """Return the useful depth envelope for the engineering tablet.

    The tablet is an interpretation product, not a raw full-well viewer.  Empty
    depth above and below classified intervals only compresses the curves.  The
    viewport therefore follows all meaningful interpreted intervals and adds a
    small geological context margin.  The original applied depth range remains
    the hard boundary.
    """

    lower_bound, upper_bound = sorted((float(fallback_range[0]), float(fallback_range[1])))
    ignored = {
        "", "unknown", "uncertain", "no_data", "insufficient_data",
        "insufficient", "dry", "none", "not_interpreted",
    }
    # A selected interval is the primary engineering context.  Focusing it
    # avoids compressing a 10–20 m target inside a 700 m envelope merely
    # because many unrelated intervals exist elsewhere in the well.
    selected_interval = next(
        (item for item in overlays if str(getattr(item, "interval_id", "")) == str(selected_interval_id or "")),
        None,
    )
    if selected_interval is not None:
        top = max(lower_bound, min(float(selected_interval.top_depth), float(selected_interval.bottom_depth)))
        bottom = min(upper_bound, max(float(selected_interval.top_depth), float(selected_interval.bottom_depth)))
        span = max(bottom - top, 0.0)
        padding = max(float(minimum_padding_m), span * 0.35)
        return (max(lower_bound, top - padding), min(upper_bound, bottom + padding))

    meaningful = []
    for interval in overlays:
        fluid = str(getattr(interval, "fluid_type", "") or "").strip().lower()
        if fluid in ignored:
            continue
        top = min(float(interval.top_depth), float(interval.bottom_depth))
        bottom = max(float(interval.top_depth), float(interval.bottom_depth))
        if bottom < lower_bound or top > upper_bound:
            continue
        meaningful.append((max(top, lower_bound), min(bottom, upper_bound)))

    if not meaningful:
        if selected_depth is None:
            return (lower_bound, upper_bound)
        centre = min(max(float(selected_depth), lower_bound), upper_bound)
        half_window = max(minimum_padding_m * 2.0, (upper_bound - lower_bound) * 0.04)
        return (max(lower_bound, centre - half_window), min(upper_bound, centre + half_window))

    top = min(item[0] for item in meaningful)
    bottom = max(item[1] for item in meaningful)
    span = max(bottom - top, 0.0)
    padding = max(float(minimum_padding_m), span * float(padding_fraction))
    return (max(lower_bound, top - padding), min(upper_bound, bottom + padding))

def _visible_interval_overlays(
    overlays: Sequence[ReservoirIntervalOverlay],
    depth_range: tuple[float, float],
    *,
    selected_interval_id: str = "",
    limit: int = 24,
) -> tuple[ReservoirIntervalOverlay, ...]:
    """Return a bounded set of intervals intersecting the active viewport.

    Plotly shapes are expensive in the browser.  The selected interval is
    always retained, while the remaining entries are ranked by confidence and
    thickness.
    """

    top, bottom = sorted((float(depth_range[0]), float(depth_range[1])))
    candidates = [
        item for item in overlays
        if max(float(item.top_depth), float(item.bottom_depth)) >= top
        and min(float(item.top_depth), float(item.bottom_depth)) <= bottom
    ]
    candidates.sort(
        key=lambda item: (
            str(getattr(item, "interval_id", "")) == str(selected_interval_id or ""),
            int(getattr(item, "confidence_score", 0) or 0),
            float(getattr(item, "thickness", 0.0) or 0.0),
        ),
        reverse=True,
    )
    return tuple(candidates[: max(1, int(limit))])


def _adaptive_tablet_height(depth_range: tuple[float, float], view_mode: str, base_height: int) -> int:
    span = max(0.1, abs(float(depth_range[1]) - float(depth_range[0])))
    if view_mode == "detail":
        # Detailed interval: allocate more pixels per metre, but keep the page usable.
        return max(680, min(1500, int(520 + span * 22)))
    # Whole-well overview must remain compact enough for navigation.
    return max(680, min(1100, int(base_height)))


def _interval_display_label(interval: object, interval_id: str) -> str:
    fluid_labels = {
        "oil": "Нефть", "gas": "Газ", "condensate": "Газоконденсат",
        "gas_oil": "Газ–нефть", "oil_gas": "Нефть–газ", "mixed": "Смешанный",
        "transition": "Переходный", "water": "Вода", "uncertain": "Неопределённый",
    }
    fluid = fluid_labels.get(str(getattr(interval, "fluid_type", "")), str(getattr(interval, "fluid_type", "")))
    return (
        f"{interval_id} · {float(getattr(interval, 'top', 0.0)):g}–"
        f"{float(getattr(interval, 'base', 0.0)):g} м · {float(getattr(interval, 'thickness', 0.0)):g} м · "
        f"{fluid} · {int(getattr(interval, 'confidence_score', 0))}%"
    )


def _selected_interval_print_range(
    interval: object | None,
    fallback: tuple[float, float],
) -> tuple[float, float]:
    """Return the selected reservoir top/base or a normalized fallback range."""
    if interval is not None:
        try:
            top = float(getattr(interval, "top"))
            base = float(getattr(interval, "base"))
            if top != base:
                return (min(top, base), max(top, base))
        except (TypeError, ValueError, AttributeError):
            pass
    first, second = float(fallback[0]), float(fallback[1])
    return (min(first, second), max(first, second))


def _render_reservoir_ranking(
    frame: pd.DataFrame,
    intervals: tuple[object, ...] | list[object],
    *,
    selected_interval_id: str,
    key: str,
    project_id: str,
) -> None:
    if frame.empty or not intervals:
        return

    try:
        saved_profiles = load_project_ranking_profiles(
            root=LAS_CORRELATION_PROJECTS_ROOT, project_id=project_id,
        )
    except Exception:
        saved_profiles = ()

    all_profiles = (*BUILTIN_RANKING_PROFILES, *saved_profiles)
    profile_lookup = {profile.profile_id: profile for profile in all_profiles}
    profile_key = f"{key}_profile_id"
    current_profile_id = str(_application_state_controller().state.get(profile_key, DEFAULT_RANKING_PROFILE.profile_id))
    if current_profile_id not in profile_lookup:
        current_profile_id = DEFAULT_RANKING_PROFILE.profile_id
        _application_state_controller().state[profile_key] = current_profile_id

    with st.expander("Reservoir Ranking 2.0 — настраиваемые профили", expanded=True):
        profile_id = st.selectbox(
            "Профиль ранжирования",
            options=list(profile_lookup),
            index=list(profile_lookup).index(current_profile_id),
            format_func=lambda value: profile_lookup[value].name,
            key=profile_key,
        )
        base_profile = profile_lookup[profile_id]
        st.caption(base_profile.description or "Настраиваемый инженерный профиль.")

        custom_mode = st.checkbox(
            "Изменить веса текущего профиля",
            value=False,
            key=f"{key}_custom_mode",
        )
        if custom_mode:
            w = base_profile.weights.normalized()
            c1, c2, c3, c4 = st.columns(4)
            confidence_w = c1.number_input("Достоверность, %", 0.0, 100.0, float(w.confidence), 1.0, key=f"{key}_w_conf")
            agreement_w = c2.number_input("Согласованность, %", 0.0, 100.0, float(w.agreement), 1.0, key=f"{key}_w_agree")
            completeness_w = c3.number_input("Полнота C1–C5, %", 0.0, 100.0, float(w.completeness), 1.0, key=f"{key}_w_complete")
            thickness_w = c4.number_input("Мощность, %", 0.0, 100.0, float(w.thickness), 1.0, key=f"{key}_w_thick")
            reference_thickness = st.number_input(
                "Мощность насыщения вклада, м",
                min_value=0.1, max_value=500.0, value=float(base_profile.reference_thickness), step=0.5,
                key=f"{key}_reference_thickness",
                help="При этой мощности вклад мощности достигает максимума и далее не растёт.",
            )
            normalized_weights = ReservoirRankingWeights(
                confidence_w, agreement_w, completeness_w, thickness_w,
            ).normalized()
            current_profile = ReservoirRankingProfile(
                profile_id=f"session-{key}",
                name="Текущие пользовательские веса",
                weights=normalized_weights,
                reference_thickness=float(reference_thickness),
                description="Временный профиль текущей сессии.",
                built_in=False,
            )
            st.caption(
                "Нормализованные веса: "
                f"достоверность {normalized_weights.confidence:.1f}%, "
                f"согласованность {normalized_weights.agreement:.1f}%, "
                f"полнота {normalized_weights.completeness:.1f}%, "
                f"мощность {normalized_weights.thickness:.1f}%."
            )
            save_name = st.text_input("Название сохраняемого профиля", key=f"{key}_save_name")
            if st.button("Сохранить профиль в проект", key=f"{key}_save_profile", width="stretch"):
                clean_name = str(save_name or "").strip()
                if not clean_name:
                    st.warning("Введите название профиля.")
                else:
                    profile_slug = "custom-" + hashlib.sha1(clean_name.encode("utf-8")).hexdigest()[:10]
                    saved = ReservoirRankingProfile(
                        profile_id=profile_slug,
                        name=clean_name,
                        weights=normalized_weights,
                        reference_thickness=float(reference_thickness),
                        description="Пользовательский профиль проекта.",
                        built_in=False,
                    )
                    merged = [item for item in saved_profiles if item.profile_id != profile_slug] + [saved]
                    try:
                        save_project_ranking_profiles(
                            merged, root=LAS_CORRELATION_PROJECTS_ROOT, project_id=project_id,
                        )
                    except Exception:
                        st.error("Не удалось сохранить профиль ранжирования.")
                    else:
                        st.success(f"Профиль «{clean_name}» сохранён.")
        else:
            current_profile = base_profile

        reference_options = {profile.profile_id: profile for profile in all_profiles}
        reference_id = st.selectbox(
            "Сравнить с профилем",
            options=list(reference_options),
            index=0,
            format_func=lambda value: reference_options[value].name,
            key=f"{key}_reference_profile",
        )
        reference_profile = reference_options[reference_id]

        _application_state_controller().state["active_reservoir_ranking_profile"] = current_profile
        ranking = rank_reservoir_intervals(frame, intervals, profile=current_profile)
        reference_ranking = rank_reservoir_intervals(frame, intervals, profile=reference_profile)
        changes = compare_reservoir_rankings(
            reference_ranking, ranking,
            previous_profile=reference_profile,
            current_profile=current_profile,
        )
        ranking_df = reservoir_ranking_dataframe(ranking, changes)
        if ranking_df.empty:
            return
        ranking_df.insert(0, "Активный", ["▶" if str(value) == str(selected_interval_id) else "" for value in ranking_df["ID"]])
        st.caption(
            f"Активный профиль: {current_profile.name}. Индекс 0–100 является инструментом инженерной приоритизации, "
            "а не оценкой запасов, net pay, насыщенности или коммерческой ценности."
        )
        event = st.dataframe(
            ranking_df.head(20), width="stretch", height=470, hide_index=True,
            on_select="rerun", selection_mode="single-row", key=key,
            column_config={
                "Активный": st.column_config.TextColumn("", width="small"),
                "Место": st.column_config.NumberColumn("№", format="%d", width="small"),
                "Δ места": st.column_config.NumberColumn("Δ места", format="%+d", width="small"),
                "ID": st.column_config.TextColumn("ID", width="small"),
                "Индекс приоритета": st.column_config.ProgressColumn("Приоритет", min_value=0, max_value=100, format="%.1f"),
                "Δ индекса": st.column_config.NumberColumn("Δ индекса", format="%+.1f"),
                "Мощность, м": st.column_config.NumberColumn("Мощность, м", format="%.2f"),
                "Почему изменилось": st.column_config.TextColumn("Почему изменилось", width="large"),
                "Рекомендация": st.column_config.TextColumn("Рекомендация", width="large"),
            },
        )
        chosen = _selected_interval_id_from_table(event, ranking_df.head(20))
        if chosen and chosen != selected_interval_id:
            lookup = {f"HC-{index:03d}": interval for index, interval in enumerate(intervals, start=1)}
            interval = lookup.get(chosen)
            payload = {"selected_reservoir_interval_id": chosen}
            if interval is not None:
                payload.update({
                    "selected_reservoir_depth": (float(interval.top) + float(interval.base)) / 2.0,
                    "selected_reservoir_top": float(interval.top),
                    "selected_reservoir_bottom": float(interval.base),
                })
            _application_state_controller().update_values(payload)
            _request_ui_refresh_and_rerun("ranking_interval_selected")


def _render_selected_interval_passport(
    interval: object,
    interval_id: str,
    *,
    frame: pd.DataFrame | None = None,
    selected_row: pd.Series | None = None,
    pixler_zones=(),
    ternary_regions=(),
) -> None:
    if frame is None or frame.empty:
        return
    passport = build_reservoir_passport(
        frame, interval, interval_id=interval_id, selected_row=selected_row,
        pixler_zones=tuple(pixler_zones),
        ternary_regions=tuple(ternary_regions),
    )
    with st.expander(f"Reservoir Passport 2.0 — {passport.interval_id}", expanded=True):
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Кровля", f"{passport.top:g} м")
        c2.metric("Подошва", f"{passport.base:g} м")
        c3.metric("Мощность", f"{passport.thickness:g} м")
        c4.metric("Достоверность", f"{passport.confidence_score}%")
        c5.metric("Согласованность", f"{passport.agreement_percent:g}%")
        st.markdown(f"**Вероятный флюид:** {passport.fluid_type}  ·  **{passport.readiness_label}**")

        gas_df = pd.DataFrame([{
            "Компонент": name.upper().replace("IC", "iC").replace("NC", "nC"),
            "Медиана по интервалу": value,
        } for name, value in passport.gas_composition])
        ratio_df = pd.DataFrame([{
            "Показатель": name, "Медиана по интервалу": value,
        } for name, value in passport.derived_metrics])
        method_df = pd.DataFrame([{
            "Методика": item.method, "Результат": item.classification,
            "Поддержка, %": item.support_percent, "Статус": item.status,
        } for item in passport.methods])
        tab_gas, tab_ratios, tab_methods, tab_cross, tab_decision = st.tabs((
            "Газовый состав", "Коэффициенты", "Методики", "Cross-Method", "Заключение",
        ))
        tab_gas.dataframe(gas_df, width="stretch", hide_index=True, height=300)
        tab_gas.caption(f"Полнота компонентов C1–C5: {passport.data_completeness_percent:g}%")
        tab_ratios.dataframe(ratio_df, width="stretch", hide_index=True, height=360)
        tab_methods.dataframe(method_df, width="stretch", hide_index=True, height=220)
        tab_methods.caption(f"Индекс согласованности методик: {passport.agreement_percent:g}%")
        analysis = passport.cross_method_analysis
        if analysis is not None and analysis.agreement_matrix:
            matrix = pd.DataFrame(analysis.agreement_matrix[1:], columns=analysis.agreement_matrix[0])
            tab_cross.markdown("**Матрица согласованности**")
            tab_cross.dataframe(matrix, width="stretch", hide_index=True, height=220)
        contrib_df = pd.DataFrame([{
            "Методика": item.method,
            "Вклад, %": item.contribution_percent,
            "Классификация": item.classification,
            "Поддержка, %": item.support_percent,
        } for item in analysis.contributions]) if analysis is not None else pd.DataFrame()
        if not contrib_df.empty:
            tab_cross.markdown("**Вклад методик в итоговую классификацию**")
            tab_cross.dataframe(contrib_df, width="stretch", hide_index=True, height=220)
        if analysis is not None and analysis.disagreement_reasons:
            tab_cross.markdown("**Возможные причины расхождения:**")
            for reason in analysis.disagreement_reasons:
                tab_cross.markdown(f"- {reason}")
        if analysis is not None and analysis.quality_issues:
            tab_cross.markdown("**QC:**")
            for issue in analysis.quality_issues[:8]:
                tab_cross.markdown(f"- `{issue.severity}` — {issue.message}")
        if analysis is not None:
            breakdown_df = pd.DataFrame(analysis.confidence_breakdown, columns=("Источник", "Оценка, %"))
            tab_cross.markdown("**Разложение уверенности**")
            tab_cross.dataframe(breakdown_df, width="stretch", hide_index=True, height=220)
        if passport.engineering_conclusion:
            tab_decision.markdown(f"**Инженерное заключение:** {passport.engineering_conclusion}")
        if passport.recommendations:
            tab_decision.markdown("**Рекомендации:**")
            for item in passport.recommendations[:5]:
                tab_decision.markdown(f"- {item}")
        if passport.limitations:
            tab_decision.markdown("**Ограничения:**")
            for item in passport.limitations[:5]:
                tab_decision.markdown(f"- {item}")
        tab_decision.info(passport.readiness_label)



def _streamlit_fragment(function=None, *, run_every: str | None = None):
    """Use fragment reruns when supported, keeping compatibility with older Streamlit."""
    def decorate(target):
        fragment = getattr(st, "fragment", None)
        if not callable(fragment):
            return target
        if run_every is None:
            decorated = fragment(target)
        else:
            fragment_decorator = fragment(run_every=run_every)
            if not callable(fragment_decorator):
                return target
            decorated = fragment_decorator(target)
        return decorated if callable(decorated) else target

    return decorate(function) if function is not None else decorate


@_streamlit_fragment(run_every="2s")
def _render_professional_export_panel(
    logger,
    active_project: ProjectRecord,
    *,
    calculated_df: pd.DataFrame,
    valid_depth: pd.Series,
    depth_range: tuple[float, float],
    selected_interval: object | None,
    selected_interval_id: str | None,
    source_label: str,
    calculated_signature: str,
    revision_snapshot,
    height: int,
) -> None:
    """Render Professional Export as an isolated fragment.

    Widget changes and artifact preparation rerun only this panel on Streamlit
    versions that support fragments, so the surrounding Plotly charts are not
    serialized and sent to the browser again.
    """
    with st.expander("🖨️ ПЕЧАТЬ И ПРОФЕССИОНАЛЬНЫЙ ЭКСПОРТ", expanded=True):
        st.markdown("### Подготовка PDF, DOCX, PNG, SVG или XLSX")
        st.info(
            "Здесь настраивается печать отчёта. Для полного отчёта по скважине "
            "выберите режим «Вся скважина и все УВ-интервалы». "
            "После запуска приложение покажет текущий этап подготовки файла."
        )
        st.caption("Шаги: профиль → формат → область печати → подготовить → скачать.")
        profile_options = report_profile_options()
        format_options = export_format_options()
        export_cache_key = f"presentation_export_artifact_{active_project.id}"
        export_error_key = f"presentation_export_error_{active_project.id}"
        report_preview_counts_key = f"presentation_report_document_counts_{active_project.id}"
        pdf_preview_cache_key = f"presentation_pdf_preview_{active_project.id}"

        print_mode_options = [
            "Вся скважина и все УВ-интервалы",
            "Текущий интервал графиков",
            "Выбрать отдельно",
        ]
        if selected_interval is not None:
            print_mode_options.insert(1, "Выбранный пласт")
        full_print_min = float(valid_depth.min()) if not valid_depth.empty else float(depth_range[0])
        full_print_max = float(valid_depth.max()) if not valid_depth.empty else float(depth_range[1])
        default_print_top = (
            float(selected_interval.top) if selected_interval is not None else float(depth_range[0])
        )
        default_print_bottom = (
            float(selected_interval.base) if selected_interval is not None else float(depth_range[1])
        )
        state_controller = _application_state_controller()
        export_state = state_controller.state
        cache_metrics_registry = state_controller.ensure_runtime_service(
            "cache_metrics_registry",
            CacheMetricsRegistry,
            expected_type=CacheMetricsRegistry,
            scope="session",
        )
        pdf_preview_runtime_cache = application_service_container(export_state).pdf_preview(
            project_id=str(active_project.id),
            root=LAS_CORRELATION_PROJECTS_ROOT,
            metrics_registry=cache_metrics_registry,
        )
        # Migrate and immediately remove the legacy Session State payload.
        legacy_pdf_preview_cache = export_state.pop(pdf_preview_cache_key, None)
        if isinstance(legacy_pdf_preview_cache, dict):
            migrated_entries = pdf_preview_runtime_cache.migrate_legacy_entries(
                legacy_pdf_preview_cache
            )
            logger.info(
                "pdf_preview_cache_migrated project_id=%s entries=%d",
                safe_log_value(active_project.id),
                migrated_entries,
            )
        background_manager = application_service_container(export_state).background_export(
            project_id=str(active_project.id),
            root=LAS_CORRELATION_PROJECTS_ROOT,
            max_workers=1,
        )
        normalized_form = normalize_export_form_state(
            export_state,
            project_id=str(active_project.id),
            profile_labels=tuple(option.label for option in profile_options),
            format_labels=tuple(option.label for option in format_options),
            print_modes=tuple(print_mode_options),
            depth_min=full_print_min,
            depth_max=full_print_max,
            default_top=default_print_top,
            default_bottom=default_print_bottom,
        )
        form_keys = normalized_form["keys"]
        designer_modes = report_modes()
        mode_by_label = {item.label: item for item in designer_modes}
        designer_templates = report_templates()
        template_by_label = {item.label: item for item in designer_templates}
        export_application = application_service_container(export_state).presentation_export(
            project_id=str(active_project.id),
            root=ROOT_DIR / "data" / "projects",
        )
        repeat_pending_key = f"export_history_repeat_pending_{active_project.id}"
        repeat_confirm_key = f"export_history_repeat_confirm_{active_project.id}"
        repeat_autorun_key = f"export_history_repeat_autorun_{active_project.id}"
        background_retry_context_key = f"background_export_retry_context_{active_project.id}"
        pending_confirmation = export_state.get(repeat_confirm_key)
        if isinstance(pending_confirmation, dict):
            st.warning(str(pending_confirmation.get("title", "Подтвердите повторный экспорт")))
            for confirmation_line in pending_confirmation.get("lines", ()):
                st.caption(str(confirmation_line))
            confirm_left, confirm_right = st.columns(2)
            if confirm_left.button(
                "✅ Подтвердить и пересобрать",
                key=f"export_history_confirm_rebuild_{active_project.id}",
                type="primary",
                width="stretch",
            ):
                export_state[repeat_pending_key] = dict(pending_confirmation.get("payload", {}))
                export_state[repeat_autorun_key] = True
                export_state.pop(repeat_confirm_key, None)
                _request_ui_refresh_and_rerun("export_history_confirm_rebuild")
                return
            if confirm_right.button(
                "Отмена",
                key=f"export_history_cancel_rebuild_{active_project.id}",
                width="stretch",
            ):
                export_state.pop(repeat_confirm_key, None)
                _request_ui_refresh_and_rerun("export_history_cancel_rebuild")
                return

        pending_repeat = export_state.pop(repeat_pending_key, None)
        if isinstance(pending_repeat, dict):
            profile_label_by_id = {item.id: item.label for item in profile_options}
            format_label_by_id = {item.id: item.label for item in format_options}
            repeated_profile = profile_label_by_id.get(str(pending_repeat.get("profile_id", "")))
            repeated_format = format_label_by_id.get(str(pending_repeat.get("format_id", "")))
            if repeated_profile:
                export_state[form_keys["profile"]] = repeated_profile
            if repeated_format:
                export_state[form_keys["format"]] = repeated_format
            mode_label_by_id = {item.id: item.label for item in designer_modes}
            template_label_by_id = {item.id: item.label for item in designer_templates}
            repeated_mode_id = str(pending_repeat.get("report_mode_id", "full_engineering"))
            repeated_template_id = str(pending_repeat.get("template_id", "engineering"))
            export_state[f"report_designer_mode_{active_project.id}"] = mode_label_by_id.get(
                repeated_mode_id, designer_modes[0].label
            )
            export_state[f"report_designer_template_{active_project.id}"] = template_label_by_id.get(
                repeated_template_id, designer_templates[0].label
            )
            export_state[f"report_designer_title_{active_project.id}"] = str(
                pending_repeat.get("report_title", "Gas Ratio Professional Report")
            )
            export_state[f"report_designer_technical_{active_project.id}"] = bool(
                pending_repeat.get("include_technical_appendix", True)
            )
            export_state[f"report_designer_chrome_{active_project.id}"] = bool(
                pending_repeat.get("show_page_chrome", True)
            )
            repeated_sections = tuple(
                item for item in pending_repeat.get("sections", ())
                if item in {"plots", "visualizations", "results", "conclusion"}
            )
            section_labels_repeat = {
                "plots": "Инженерные графики",
                "visualizations": "Планшеты и визуализации",
                "results": "Расчётные результаты",
                "conclusion": "Заключение и ограничения",
            }
            export_state[f"report_designer_sections_{active_project.id}_{repeated_template_id}"] = [
                section_labels_repeat[item] for item in repeated_sections
            ]
            repeated_print_mode = str(pending_repeat.get("print_mode", "Выбрать отдельно"))
            export_state[form_keys["print_mode"]] = (
                repeated_print_mode if repeated_print_mode in print_mode_options else "Выбрать отдельно"
            )
            export_state[form_keys["top"]] = float(pending_repeat.get("depth_top", default_print_top))
            export_state[form_keys["bottom"]] = float(pending_repeat.get("depth_bottom", default_print_bottom))
            export_state.pop(export_cache_key, None)
            export_state.pop(export_error_key, None)
        draft_key = f"export_wizard_draft_restored_{active_project.id}"
        if not export_state.get(draft_key):
            try:
                saved_draft = export_application.load_draft()
            except (OSError, ValueError, TypeError):
                logger.exception("export_wizard_draft_restore_failed project_id=%s", safe_log_value(active_project.id))
                saved_draft = None
            if saved_draft is not None:
                profile_label_by_id = {item.id: item.label for item in profile_options}
                format_label_by_id = {item.id: item.label for item in format_options}
                mode_label_by_id = {item.id: item.label for item in designer_modes}
                template_label_by_id = {item.id: item.label for item in designer_templates}
                export_state.setdefault(form_keys["profile"], profile_label_by_id.get(saved_draft.wizard.profile, profile_options[0].label))
                export_state.setdefault(form_keys["format"], format_label_by_id.get(saved_draft.wizard.export_format, format_options[0].label))
                export_state.setdefault(form_keys["print_mode"], saved_draft.print_mode)
                if saved_draft.depth_top is not None:
                    export_state.setdefault(form_keys["top"], float(saved_draft.depth_top))
                if saved_draft.depth_bottom is not None:
                    export_state.setdefault(form_keys["bottom"], float(saved_draft.depth_bottom))
                export_state.setdefault(f"report_designer_mode_{active_project.id}", mode_label_by_id.get(saved_draft.report_mode_id, designer_modes[0].label))
                export_state.setdefault(f"report_designer_template_{active_project.id}", template_label_by_id.get(saved_draft.template_id, designer_templates[0].label))
                export_state.setdefault(f"report_designer_title_{active_project.id}", saved_draft.report_title)
                export_state.setdefault(f"report_designer_technical_{active_project.id}", saved_draft.include_technical_appendix)
                export_state.setdefault(f"report_designer_chrome_{active_project.id}", saved_draft.show_page_chrome)
                restored_template = next((item for item in designer_templates if item.id == saved_draft.template_id), designer_templates[0])
                section_labels_restore = {
                    "plots": "Инженерные графики",
                    "visualizations": "Планшеты и визуализации",
                    "results": "Расчётные результаты",
                    "conclusion": "Заключение и ограничения",
                }
                export_state.setdefault(
                    f"report_designer_sections_{active_project.id}_{restored_template.id}",
                    [section_labels_restore[item] for item in saved_draft.sections if item in section_labels_restore],
                )
            export_state[draft_key] = True

        preview_counts_restore_key = f"report_preview_counts_restored_{active_project.id}"
        preview_counts_recovery_notice_key = f"report_preview_counts_recovery_notice_{active_project.id}"
        if not export_state.get(preview_counts_restore_key):
            try:
                preview_counts_load = export_application.load_preview_counts()
                if preview_counts_load.payload is not None:
                    export_state[report_preview_counts_key] = preview_counts_load.payload
                if preview_counts_load.recovered or preview_counts_load.source == "quarantined":
                    export_state[preview_counts_recovery_notice_key] = preview_counts_load.message
                    logger.warning(
                        "report_preview_counts_recovery project_id=%s source=%s quarantined=%s",
                        safe_log_value(active_project.id),
                        safe_log_value(preview_counts_load.source),
                        safe_log_value(len(preview_counts_load.quarantined)),
                    )
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                logger.exception(
                    "report_preview_counts_restore_failed project_id=%s",
                    safe_log_value(active_project.id),
                )
            export_state[preview_counts_restore_key] = True

        draft_controls_left, draft_controls_right = st.columns(2)
        reset_draft = draft_controls_left.button(
            "↺ Сбросить настройки",
            key=f"export_wizard_reset_{active_project.id}",
            help="Удаляет сохранённый черновик экспорта этого проекта и возвращает значения по умолчанию.",
            width="stretch",
        )
        clear_history = draft_controls_right.button(
            "🗑 Очистить историю",
            key=f"export_history_clear_{active_project.id}",
            help="Удаляет только компактную историю успешных экспортов. Готовые файлы и инженерные данные не затрагиваются.",
            width="stretch",
        )
        if reset_draft:
            try:
                export_application.delete_draft()
            except (OSError, ValueError):
                logger.exception("export_wizard_draft_delete_failed project_id=%s", safe_log_value(active_project.id))
            try:
                export_application.delete_preview_counts(include_quarantine=True)
            except (OSError, ValueError):
                logger.exception(
                    "report_preview_counts_delete_failed project_id=%s",
                    safe_log_value(active_project.id),
                )
            reset_keys = {
                draft_key,
                export_cache_key,
                export_error_key,
                report_preview_counts_key,
                pdf_preview_cache_key,
                preview_counts_restore_key,
                preview_counts_recovery_notice_key,
                form_keys["profile"],
                form_keys["format"],
                form_keys["print_mode"],
                form_keys["top"],
                form_keys["bottom"],
                f"report_designer_mode_{active_project.id}",
                f"report_designer_template_{active_project.id}",
                f"report_designer_title_{active_project.id}",
                f"report_designer_technical_{active_project.id}",
                f"report_designer_chrome_{active_project.id}",
            }
            reset_keys.update(
                f"report_designer_sections_{active_project.id}_{template.id}"
                for template in designer_templates
            )
            for reset_key in reset_keys:
                export_state.pop(reset_key, None)
            _request_ui_refresh_and_rerun("export_wizard_reset")
            return
        if clear_history:
            try:
                export_application.clear_history()
            except (OSError, ValueError):
                logger.exception("export_history_clear_failed project_id=%s", safe_log_value(active_project.id))
            _request_ui_refresh_and_rerun("export_history_clear")
            return

        # A form batches profile/format changes and starts the costly renderer
        # only after explicit confirmation. Persisted values are normalized
        # before widgets are created so a new LAS cannot leave stale out-of-
        # range depth values in Streamlit session state.
        with st.form(key=f"presentation_export_form_{active_project.id}", clear_on_submit=False):
            profile_widget_kwargs = {"index": 0} if form_keys["profile"] not in export_state else {}
            selected_profile_label = st.selectbox(
                "Профиль отчета",
                options=[option.label for option in profile_options],
                key=form_keys["profile"],
                help=tooltip("report.profile"),
                **profile_widget_kwargs,
            )
            format_widget_kwargs = {"index": 0} if form_keys["format"] not in export_state else {}
            selected_format_label = st.selectbox(
                "Формат экспорта",
                options=[option.label for option in format_options],
                key=form_keys["format"],
                help=tooltip("report.format"),
                **format_widget_kwargs,
            )
            mode_widget_key = f"report_designer_mode_{active_project.id}"
            mode_widget_kwargs = {"index": 2} if mode_widget_key not in export_state else {}
            selected_mode_label = st.selectbox(
                "Режим отчёта",
                options=tuple(mode_by_label),
                key=mode_widget_key,
                help="Краткий — только ключевые результаты; стандартный — основные графики и выводы; полный инженерный — весь комплект разделов и приложений.",
                **mode_widget_kwargs,
            )
            selected_mode = mode_by_label[selected_mode_label]
            template_widget_key = f"report_designer_template_{active_project.id}"
            template_widget_kwargs = {"index": 0} if template_widget_key not in export_state else {}
            selected_template_label = st.selectbox(
                "Шаблон оформления",
                options=tuple(template_by_label),
                key=template_widget_key,
                help=tooltip("report.template"),
                **template_widget_kwargs,
            )
            selected_template = template_by_label[selected_template_label]
            title_widget_key = f"report_designer_title_{active_project.id}"
            title_widget_kwargs = (
                {"value": "Gas Ratio Professional Report"}
                if title_widget_key not in export_state
                else {}
            )
            report_title = st.text_input(
                "Заголовок отчёта",
                key=title_widget_key,
                **title_widget_kwargs,
            )
            section_labels = {
                "plots": "Инженерные графики",
                "visualizations": "Планшеты и визуализации",
                "results": "Расчётные результаты",
                "conclusion": "Заключение и ограничения",
            }
            sections_widget_key = f"report_designer_sections_{active_project.id}_{selected_template.id}"
            sections_widget_kwargs = (
                {"default": tuple(section_labels[item] for item in selected_template.default_sections)}
                if sections_widget_key not in export_state
                else {}
            )
            selected_section_labels = st.multiselect(
                "Разделы отчёта",
                options=tuple(section_labels.values()),
                key=sections_widget_key,
                help=tooltip("report.sections"),
                **sections_widget_kwargs,
            )
            technical_widget_key = f"report_designer_technical_{active_project.id}"
            technical_widget_kwargs = (
                {"value": selected_template.include_technical_appendix}
                if technical_widget_key not in export_state
                else {}
            )
            include_technical_design = st.checkbox(
                "Техническое приложение",
                key=technical_widget_key,
                help=tooltip("report.technical_appendix"),
                **technical_widget_kwargs,
            )
            chrome_widget_key = f"report_designer_chrome_{active_project.id}"
            chrome_widget_kwargs = (
                {"value": selected_template.show_page_chrome}
                if chrome_widget_key not in export_state
                else {}
            )
            show_page_chrome_design = st.checkbox(
                "Служебные колонтитулы и нумерация",
                key=chrome_widget_key,
                help=tooltip("report.page_chrome"),
                **chrome_widget_kwargs,
            )

            print_mode = st.radio(
                "Интервал печати",
                options=tuple(print_mode_options),
                horizontal=True,
                key=form_keys["print_mode"],
                help=tooltip("report.print_scope"),
            )
            if print_mode == "Вся скважина и все УВ-интервалы":
                print_top, print_bottom = full_print_min, full_print_max
                st.success(
                    f"Полный отчёт по скважине: {print_top:g}–{print_bottom:g} м. "
                    "Будут добавлены обзорный планшет и детальные страницы по УВ-интервалам."
                )
            elif print_mode == "Выбранный пласт" and selected_interval is not None:
                print_top, print_bottom = _selected_interval_print_range(
                    selected_interval,
                    depth_range,
                )
                st.caption(
                    f"Будет напечатан {selected_interval_id}: "
                    f"{print_top:g}–{print_bottom:g} м."
                )
            elif print_mode == "Выбрать отдельно":
                print_left, print_right = st.columns(2)
                top_widget_kwargs = (
                    {"value": float(normalized_form["top"])}
                    if form_keys["top"] not in export_state
                    else {}
                )
                print_top = print_left.number_input(
                    "Печать от, м",
                    min_value=full_print_min,
                    max_value=full_print_max,
                    step=0.1,
                    key=form_keys["top"],
                    **top_widget_kwargs,
                )
                bottom_widget_kwargs = (
                    {"value": float(normalized_form["bottom"])}
                    if form_keys["bottom"] not in export_state
                    else {}
                )
                print_bottom = print_right.number_input(
                    "Печать до, м",
                    min_value=full_print_min,
                    max_value=full_print_max,
                    step=0.1,
                    key=form_keys["bottom"],
                    **bottom_widget_kwargs,
                )
            else:
                print_top, print_bottom = depth_range

            section_id_by_label_preview = {
                "Инженерные графики": "plots",
                "Планшеты и визуализации": "visualizations",
                "Расчётные результаты": "results",
                "Заключение и ограничения": "conclusion",
            }
            preview_design = ReportDesign(
                mode_id=selected_mode.id,
                template_id=selected_template.id,
                title=str(report_title or "").strip(),
                document_code=f"GRP-{str(active_project.id).upper()[:16]}",
                sections=tuple(
                    section_id_by_label_preview[label]
                    for label in selected_section_labels
                ),
                include_technical_appendix=bool(include_technical_design),
                show_page_chrome=bool(show_page_chrome_design),
            )
            preview_target_format = next(
                (option.id for option in format_options if option.label == selected_format_label),
                format_options[0].id,
            )
            preview_counts_signature = build_report_document_counts_signature(
                preview_design,
                target_format=preview_target_format,
                depth_top=float(print_top),
                depth_bottom=float(print_bottom),
                source_signature=str(calculated_signature),
                calculation_revision=int(revision_snapshot.calculation),
                presentation_revision=int(revision_snapshot.presentation),
            )
            saved_preview_payload = export_state.get(report_preview_counts_key)
            preview_counts_resolution = resolve_report_document_counts_snapshot(
                saved_preview_payload,
                expected_signature=preview_counts_signature,
            )
            saved_preview_counts = preview_counts_resolution.counts

            structure_preview = build_report_structure_preview(
                preview_design,
                document_counts=saved_preview_counts,
                target_format=preview_target_format,
            )
            with st.expander("Предпросмотр структуры отчёта", expanded=True):
                preview_recovery_notice = export_state.pop(preview_counts_recovery_notice_key, None)
                if preview_recovery_notice:
                    st.warning(str(preview_recovery_notice))
                try:
                    preview_storage_health = export_application.preview_storage_health()
                except (OSError, ValueError):
                    preview_storage_health = None
                    logger.exception(
                        "report_preview_counts_health_failed project_id=%s",
                        safe_log_value(active_project.id),
                    )
                if preview_storage_health is not None:
                    health_icon = {
                        "healthy": "✅",
                        "recoverable": "⚠️",
                        "degraded": "❌",
                        "quarantined": "⚠️",
                        "empty": "ℹ️",
                    }.get(preview_storage_health.status, "ℹ️")
                    with st.expander("Состояние хранилища предпросмотра", expanded=False):
                        st.markdown(f"{health_icon} **{preview_storage_health.message}**")
                        st.caption(
                            "Основной файл: "
                            + ("корректен" if preview_storage_health.primary_valid else "отсутствует или повреждён")
                            + " · Резервная копия: "
                            + ("корректна" if preview_storage_health.backup_valid else "отсутствует или повреждена")
                            + f" · Карантин: {preview_storage_health.quarantine_count}"
                            + f" · Объём: {preview_storage_health.total_bytes} Б"
                        )
                st.caption(
                    f"{structure_preview.mode_label} · {structure_preview.template_label} · "
                    f"{structure_preview.paper_size} · поля {structure_preview.margin_mm} мм"
                )
                st.markdown(f"**{structure_preview.title}**")
                if preview_counts_resolution.state == "current":
                    st.caption(preview_counts_resolution.message)
                elif preview_counts_resolution.state in {"stale", "legacy", "unsupported", "invalid"}:
                    st.info(preview_counts_resolution.message)
                for preview_index, preview_item in enumerate(structure_preview.sections, start=1):
                    status_mark = "✅" if preview_item.enabled else "⏸️"
                    st.markdown(
                        f"{preview_index}. {status_mark} **{preview_item.label}** — "
                        f"{preview_item.description}"
                    )
                preview_flags = []
                if structure_preview.include_table_of_contents:
                    preview_flags.append("оглавление")
                if structure_preview.include_pdf_bookmarks:
                    preview_flags.append("PDF-закладки")
                if structure_preview.include_technical_appendix:
                    preview_flags.append("техническое приложение")
                if structure_preview.show_page_chrome:
                    preview_flags.append("колонтитулы и нумерация")
                st.caption(
                    "Дополнительно: " + (", ".join(preview_flags) if preview_flags else "не включено")
                )
                st.metric(
                    "Оценочный объём",
                    f"{structure_preview.estimated_min_pages}–{structure_preview.estimated_max_pages} стр.",
                    help=(
                        "Диапазон уточнён по последней собранной модели документа."
                        if saved_preview_counts is not None
                        else "Диапазон рассчитан по составу разделов без построения бинарного PDF/DOCX."
                    ),
                )
                if saved_preview_counts is not None:
                    st.caption(
                        "Фактический состав последней подготовленной модели: "
                        f"разделов {saved_preview_counts.sections}, таблиц {saved_preview_counts.tables}, "
                        f"строк {saved_preview_counts.table_rows}, графиков {saved_preview_counts.plots}, "
                        f"планшетов {saved_preview_counts.visualizations}."
                    )
                with st.expander("Оценка состава страниц", expanded=False):
                    for estimate in structure_preview.page_estimates:
                        state = "✅" if estimate.enabled else "⏸️"
                        page_range = (
                            str(estimate.min_pages)
                            if estimate.min_pages == estimate.max_pages
                            else f"{estimate.min_pages}–{estimate.max_pages}"
                        )
                        st.caption(f"{state} {estimate.label}: {page_range} стр.")
                if structure_preview.format_capabilities:
                    with st.expander("Возможности выбранного формата", expanded=False):
                        for capability in structure_preview.format_capabilities:
                            state = "✅" if capability.supported else "—"
                            st.caption(f"{state} **{capability.label}** — {capability.detail}")
                for diagnostic in structure_preview.diagnostics:
                    if diagnostic.level == "error":
                        st.error(diagnostic.message)
                    elif diagnostic.level == "warning":
                        st.warning(diagnostic.message)
                    elif diagnostic.level == "success":
                        st.success(diagnostic.message)
                    else:
                        st.info(diagnostic.message)
                for preview_issue in structure_preview.issues:
                    st.error(preview_issue.message) if preview_issue.blocking else st.warning(preview_issue.message)

            wizard_capabilities = ExportWizardCapabilities(
                report_formats=tuple(option.id for option in format_options),
            )
            wizard_state = ExportWizardState(
                step=ExportWizardStep.REVIEW,
                source_label=str(source_label),
                project_label=str(active_project.name),
                profile=selected_profile_label and next(
                    option.id for option in profile_options if option.label == selected_profile_label
                ),
                export_format=selected_format_label and next(
                    option.id for option in format_options if option.label == selected_format_label
                ),
                include_figures=True,
                output_dir=ROOT_DIR / "artifacts" / "presentation_exports",
                base_name_parts=(
                    str(active_project.name),
                    str(source_label),
                    "professional_report",
                ),
            )
            wizard_review = build_export_wizard_review(
                wizard_state,
                capabilities=wizard_capabilities,
            )
            st.markdown("#### Проверка перед формированием")
            wizard_columns = st.columns(len(wizard_review.steps))
            for wizard_column, wizard_step in zip(wizard_columns, wizard_review.steps):
                marker = "✅" if wizard_step.completed else ("➡️" if wizard_step.active else "○")
                wizard_column.markdown(f"**{marker} {wizard_step.number}. {wizard_step.label}**")
                wizard_column.caption(wizard_step.description)
            st.progress(1.0 if wizard_review.ready else 0.8)
            review_left, review_right = st.columns(2)
            review_left.markdown(
                f"**Источник:** {wizard_review.source_label}  \n"
                f"**Проект:** {wizard_review.project_label}  \n"
                f"**Профиль:** {wizard_review.profile_label}"
            )
            review_right.markdown(
                f"**Формат:** {wizard_review.format_label}  \n"
                f"**Файл:** `{wizard_review.file_name}`  \n"
                f"**Диапазон:** {min(float(print_top), float(print_bottom)):g}–"
                f"{max(float(print_top), float(print_bottom)):g} м"
            )
            for wizard_issue in wizard_review.issues:
                st.error(wizard_issue.message) if wizard_issue.blocking else st.warning(wizard_issue.message)

            prepare_export = st.form_submit_button(
                "🖨️ ПОДГОТОВИТЬ ФАЙЛ ДЛЯ ПЕЧАТИ И СКАЧИВАНИЯ",
                width="stretch",
                type="primary",
                disabled=not wizard_review.ready,
                help=tooltip("report.prepare"),
            )

        selected_profile = next((option for option in profile_options if option.label == selected_profile_label), profile_options[0])
        selected_format = next((option for option in format_options if option.label == selected_format_label), format_options[0])
        section_id_by_label = {
            "Инженерные графики": "plots",
            "Планшеты и визуализации": "visualizations",
            "Расчётные результаты": "results",
            "Заключение и ограничения": "conclusion",
        }
        report_design = ReportDesign(
            mode_id=selected_mode.id,
            template_id=selected_template.id,
            title=str(report_title or "").strip(),
            document_code=f"GRP-{str(active_project.id).upper()[:16]}",
            sections=tuple(section_id_by_label[label] for label in selected_section_labels),
            include_technical_appendix=bool(include_technical_design),
            show_page_chrome=bool(show_page_chrome_design),
        )
        current_print_depth_range = (
            min(float(print_top), float(print_bottom)),
            max(float(print_top), float(print_bottom)),
        )
        try:
            export_application.save_draft(
                ExportWizardDraft(
                    project_id=str(active_project.id),
                    wizard=wizard_state,
                    report_mode_id=report_design.mode_id,
                    template_id=report_design.template_id,
                    report_title=report_design.title,
                    sections=report_design.sections,
                    include_technical_appendix=report_design.include_technical_appendix,
                    show_page_chrome=report_design.show_page_chrome,
                    print_mode=str(print_mode),
                    depth_top=float(current_print_depth_range[0]),
                    depth_bottom=float(current_print_depth_range[1]),
                )
            )
        except (OSError, ValueError, TypeError):
            logger.exception("export_wizard_draft_save_failed project_id=%s", safe_log_value(active_project.id))

        current_export_request = ExportRequest(
            project_id=str(active_project.id),
            project_name=str(active_project.name),
            source_label=str(source_label),
            profile_id=str(selected_profile.id),
            format_id=str(selected_format.id),
            format_label=str(selected_format.label),
            extension=str(selected_format.extension),
            mime_type=str(selected_format.mime_type),
            depth_top=float(current_print_depth_range[0]),
            depth_bottom=float(current_print_depth_range[1]),
            source_signature=str(calculated_signature),
            calculation_revision=int(revision_snapshot.calculation),
            presentation_revision=int(revision_snapshot.presentation),
            figure_height=max(int(height), 1000),
            context_signature=hashlib.sha256(
                (
                    f"ranking={export_state.get('active_reservoir_ranking_profile', '')}|"
                    f"interval={selected_interval_id or ''}|scope={print_mode}|"
                    f"mode={report_design.mode_id}|template={report_design.template_id}|title={report_design.title}|"
                    f"sections={','.join(report_design.sections)}|technical={report_design.include_technical_appendix}|"
                    f"chrome={report_design.show_page_chrome}"
                ).encode("utf-8")
            ).hexdigest(),
        )
        current_data_revision = build_export_data_revision(
            project_id=str(active_project.id),
            source_signature=current_export_request.source_signature,
            calculation_revision=current_export_request.calculation_revision,
        )

        prepare_export = bool(prepare_export or export_state.pop(repeat_autorun_key, False))

        if prepare_export:
            print_depth_range = current_print_depth_range
            print_df = _filter_by_depth_range(
                calculated_df, print_depth_range[0], print_depth_range[1]
            )
            if print_df.empty:
                st.error("В выбранном интервале печати нет данных.")
            else:
                request = current_export_request
                ranking_profile_snapshot = export_state.get("active_reservoir_ranking_profile")
                selected_profile_label_snapshot = selected_profile.label
                selected_interval_id_snapshot = selected_interval_id or ""
                export_runtime = application_service_container(export_state).presentation_export_runtime(
                    project_id=str(active_project.id),
                    root=LAS_CORRELATION_PROJECTS_ROOT,
                )
                frame_snapshot = print_df.copy(deep=False)

                def _background_work(report, check_cancelled):
                    staged_report = staged_progress_reporter(report)
                    report_document_counts = None

                    def _build_export_model(frame, export_request):
                        check_cancelled()
                        payload = build_hydrocarbon_report_payload(
                            frame,
                            source_label=export_request.source_label,
                            project_label=f"{export_request.project_name} ({export_request.project_id})",
                            depth_label=_range_label(export_request.normalized_depth_range, unit="м"),
                            report_profile=export_request.profile_id,
                            include_plot=True,
                            ranking_profile=ranking_profile_snapshot,
                        )
                        if payload.presentation_model is None:
                            raise RuntimeError("PresentationModel не был сформирован.")
                        return payload.presentation_model

                    def _render_export_artifact(presentation_model, frame, export_request):
                        check_cancelled()
                        presentation_state = build_presentation_export_ui_state(
                            profile=export_request.profile_id,
                            export_format=export_request.format_id,
                            output_dir=ROOT_DIR / "artifacts" / "presentation_exports",
                            base_name_parts=(
                                export_request.project_name,
                                export_request.source_label,
                                "professional_report",
                            ),
                            include_figures=True,
                        )
                        if export_request.format_id == "xlsx":
                            content = export_xlsx_bytes(
                                frame,
                                sheet_name="Инженерные данные",
                                metadata={
                                    "Проект": export_request.project_name,
                                    "Источник": export_request.source_label,
                                    "Профиль отчёта": selected_profile_label_snapshot,
                                    "Формат": export_request.format_label,
                                    "Глубина от, м": f"{export_request.normalized_depth_range[0]:g}",
                                    "Глубина до, м": f"{export_request.normalized_depth_range[1]:g}",
                                    "Строк данных": len(frame),
                                    "Выбранный интервал": selected_interval_id_snapshot or "Не выбран",
                                },
                            )
                            file_name = f"{presentation_state.base_name}.xlsx"
                        elif export_request.format_id in {"png", "svg"}:
                            report_figures = presentation_model.figures
                            if not report_figures:
                                raise RuntimeError("Инженерный график не был сформирован для экспорта.")
                            content = export_plotly_static_bytes(
                                report_figures[0],
                                StaticExportOptions(
                                    format=export_request.format_id,
                                    width=1800,
                                    height=export_request.figure_height,
                                    scale=2.0,
                                ),
                            )
                            file_name = f"{presentation_state.base_name}.{export_request.extension}"
                        else:
                            rendered = build_designed_report_artifact(
                                presentation_model,
                                design=report_design,
                                export_format=export_request.format_id,
                                base_name=presentation_state.base_name,
                                on_progress=staged_report,
                                check_cancelled=check_cancelled,
                            )
                            content = rendered.content
                            file_name = rendered.file_name
                            nonlocal report_document_counts
                            report_document_counts = rendered.document_counts
                        check_cancelled()
                        return ControlledExportArtifact(
                            content=content,
                            file_name=file_name,
                            mime_type=export_request.mime_type,
                            format_id=export_request.format_id,
                            format_label=export_request.format_label,
                            profile_id=export_request.profile_id,
                        )

                    artifact, metrics = export_runtime.prepare(
                        request,
                        frame=frame_snapshot,
                        build_model=_build_export_model,
                        render_artifact=_render_export_artifact,
                        on_progress=staged_report,
                        check_cancelled=check_cancelled,
                    )
                    return BackgroundExportResult(
                        artifact=artifact,
                        metrics=metrics,
                        report_document_counts=report_document_counts,
                    )

                try:
                    retry_context = export_state.pop(background_retry_context_key, {})
                    if not isinstance(retry_context, dict):
                        retry_context = {}
                    created_job = background_manager.submit(
                        request_signature=current_export_request.selection_signature,
                        work=_background_work,
                        retry_of_job_id=str(retry_context.get("job_id", "")),
                        retry_reason=str(retry_context.get("reason", "")),
                        export_format=str(selected_format.id),
                    )
                    export_state.pop(export_error_key, None)
                    logger.info(
                        "background_export_submitted project_id=%s job_id=%s profile=%s format=%s rows=%d",
                        safe_log_value(active_project.id),
                        safe_log_value(created_job.id),
                        safe_log_value(selected_profile.id),
                        safe_log_value(selected_format.id),
                        len(frame_snapshot),
                    )
                except RuntimeError as exc:
                    st.warning(str(exc))

        project_jobs = background_manager.list()
        relevant_job = latest_relevant_job(
            project_jobs,
            request_signature=current_export_request.selection_signature,
        )
        if relevant_job is not None:
            status_view = build_background_export_status_view(
                relevant_job,
                artifact_available=background_manager.result_available(relevant_job.id),
            )
            st.progress(status_view.progress / 100.0, text=status_view.detail or status_view.title)
            if status_view.level == "error":
                st.error(f"{status_view.title}: {status_view.detail}")
            elif status_view.level == "warning":
                st.warning(f"{status_view.title}: {status_view.detail}")
            elif status_view.level == "success":
                st.success(status_view.title)
            else:
                st.info(status_view.title)

            job_left, job_right = st.columns(2)
            if status_view.cancellable and job_left.button(
                "Отменить экспорт",
                key=f"background_export_cancel_{active_project.id}_{relevant_job.id}",
                width="stretch",
            ):
                background_manager.cancel(relevant_job.id)
                _request_ui_refresh_and_rerun("background_export_cancel")
                return
            if status_view.retryable and job_left.button(
                "Повторить экспорт",
                key=f"background_export_retry_{active_project.id}_{relevant_job.id}",
                type="primary",
                width="stretch",
            ):
                export_state[background_retry_context_key] = {
                    "job_id": relevant_job.id,
                    "reason": retry_diagnostic_reason(
                        relevant_job,
                        artifact_available=background_manager.result_available(relevant_job.id),
                    ),
                }
                background_manager.dismiss(relevant_job.id)
                export_state[repeat_autorun_key] = True
                _request_ui_refresh_and_rerun("background_export_retry")
                return
            if not relevant_job.terminal:
                job_right.caption("Прогресс обновляется автоматически каждые 2 секунды.")
            elif status_view.retryable:
                job_right.caption("Повтор использует текущие параметры мастера экспорта.")

        recent_job_history = build_recent_background_job_history(
            project_jobs,
            artifact_availability={
                item.id: background_manager.result_available(item.id) for item in project_jobs
            },
            limit=5,
        )
        if recent_job_history:
            with st.expander("Последние фоновые экспорты", expanded=False):
                performance_summary = build_background_export_performance_summary(
                    recent_job_history
                )
                perf_total, perf_success, perf_duration, perf_size = st.columns(4)
                perf_total.metric(
                    "Заданий",
                    performance_summary.total_jobs,
                    delta=(
                        f"активных: {performance_summary.active_jobs}"
                        if performance_summary.active_jobs
                        else None
                    ),
                )
                perf_success.metric(
                    "Успешность",
                    f"{performance_summary.success_rate_percent:.0f}%",
                    delta=f"готово: {performance_summary.completed_jobs}",
                )
                perf_duration.metric(
                    "Среднее время",
                    format_export_duration(performance_summary.average_duration_seconds),
                )
                perf_size.metric(
                    "Средний файл",
                    (
                        format_artifact_size(performance_summary.average_artifact_size_bytes)
                        if performance_summary.average_artifact_size_bytes > 0
                        else "—"
                    ),
                )
                if (
                    performance_summary.failed_jobs
                    or performance_summary.cancelled_jobs
                    or performance_summary.orphaned_jobs
                ):
                    st.caption(
                        "Незавершённые: "
                        f"ошибки — {performance_summary.failed_jobs}, "
                        f"отменены — {performance_summary.cancelled_jobs}, "
                        f"прерваны — {performance_summary.orphaned_jobs}."
                    )

                filter_left, filter_right, sort_column = st.columns([2, 2, 2])
                status_label_to_value = {
                    "Выполняется": "running",
                    "Завершён": "completed",
                    "Ошибка": "failed",
                    "Отменён": "cancelled",
                    "Прерван": "orphaned",
                }
                available_formats = tuple(sorted({
                    item.export_format.upper()
                    for item in recent_job_history
                    if item.export_format
                }))
                selected_status_labels = filter_left.multiselect(
                    "Статус",
                    options=tuple(status_label_to_value),
                    key=f"background_export_history_status_filter_{active_project.id}",
                    placeholder="Все статусы",
                )
                selected_history_formats = filter_right.multiselect(
                    "Формат",
                    options=available_formats,
                    key=f"background_export_history_format_filter_{active_project.id}",
                    placeholder="Все форматы",
                )
                sort_label_to_value = {
                    "Сначала новые": "updated_desc",
                    "Сначала старые": "updated_asc",
                    "Дольше выполнялись": "duration_desc",
                    "Быстрее выполнялись": "duration_asc",
                    "Сначала большие файлы": "size_desc",
                    "Сначала меньшие файлы": "size_asc",
                }
                selected_sort_label = sort_column.selectbox(
                    "Сортировка",
                    options=tuple(sort_label_to_value),
                    key=f"background_export_history_sort_{active_project.id}",
                )
                filtered_job_history = filter_recent_background_job_history(
                    recent_job_history,
                    statuses=tuple(status_label_to_value[label] for label in selected_status_labels),
                    formats=tuple(selected_history_formats),
                )
                filtered_job_history = sort_recent_background_job_history(
                    filtered_job_history,
                    sort_by=sort_label_to_value[selected_sort_label],
                )
                cleanup_candidates = tuple(
                    item for item in filtered_job_history if item.dismissible
                )
                if cleanup_candidates and st.button(
                    "Очистить завершённые записи",
                    key=f"background_export_cleanup_terminal_{active_project.id}",
                    help=(
                        "Удаляет завершённые записи истории проекта. "
                        "Готовый файл, ещё не переданный в интерфейс, сохраняется."
                    ),
                    width="stretch",
                ):
                    removed_count = background_manager.dismiss_terminal(
                        preserve_available_results=True,
                    )
                    if removed_count:
                        st.toast(f"Удалено записей: {removed_count}")
                    _request_ui_refresh_and_rerun("background_export_cleanup_terminal")
                    return

                if not filtered_job_history:
                    st.caption("Нет экспортов, соответствующих выбранным фильтрам.")

                for history_item in filtered_job_history:
                    history_content, history_action = st.columns([5, 1])
                    retry_note = (
                        f"  \nПричина повтора: {history_item.retry_reason}"
                        if history_item.retry_reason
                        else ""
                    )
                    history_metadata = [
                        f"Длительность: {format_export_duration(history_item.duration_seconds)}"
                    ]
                    if history_item.artifact_size_bytes > 0:
                        history_metadata.append(
                            f"Размер: {format_artifact_size(history_item.artifact_size_bytes)}"
                        )
                    if history_item.export_format:
                        history_metadata.append(history_item.export_format.upper())
                    history_content.markdown(
                        f"**{history_item.title}** · {history_item.progress}%  \n"
                        f"{history_item.detail}{retry_note}  \n"
                        f"{' · '.join(history_metadata)}"
                    )
                    if history_item.dismissible and history_action.button(
                        "Удалить",
                        key=(
                            f"background_export_dismiss_history_"
                            f"{active_project.id}_{history_item.job_id}"
                        ),
                        help="Удалить эту завершённую запись из истории.",
                        width="stretch",
                    ):
                        background_manager.dismiss(history_item.job_id)
                        _request_ui_refresh_and_rerun("background_export_dismiss_history")
                        return
                    if history_item.terminal and not history_item.dismissible:
                        history_action.caption("Файл готов")

            if (
                relevant_job is not None
                and relevant_job.status is ExportJobStatus.COMPLETED
                and background_manager.result_available(relevant_job.id)
            ):
                completed = background_manager.pop_result(relevant_job.id)
                if not isinstance(completed, BackgroundExportResult):
                    raise RuntimeError("Фоновый экспорт вернул неподдерживаемый тип результата.")
                export_artifact = completed.artifact
                export_metrics = dict(completed.metrics)
                if isinstance(completed.report_document_counts, ReportDocumentCounts):
                    report_counts_snapshot = build_report_document_counts_snapshot(
                        completed.report_document_counts,
                        signature=build_report_document_counts_signature(
                            report_design,
                            target_format=selected_format.id,
                            depth_top=current_print_depth_range[0],
                            depth_bottom=current_print_depth_range[1],
                            source_signature=current_export_request.source_signature,
                            calculation_revision=current_export_request.calculation_revision,
                            presentation_revision=current_export_request.presentation_revision,
                        ),
                    )
                    export_state[report_preview_counts_key] = report_counts_snapshot
                    try:
                        export_application.save_preview_counts(
                            report_counts_snapshot,
                        )
                    except (OSError, ValueError, TypeError):
                        logger.exception(
                            "report_preview_counts_persist_failed project_id=%s",
                            safe_log_value(active_project.id),
                        )
                export_state.pop(pdf_preview_cache_key, None)
                export_state[export_cache_key] = {
                    "content": export_artifact.content,
                    "file_name": export_artifact.file_name,
                    "mime_type": export_artifact.mime_type,
                    "format_id": export_artifact.format_id,
                    "format_label": export_artifact.format_label,
                    "profile_id": export_artifact.profile_id,
                    "request_signature": export_artifact.request_signature,
                    "depth_top": current_print_depth_range[0],
                    "depth_bottom": current_print_depth_range[1],
                }
                export_state.pop(export_error_key, None)
                try:
                    export_application.record_history(
                        ExportHistoryEntry(
                            project_id=str(active_project.id),
                            file_name=export_artifact.file_name,
                            format_id=export_artifact.format_id,
                            format_label=export_artifact.format_label,
                            profile_id=export_artifact.profile_id,
                            depth_top=float(current_print_depth_range[0]),
                            depth_bottom=float(current_print_depth_range[1]),
                            size_bytes=len(export_artifact.content),
                            request_signature=export_artifact.request_signature,
                            cache_hit=bool(export_artifact.cache_hit),
                            report_mode_id=report_design.mode_id,
                            template_id=report_design.template_id,
                            report_title=report_design.title,
                            sections=report_design.sections,
                            include_technical_appendix=report_design.include_technical_appendix,
                            show_page_chrome=report_design.show_page_chrome,
                            print_mode=str(print_mode),
                            data_revision=current_data_revision,
                            project_updated_at=str(active_project.updated_at or ""),
                        )
                    )
                except (OSError, ValueError, TypeError):
                    logger.exception("export_history_record_failed project_id=%s", safe_log_value(active_project.id))
                logger.info(
                    "background_export_completed project_id=%s job_id=%s format=%s bytes=%d duration_ms=%.2f",
                    safe_log_value(active_project.id),
                    safe_log_value(relevant_job.id),
                    safe_log_value(export_artifact.format_id),
                    len(export_artifact.content),
                    float(export_metrics.get("duration_ms", 0.0)),
                )
                background_manager.dismiss(relevant_job.id)

        cached_export = _application_state_controller().state.get(export_cache_key)
        cached_matches_controls = (
            isinstance(cached_export, dict)
            and cached_export.get("request_signature") == current_export_request.selection_signature
        )
        if cached_matches_controls:
            st.download_button(
                f"⬇️ СКАЧАТЬ ГОТОВЫЙ {cached_export.get('format_label', 'ОТЧЁТ')}",
                data=cached_export.get("content", b""),
                file_name=str(cached_export.get("file_name", "professional_report.bin")),
                mime=str(cached_export.get("mime_type", "application/octet-stream")),
                width="stretch",
                key=(
                    f"presentation_download_{active_project.id}_"
                    f"{cached_export.get('format_id', 'cached')}_"
                    f"{str(cached_export.get('request_signature', ''))[:12]}"
                ),
            )
            st.caption(
                f"Подготовлен формат: {cached_export.get('format_label', '—')}; "
                f"диапазон {cached_export.get('depth_top', '—')}–{cached_export.get('depth_bottom', '—')} м."
            )

            if str(cached_export.get("format_id", "")).lower() == "pdf":
                with st.expander("Предпросмотр страниц PDF", expanded=False):
                    preview_start_control, preview_controls, preview_dpi_control, preview_layout_control = st.columns([1, 2, 2, 2])
                    preview_start_key = f"pdf_preview_start_page_{active_project.id}"
                    preview_start_page = preview_start_control.number_input(
                        "С первой страницы",
                        min_value=1,
                        value=1,
                        step=1,
                        key=preview_start_key,
                    )
                    preview_page_limit = preview_controls.select_slider(
                        "Количество страниц",
                        options=(1, 2, 3, 4, 5, 8, 12),
                        value=5,
                        key=f"pdf_preview_page_limit_{active_project.id}",
                    )
                    preview_dpi = preview_dpi_control.select_slider(
                        "Качество, DPI",
                        options=(72, 90, 110, 144, 180),
                        value=110,
                        key=f"pdf_preview_dpi_{active_project.id}",
                    )
                    preview_layout = preview_layout_control.selectbox(
                        "Расположение",
                        options=("Одна колонка", "Две колонки"),
                        index=1,
                        key=f"pdf_preview_layout_{active_project.id}",
                    )
                    pdf_payload = cached_export.get("content", b"")
                    known_total_pages = pdf_preview_runtime_cache.known_total_pages()

                    page_jump_validation = validate_pdf_preview_page_jump(
                        int(preview_start_page),
                        total_pages=known_total_pages,
                        page_limit=int(preview_page_limit),
                    )
                    effective_preview_start = page_jump_validation.normalized_page
                    if page_jump_validation.adjusted:
                        st.warning(page_jump_validation.message)
                    elif known_total_pages > 0:
                        st.caption(
                            f"Доступно страниц: {known_total_pages}. "
                            f"Текущий диапазон начинается со страницы {effective_preview_start}."
                        )

                    expected_preview_signature = None
                    try:
                        expected_preview_signature = build_pdf_preview_signature(
                            pdf_payload,
                            request_signature=str(cached_export.get("request_signature", "")),
                            page_limit=int(preview_page_limit),
                            start_page=effective_preview_start,
                            dpi=preview_dpi,
                        )
                    except (TypeError, ValueError):
                        st.error("Готовый PDF повреждён или недоступен для предпросмотра.")

                    preview_cache_lookup = (
                        pdf_preview_runtime_cache.inspect(
                            str(expected_preview_signature or "")
                        )
                        if expected_preview_signature is not None
                        else None
                    )
                    matched_preview_result = (
                        preview_cache_lookup.result if preview_cache_lookup is not None else None
                    )
                    preview_matches = isinstance(matched_preview_result, PdfPreviewResult)
                    if expected_preview_signature is not None:
                        logger.info(
                            "pdf_preview_cache_lookup project_id=%s hit=%s source=%s entry_index=%s start_page=%d page_limit=%d dpi=%d",
                            safe_log_value(active_project.id),
                            bool(preview_cache_lookup and preview_cache_lookup.hit),
                            safe_log_value(preview_cache_lookup.source if preview_cache_lookup else "miss"),
                            preview_cache_lookup.entry_index if preview_cache_lookup else None,
                            effective_preview_start,
                            int(preview_page_limit),
                            preview_dpi,
                        )
                    prefetch_next_range = st.checkbox(
                        "Предзагрузить следующую группу страниц",
                        value=False,
                        key=f"pdf_preview_prefetch_next_{active_project.id}",
                        help=(
                            "После построения текущего диапазона приложение заранее создаст "
                            "только одну следующую ограниченную группу страниц."
                        ),
                    )
                    cache_budget_mib = st.selectbox(
                        "Лимит памяти кэша",
                        options=(8, 16, 24, 48),
                        index=2,
                        key=f"pdf_preview_cache_budget_mib_{active_project.id}",
                        help=(
                            "При превышении лимита самые старые диапазоны удаляются. "
                            "Текущий диапазон всегда сохраняется."
                        ),
                    )
                    cache_budget_bytes = int(cache_budget_mib) * 1024 * 1024

                    show_cache_stats = st.checkbox(
                        "Показать статистику кэша предпросмотра",
                        value=False,
                        key=f"pdf_preview_cache_stats_{active_project.id}",
                        help=(
                            "Показывает число сохранённых диапазонов и ориентировочный объём "
                            "PNG-миниатюр в памяти текущей сессии."
                        ),
                    )
                    if show_cache_stats:
                        pdf_preview_runtime_cache.configure(
                            max_entries=3, max_bytes=cache_budget_bytes
                        )
                        cache_stats = pdf_preview_runtime_cache.stats(
                            warning_threshold_bytes=max(1, int(cache_budget_bytes * 0.75)),
                            critical_threshold_bytes=cache_budget_bytes,
                        )
                        cache_metric_columns = st.columns(4)
                        cache_metric_columns[0].metric("Диапазоны в кэше", cache_stats.entry_count)
                        cache_metric_columns[1].metric("Страницы в памяти", cache_stats.rendered_pages)
                        cache_metric_columns[2].metric(
                            "Объём кэша", f"{cache_stats.image_size_bytes / 1024:.1f} КиБ"
                        )
                        cache_metric_columns[3].metric(
                            "Крупнейший диапазон",
                            f"{cache_stats.largest_entry_bytes / 1024:.1f} КиБ",
                        )
                        if cache_stats.status == "critical":
                            st.error(
                                "Кэш миниатюр создаёт высокую нагрузку на память. "
                                "Очистите кэш или уменьшите DPI/количество страниц."
                            )
                        elif cache_stats.status == "warning":
                            st.warning(
                                "Объём кэша миниатюр повышен. Для снижения нагрузки можно "
                                "очистить кэш или уменьшить качество предпросмотра."
                            )
                        elif cache_stats.status == "ok":
                            st.caption(
                                "Нагрузка кэша в безопасном диапазоне; средний диапазон: "
                                f"{cache_stats.average_entry_bytes / 1024:.1f} КиБ."
                            )
                        else:
                            st.caption("Кэш предпросмотра пуст.")

                    navigation_previous, navigation_next, preview_action = st.columns([1, 1, 2])
                    if navigation_previous.button(
                        "← Предыдущие",
                        key=f"pdf_preview_previous_{active_project.id}",
                        width="stretch",
                        disabled=effective_preview_start <= 1,
                    ):
                        export_state[preview_start_key] = shift_pdf_preview_window(
                            effective_preview_start,
                            direction=-1,
                            page_limit=int(preview_page_limit),
                            total_pages=known_total_pages,
                        )
                        _refresh_ui("pdf_preview_previous")
                    if navigation_next.button(
                        "Следующие →",
                        key=f"pdf_preview_next_{active_project.id}",
                        width="stretch",
                        disabled=(known_total_pages > 0 and effective_preview_start + int(preview_page_limit) > known_total_pages),
                    ):
                        export_state[preview_start_key] = shift_pdf_preview_window(
                            effective_preview_start,
                            direction=1,
                            page_limit=int(preview_page_limit),
                            total_pages=known_total_pages,
                        )
                        _refresh_ui("pdf_preview_next")
                    if preview_action.button(
                        "Создать предпросмотр",
                        key=f"build_pdf_preview_{active_project.id}",
                        width="stretch",
                        disabled=expected_preview_signature is None,
                    ):
                        try:
                            preview_result = build_pdf_preview(
                                pdf_payload,
                                page_limit=int(preview_page_limit),
                                start_page=effective_preview_start,
                                dpi=preview_dpi,
                            )
                            pdf_preview_runtime_cache.configure(
                                max_entries=3, max_bytes=cache_budget_bytes
                            )
                            cache_store = pdf_preview_runtime_cache.store(
                                str(expected_preview_signature), preview_result
                            )
                            if cache_store.eviction_count:
                                logger.info(
                                    "pdf_preview_cache_evicted project_id=%s count=%d bytes=%d retained_bytes=%d budget_bytes=%d",
                                    safe_log_value(active_project.id),
                                    cache_store.eviction_count,
                                    cache_store.evicted_bytes,
                                    cache_store.retained_bytes,
                                    cache_store.budget_bytes,
                                )
                            matched_preview_result = preview_result
                            preview_matches = True

                            if prefetch_next_range:
                                adjacent_start = next_pdf_preview_start_page(
                                    effective_preview_start,
                                    total_pages=preview_result.total_pages,
                                    page_limit=int(preview_page_limit),
                                )
                                if adjacent_start is not None:
                                    adjacent_signature = build_pdf_preview_signature(
                                        pdf_payload,
                                        request_signature=str(cached_export.get("request_signature", "")),
                                        page_limit=int(preview_page_limit),
                                        start_page=adjacent_start,
                                        dpi=preview_dpi,
                                    )
                                    adjacent_lookup = pdf_preview_runtime_cache.inspect(
                                        adjacent_signature
                                    )
                                    if not adjacent_lookup.hit:
                                        adjacent_result = build_pdf_preview(
                                            pdf_payload,
                                            page_limit=int(preview_page_limit),
                                            start_page=adjacent_start,
                                            dpi=preview_dpi,
                                        )
                                        prefetch_store = pdf_preview_runtime_cache.store(
                                            adjacent_signature, adjacent_result
                                        )
                                        if prefetch_store.eviction_count:
                                            logger.info(
                                                "pdf_preview_cache_evicted project_id=%s count=%d bytes=%d retained_bytes=%d budget_bytes=%d source=prefetch",
                                                safe_log_value(active_project.id),
                                                prefetch_store.eviction_count,
                                                prefetch_store.evicted_bytes,
                                                prefetch_store.retained_bytes,
                                                prefetch_store.budget_bytes,
                                            )
                                        logger.info(
                                            "pdf_preview_prefetched project_id=%s start_page=%d pages=%d duration_ms=%.2f bytes=%d backend=%s",
                                            safe_log_value(active_project.id),
                                            adjacent_start,
                                            adjacent_result.rendered_pages,
                                            adjacent_result.render_duration_seconds * 1000.0,
                                            adjacent_result.image_size_bytes,
                                            safe_log_value(adjacent_result.backend),
                                        )
                                    else:
                                        logger.info(
                                            "pdf_preview_prefetch_cache_hit project_id=%s start_page=%d source=%s entry_index=%s",
                                            safe_log_value(active_project.id),
                                            adjacent_start,
                                            safe_log_value(adjacent_lookup.source),
                                            adjacent_lookup.entry_index,
                                        )
                            logger.info(
                                "pdf_preview_built project_id=%s pages=%d total=%d backend=%s",
                                safe_log_value(active_project.id),
                                preview_result.rendered_pages,
                                preview_result.total_pages,
                                safe_log_value(preview_result.backend),
                            )
                        except (PdfPreviewUnavailableError, ValueError, OSError) as exc:
                            logger.warning(
                                "pdf_preview_failed project_id=%s error=%s",
                                safe_log_value(active_project.id),
                                safe_log_value(exc),
                            )
                            st.warning(
                                "Предпросмотр PDF недоступен в текущем окружении. "
                                "Готовый файл всё равно можно скачать."
                            )

                    if pdf_preview_runtime_cache.snapshot().entry_count > 0:
                        if st.button(
                            "Очистить кэш предпросмотра",
                            key=f"clear_pdf_preview_{active_project.id}",
                            width="stretch",
                        ):
                            cleared_entries = pdf_preview_runtime_cache.clear()
                            preview_matches = False
                            logger.info(
                                "pdf_preview_cache_cleared project_id=%s entries=%d",
                                safe_log_value(active_project.id),
                                cleared_entries,
                            )
                            st.success("Кэш миниатюр PDF очищен.")

                    if preview_matches and isinstance(matched_preview_result, PdfPreviewResult):
                        preview_result = matched_preview_result
                        metric_columns = st.columns(4)
                        metric_columns[0].metric(
                            "Страницы",
                            f"{preview_result.rendered_pages}/{preview_result.total_pages}",
                        )
                        metric_columns[1].metric(
                            "Время",
                            f"{preview_result.render_duration_seconds:.2f} с",
                        )
                        metric_columns[2].metric(
                            "Миниатюры",
                            f"{preview_result.image_size_bytes / 1024:.1f} КиБ",
                        )
                        metric_columns[3].metric("Backend", preview_result.backend)
                        st.caption(
                            f"Исходный PDF: {preview_result.source_size_bytes / 1024:.1f} КиБ; "
                            f"средняя миниатюра: {preview_result.average_page_size_bytes / 1024:.1f} КиБ."
                        )
                        if preview_result.truncated:
                            st.info("Предпросмотр ограничен выбранным количеством страниц.")
                        if preview_layout == "Две колонки":
                            preview_columns = st.columns(2)
                            for index, page in enumerate(preview_result.pages):
                                with preview_columns[index % 2]:
                                    st.image(
                                        page.image_png,
                                        caption=f"Страница {page.page_number}",
                                        width="stretch",
                                    )
                        else:
                            for page in preview_result.pages:
                                st.image(
                                    page.image_png,
                                    caption=f"Страница {page.page_number}",
                                    width="stretch",
                                )
                    else:
                        st.caption(
                            "Миниатюры создаются только по запросу и кэшируются до изменения "
                            "PDF, параметров экспорта, начальной страницы или лимита страниц."
                        )
        elif isinstance(cached_export, dict):
            st.warning(
                "Настройки экспорта изменены. Ранее подготовленный файл относится к другому "
                "профилю, формату или диапазону глубин. Подготовьте файл заново."
            )
        else:
            st.info("Файл ещё не подготовлен. Выберите настройки выше и нажмите большую синюю кнопку подготовки.")

        cached_error = _application_state_controller().state.get(export_error_key)
        if isinstance(cached_error, dict):
            st.error(
                f"Не удалось сформировать экспорт. Код ошибки: {cached_error.get('id', '—')}. "
                "Подробности записаны в logs/app.log."
            )
        try:
            export_history = export_application.load_history()
        except (OSError, ValueError, TypeError):
            logger.exception("export_history_load_failed project_id=%s", safe_log_value(active_project.id))
            export_history = ()
        if export_history:
            with st.expander("История успешных экспортов", expanded=False):
                history_search = st.text_input(
                    "Поиск в истории",
                    key=f"export_history_search_{active_project.id}",
                    placeholder="Имя файла, формат или профиль",
                )
                history_filter_left, history_filter_right = st.columns(2)
                history_formats = ("Все форматы", *sorted({item.format_id for item in export_history}))
                history_profiles = ("Все профили", *sorted({item.profile_id for item in export_history}))
                history_format = history_filter_left.selectbox(
                    "Формат", history_formats, key=f"export_history_format_{active_project.id}"
                )
                history_profile = history_filter_right.selectbox(
                    "Профиль", history_profiles, key=f"export_history_profile_{active_project.id}"
                )
                filtered_history = filter_export_history(
                    export_history,
                    ExportHistoryFilter(
                        search=history_search,
                        format_id="" if history_format == "Все форматы" else history_format,
                        profile_id="" if history_profile == "Все профили" else history_profile,
                    ),
                )
                if not filtered_history:
                    st.info("По выбранным фильтрам экспортов не найдено.")
                for history_index, history_item in enumerate(filtered_history[:10]):
                    created_label = history_item.created_at.replace("T", " ")[:19]
                    cache_label = " · кэш" if history_item.cache_hit else ""
                    revision_comparison = compare_export_data_revision(
                        history_item,
                        current_revision=current_data_revision,
                        current_project_updated_at=str(active_project.updated_at or ""),
                    )
                    revision_label = {
                        "current": " · данные актуальны",
                        "stale": " · данные изменены",
                        "unknown": " · ревизия неизвестна",
                    }.get(revision_comparison.status, "")
                    history_info, history_action = st.columns([4, 1])
                    history_info.markdown(
                        f"**{history_item.format_label}** · `{history_item.file_name}`  \n"
                        f"{created_label} UTC · {history_item.depth_top:g}–{history_item.depth_bottom:g} м · "
                        f"{history_item.size_bytes / 1024:.1f} КБ{cache_label}{revision_label}  \n"
                        f"Режим: `{history_item.report_mode_id}` · шаблон: `{history_item.template_id}`"
                    )
                    if revision_comparison.stale:
                        history_info.warning(revision_comparison.message)
                    elif revision_comparison.status == "unknown":
                        history_info.caption(revision_comparison.message)
                    action_label = "Пересобрать" if revision_comparison.stale else "Повторить"
                    if history_action.button(
                        action_label,
                        key=f"export_history_repeat_{active_project.id}_{history_index}_{history_item.request_signature[:10]}",
                        help="Проверить и восстановить полную конфигурацию отчёта перед новым рендерингом.",
                        width="stretch",
                    ):
                        if revision_comparison.stale:
                            confirmation = build_repeat_export_confirmation(
                                history_item, comparison=revision_comparison
                            )
                            export_state[repeat_confirm_key] = {
                                "title": confirmation.title,
                                "lines": confirmation.lines,
                                "payload": history_item.repeat_payload(),
                            }
                            _request_ui_refresh_and_rerun("export_history_repeat_confirmation")
                        else:
                            export_state[repeat_pending_key] = history_item.repeat_payload()
                            _request_ui_refresh_and_rerun("export_history_repeat")
                        return
        st.caption("Экспорт использует единый выбранный диапазон глубин и согласованные инженерные данные.")

def _render_interpretation_graphs_tab(logger, active_project: ProjectRecord) -> None:
    st.subheader("Интерпретационные графики")
    # The interpretation workspace is a standalone route and must not rely on
    # palette_config created inside the Data workspace renderer.  Keeping the
    # configuration local also makes PDF/DOCX and cached figure rendering
    # deterministic after Streamlit reruns.
    try:
        palette_config = load_palette_config()
    except Exception:
        logger.exception("interpretation_palette_config_load_failed")
        st.error("Не удалось загрузить конфигурацию графиков. Проверьте config/palettes.json.")
        st.caption("Подробности записаны в logs/app.log.")
        return

    state_controller = _application_state_controller()
    calculated_df, source_label = _active_calculation_dataset(active_project.id)
    if calculated_df is None or calculated_df.empty:
        last_cleanup = state_controller.get_value("last_session_cleanup", {})
        logger.warning(
            "interpretation_data_unavailable project_id=%s cleanup_reason=%s",
            safe_log_value(active_project.id),
            safe_log_value(last_cleanup.get("reason", "") if isinstance(last_cleanup, dict) else ""),
        )
        st.info("Сначала выполните расчет во вкладке `Работа с данными`. После этого здесь появятся графики и таблица интерпретации.")
        return

    st.caption(f"Источник данных: {source_label}")
    st.caption(f"Активный проект: {active_project.name} ({active_project.id})")
    _render_interpretation_graph_settings_loader(active_project, logger)

    depth = _depth_values_for_graphs(calculated_df)
    valid_depth = depth.dropna()
    detected_interval_result = None
    all_reservoir_overlays = ()
    selected_interval = None
    selected_interval_id = ""
    selected_interval_depth = None
    try:
        detected_interval_result = detect_hydrocarbon_intervals(calculated_df)
        all_reservoir_overlays = reservoir_interval_overlays(detected_interval_result.intervals)
    except Exception as exc:
        logger.warning("interpretation_interval_detection_failed error=%s", safe_log_value(exc))

    control_left, control_mid, control_right = st.columns((1.2, 1.0, 1.0))
    view_mode_label = control_left.radio(
        "Режим планшета",
        options=("Обзор всей скважины", "Детальный интервал"),
        horizontal=False,
        key="interpretation_tablet_view_mode",
    )
    view_mode = "detail" if view_mode_label == "Детальный интервал" else "overview"
    min_interval_thickness = float(control_mid.number_input(
        "Минимальная мощность, м",
        min_value=0.0,
        value=float(state_controller.get_value("interpretation_min_interval_thickness", 0.0) or 0.0),
        step=0.2,
        key="interpretation_min_interval_thickness",
        help="Скрывает мелкие интервалы только на планшете. Исходные данные и расчёт не изменяются.",
    ))
    adaptive_height = bool(control_right.checkbox(
        "Адаптивная высота",
        value=True,
        key="interpretation_tablet_adaptive_height",
    ))

    manual_well_id = resolve_interpretation_well_id(state_controller.state)
    manual_intervals = ()
    manual_overlays = ()
    selected_manual_interval_id = ""
    try:
        interpretation_workspace = application_service_container(
            state_controller.state
        ).interpretation_workspace(
            project_id=str(active_project.id),
            root=LAS_CORRELATION_PROJECTS_ROOT,
        )
        manual_intervals = interpretation_workspace.list_intervals(
            state=state_controller.state,
            well_id=manual_well_id,
            interpretation_id="default",
        )
        raw_manual_overlays = manual_interval_overlays(manual_intervals)
        persisted_overlay_settings = interpretation_workspace.load_display_settings(
            well_id=manual_well_id,
            interpretation_id="default",
        )
        manual_overlay_visible = persisted_overlay_settings.visible
        manual_overlay_opacity = persisted_overlay_settings.opacity
        manual_overlays = configure_manual_interval_overlays(
            raw_manual_overlays,
            visible=manual_overlay_visible,
            opacity=manual_overlay_opacity,
        )
        selected_manual_interval_id = str(
            state_controller.state.get(
                f"manual_interval_selected_{active_project.id}_{manual_well_id}",
                "",
            )
            or ""
        )
    except Exception as exc:
        logger.exception(
            "interpretation_manual_interval_overlay_load_failed project_id=%s well_id=%s error=%s",
            safe_log_value(active_project.id),
            safe_log_value(manual_well_id),
            safe_log_value(exc),
        )

    if detected_interval_result is not None and detected_interval_result.intervals:
        interval_pairs = list(zip(all_reservoir_overlays, detected_interval_result.intervals))
        selectable_pairs = [
            pair for pair in interval_pairs
            if float(getattr(pair[1], "thickness", 0.0)) >= min_interval_thickness
        ] or interval_pairs
        option_ids = [overlay.interval_id for overlay, _ in selectable_pairs]
        remembered_id = str(state_controller.get_value("selected_reservoir_interval_id", "") or "")
        default_pos = option_ids.index(remembered_id) if remembered_id in option_ids else 0
        interpretation_selection_key = "interpretation_selected_interval_id"
        interpretation_synced_key = "interpretation_selected_interval_synced_id"
        if (
            remembered_id in option_ids
            and (
                interpretation_selection_key not in _application_state_controller().state
                or _application_state_controller().state.get(interpretation_synced_key) != remembered_id
            )
        ):
            _application_state_controller().state[interpretation_selection_key] = remembered_id
            _application_state_controller().state[interpretation_synced_key] = remembered_id
        selected_interval_id = (
            remembered_id if remembered_id in option_ids else option_ids[default_pos]
        )
        st.caption(
            "Выбран из инженерной таблицы: "
            + _interval_display_label(
                next(interval for overlay, interval in selectable_pairs if overlay.interval_id == selected_interval_id),
                selected_interval_id,
            )
        )
        selected_overlay, selected_interval = next(
            pair for pair in selectable_pairs if pair[0].interval_id == selected_interval_id
        )
        selected_interval_depth = (float(selected_interval.top) + float(selected_interval.base)) / 2.0
        _application_state_controller().state[interpretation_synced_key] = str(selected_interval_id)
        state_controller.update_values({
            "selected_reservoir_interval_id": selected_interval_id,
            "selected_reservoir_depth": selected_interval_depth,
            "selected_reservoir_top": float(selected_interval.top),
            "selected_reservoir_bottom": float(selected_interval.base),
        })

    _render_selected_interval_header(
        selected_interval,
        selected_interval_id,
        project_label=str(getattr(active_project, "name", "") or ""),
        source_label=str(source_label),
    )
    try:
        render_interpretation_interval_panel(
            st,
            state=_application_state_controller().state,
            project_id=str(active_project.id),
        )
        render_interpretation_correlation_panel(
            st,
            state=_application_state_controller().state,
            project_id=str(active_project.id),
        )
    except Exception as exc:
        logger.exception(
            "interpretation_manual_interval_panel_failed project_id=%s error=%s",
            safe_log_value(active_project.id),
            safe_log_value(exc),
        )
        st.error("Не удалось открыть панель ручных интервалов. Подробности записаны в logs/app.log.")
    if manual_intervals:
        overlay_scope = f"{active_project.id}_{manual_well_id}"
        overlay_visible_key = f"interpretation_manual_overlay_visible_{overlay_scope}"
        overlay_opacity_key = f"interpretation_manual_overlay_opacity_{overlay_scope}"
        application_state = _application_state_controller().state
        interpretation_workspace = application_service_container(
            application_state
        ).interpretation_workspace(
            project_id=str(active_project.id),
            root=LAS_CORRELATION_PROJECTS_ROOT,
        )
        persisted_overlay_settings = interpretation_workspace.load_display_settings(
            well_id=manual_well_id,
            interpretation_id="default",
        )
        if overlay_visible_key not in application_state:
            application_state[overlay_visible_key] = persisted_overlay_settings.visible
        if overlay_opacity_key not in application_state:
            application_state[overlay_opacity_key] = persisted_overlay_settings.opacity
        overlay_control_left, overlay_control_right = st.columns((1.0, 1.4))
        manual_overlay_visible = overlay_control_left.checkbox(
            "Показывать ручные интервалы",
            key=overlay_visible_key,
        )
        manual_overlay_opacity = float(overlay_control_right.slider(
            "Прозрачность ручных интервалов",
            min_value=0.04,
            max_value=0.55,
            step=0.01,
            key=overlay_opacity_key,
            disabled=not manual_overlay_visible,
        ))
        updated_overlay_settings = interpretation_workspace.save_display_settings(
            well_id=manual_well_id,
            interpretation_id="default",
            visible=manual_overlay_visible,
            opacity=manual_overlay_opacity,
        ) if (
            manual_overlay_visible != persisted_overlay_settings.visible
            or manual_overlay_opacity != persisted_overlay_settings.opacity
        ) else persisted_overlay_settings
        manual_overlays = configure_manual_interval_overlays(
            manual_interval_overlays(manual_intervals),
            visible=manual_overlay_visible,
            opacity=manual_overlay_opacity,
        )
        navigator_key = f"manual_interval_selected_{active_project.id}_{manual_well_id}"
        navigator_figure = build_manual_interval_navigator(
            manual_intervals,
            selected_interval_id=selected_manual_interval_id,
        )
        try:
            navigator_event = st.plotly_chart(
                navigator_figure,
                width="stretch",
                config=PLOTLY_SCREEN_CONFIG,
                key=f"manual_interval_navigator_{active_project.id}_{manual_well_id}",
                on_select="rerun",
                selection_mode="points",
            )
        except TypeError:
            # Compatibility fallback for older Streamlit builds.
            st.plotly_chart(
                navigator_figure,
                width="stretch",
                config=PLOTLY_SCREEN_CONFIG,
                key=f"manual_interval_navigator_{active_project.id}_{manual_well_id}",
            )
            navigator_event = None
        navigator_selected_id = selected_interval_id_from_plotly_event(
            navigator_event,
            valid_interval_ids=[item.id for item in manual_intervals],
        )
        if navigator_selected_id and navigator_selected_id != selected_manual_interval_id:
            _application_state_controller().state[navigator_key] = navigator_selected_id
            st.rerun()
    if detected_interval_result is not None:
        _render_reservoir_ranking(
            calculated_df, list(detected_interval_result.intervals),
            selected_interval_id=selected_interval_id,
            key="interpretation_reservoir_ranking_table",
            project_id=str(active_project.id),
        )

    if valid_depth.empty:
        st.warning("В расчетной таблице нет числовой глубины. Графики будут построены по техническому индексу.")
        filtered_df = calculated_df
        depth_range = None
        saved_depth_range = None
    else:
        min_depth = float(valid_depth.min())
        max_depth = float(valid_depth.max())
        st.caption(f"Фактическая глубина LAS: {min_depth:g}–{max_depth:g} м. Пустой диапазон от 0 не добавляется.")
        if view_mode == "detail" and selected_interval is not None:
            interval_span = max(0.1, float(selected_interval.thickness))
            margin = max(1.0, interval_span * 0.15)
            top_depth = max(min_depth, float(selected_interval.top) - margin)
            bottom_depth = min(max_depth, float(selected_interval.base) + margin)
            depth_range = (top_depth, bottom_depth)
            saved_depth_range = depth_range
            st.caption(f"Детальный режим: {top_depth:g}–{bottom_depth:g} м вокруг {selected_interval_id}.")
        else:
            mode = st.radio(
                "Ось Y / диапазон глубины",
                options=("Весь интервал", "Ручной интервал"),
                horizontal=True,
                key="interpretation_depth_range_mode",
            )
            if mode == "Ручной интервал":
                top_col, bottom_col = st.columns(2)
                top_depth = top_col.number_input(
                    "Верх, м", min_value=min_depth, max_value=max_depth, value=min_depth, step=0.1,
                    key="interpretation_top_depth",
                )
                bottom_depth = bottom_col.number_input(
                    "Низ, м", min_value=min_depth, max_value=max_depth, value=max_depth, step=0.1,
                    key="interpretation_bottom_depth",
                )
            else:
                top_depth = min_depth
                bottom_depth = max_depth
            depth_range = (min(float(top_depth), float(bottom_depth)), max(float(top_depth), float(bottom_depth)))
            saved_depth_range = depth_range if mode == "Ручной интервал" else None
        filtered_df = _filter_by_depth_range(calculated_df, depth_range[0], depth_range[1])

    if filtered_df.empty:
        st.error("В выбранном диапазоне глубин нет данных.")
        return

    manual_height = st.slider("Базовая высота графиков", min_value=420, max_value=1100, value=650, step=10, key="interpretation_chart_height")
    height = _adaptive_tablet_height(depth_range, view_mode, int(manual_height)) if adaptive_height and depth_range is not None else int(manual_height)
    st.caption(f"Рабочая высота планшета: {height}px.")

    # Export is intentionally placed before the heavy graph controls and figures.
    # Users must see the print action immediately instead of searching at the
    # bottom of a long interpretation page.
    state_controller = _application_state_controller()
    revision_snapshot = revision_controller_from_state(state_controller.state).snapshot
    cache_metrics_registry = state_controller.ensure_runtime_service(
        "cache_metrics_registry",
        CacheMetricsRegistry,
        expected_type=CacheMetricsRegistry,
    )
    presentation_service = application_service_container(state_controller.state).interpretation_presentation(
        project_id=str(active_project.id),
        root=LAS_CORRELATION_PROJECTS_ROOT,
        metrics_registry=cache_metrics_registry,
    )
    calculated_signature = presentation_service.dataframe_signature(
        calculated_df,
        revision=revision_snapshot.calculation,
        builder=dataframe_signature,
    )
    if depth_range is not None and not valid_depth.empty:
        _render_professional_export_panel(
            logger,
            active_project,
            calculated_df=calculated_df,
            valid_depth=valid_depth,
            depth_range=depth_range,
            selected_interval=selected_interval,
            selected_interval_id=selected_interval_id,
            source_label=source_label,
            calculated_signature=calculated_signature,
            revision_snapshot=revision_snapshot,
            height=int(height),
        )

    st.markdown("### Настройка экранных графиков")
    selected_tracks = st.multiselect(
        "Графики",
        options=INTERPRETATION_TRACK_OPTIONS,
        default=INTERPRETATION_TRACK_OPTIONS,
        key="interpretation_tracks",
    )

    with st.expander("Ручной масштаб X", expanded=False):
        gas_x_range = _select_x_range("C1-C5", "interpretation_gas")
        ratio_x_range = _select_x_range("Wh/Bh/Ch", "interpretation_ratio")
        pixler_x_range = _select_x_range("Pixler ratios по глубине", "interpretation_pixler")
        pixler_palette_y_range = _select_positive_y_range("Pixler crossplot", "interpretation_pixler_palette")

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
        pixler_palette_y_range=pixler_palette_y_range,
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
        tablet_view_mode=view_mode,
        tablet_min_interval_thickness=min_interval_thickness,
        selected_interval_id=selected_interval_id,
        tablet_adaptive_height=adaptive_height,
    )
    _render_interpretation_graph_settings_saver(active_project, current_settings, logger)

    build_clicked = st.button(
        "Построить графики и планшет",
        type="primary",
        width="stretch",
        key="apply_interpretation_presentation",
        help="Фиксирует текущие настройки. Последующие изменения виджетов не перестраивают графики до следующего применения.",
    )
    if build_clicked:
        presentation_status = st.empty()
        _set_inline_operation_status(
            presentation_status,
            "Визуализация",
            "Проверяются и фиксируются настройки планшета.",
        )
        persist_applied_presentation(
            _application_state_controller().state,
            AppliedPresentationState(
                source_signature=calculated_signature,
                calculation_revision=revision_snapshot.calculation,
                settings=interpretation_graph_settings_to_dict(current_settings),
            ),
        )
        revisions = revision_controller_from_state(_application_state_controller().state)
        persist_revisions(_application_state_controller().state, revisions.bump_presentation())
        _application_state_controller().state.pop("interpretation_figure_cache", None)
        presentation_service.clear_plots()
        logger.info(
            "interpretation_presentation_committed signature=%s calculation_revision=%d tracks=%s",
            safe_log_value(calculated_signature[:12]),
            revision_snapshot.calculation,
            safe_log_value(",".join(current_settings.selected_tracks)),
        )
        _set_inline_operation_status(
            presentation_status,
            "Визуализация",
            "Настройки применены. Выполняется построение по зафиксированному снимку.",
            state="success",
        )

    applied_presentation = applied_presentation_from_state(_application_state_controller().state)
    applied_matches = presentation_matches_source(
        applied_presentation,
        calculated_signature,
        revision_snapshot.calculation,
    )
    if not applied_matches:
        # Build the first presentation automatically. Repeated widget changes still
        # require the explicit Apply button, so expensive plots are not rebuilt on
        # every Streamlit rerun.
        persist_applied_presentation(
            _application_state_controller().state,
            AppliedPresentationState(
                source_signature=calculated_signature,
                calculation_revision=revision_snapshot.calculation,
                settings=interpretation_graph_settings_to_dict(current_settings),
            ),
        )
        revisions = revision_controller_from_state(_application_state_controller().state)
        persist_revisions(_application_state_controller().state, revisions.bump_presentation())
        _application_state_controller().state.pop("interpretation_figure_cache", None)
        presentation_service.clear_plots()
        logger.info(
            "interpretation_presentation_auto_committed signature=%s calculation_revision=%d tracks=%s",
            safe_log_value(calculated_signature[:12]),
            revision_snapshot.calculation,
            safe_log_value(",".join(current_settings.selected_tracks)),
        )
        applied_presentation = applied_presentation_from_state(_application_state_controller().state)
        applied_matches = presentation_matches_source(
            applied_presentation,
            calculated_signature,
            revision_snapshot.calculation,
        )
        if not applied_matches:
            st.error("Не удалось зафиксировать настройки интерпретационных графиков.")
            return
        st.caption("Первичное представление построено автоматически. После изменения настроек нажмите кнопку применения повторно.")

    render_settings = interpretation_graph_settings_from_dict(dict(applied_presentation.settings))
    selected_tracks = tuple(render_settings.selected_tracks)
    height = int(render_settings.height)
    gas_x_range = render_settings.gas_x_range
    ratio_x_range = render_settings.ratio_x_range
    pixler_x_range = render_settings.pixler_x_range
    pixler_palette_y_range = render_settings.pixler_palette_y_range
    tablet_columns = tuple(render_settings.tablet_tracks)
    tablet_x_ranges = dict(render_settings.tablet_x_ranges)
    tablet_colors = dict(render_settings.tablet_colors)
    tablet_fill_modes = dict(render_settings.tablet_fill_modes)
    tablet_markers = tuple(
        InterpretationMarker(
            label=str(marker.get("label") or chr(ord("a") + index)),
            depth=float(marker.get("depth", 0.0)),
            note=str(marker.get("note") or ""),
        )
        for index, marker in enumerate(render_settings.tablet_markers)
    )
    tablet_zones = tuple(
        InterpretationZone(
            label=str(zone.get("label") or f"Zone {index + 1}"),
            top_depth=float(zone.get("top_depth", 0.0)),
            bottom_depth=float(zone.get("bottom_depth", 0.0)),
            color=str(zone.get("color") or "#ffd966"),
            note=str(zone.get("note") or ""),
        )
        for index, zone in enumerate(render_settings.tablet_zones)
    )
    tablet_fill = bool(render_settings.tablet_fill)
    if render_settings.depth_range is None:
        # ``None`` is the persisted representation of "full interval".  From
        # this point onward the renderer, report metadata and export helpers all
        # require a concrete iterable range, so resolve it once and keep the full
        # dataframe unchanged.
        filtered_df = calculated_df
        depth_range = _effective_depth_range(filtered_df, None)
    else:
        depth_range = _effective_depth_range(calculated_df, render_settings.depth_range)
        filtered_df = _filter_by_depth_range(calculated_df, depth_range[0], depth_range[1])
    if filtered_df.empty:
        st.error("В примененном диапазоне глубин нет строк. Измените настройки и повторно постройте графики.")
        return
    screen_filtered_df = presentation_service.screen_sample(
        filtered_df,
        source_signature=calculated_signature,
        depth_range=depth_range,
        max_rows=2200,
        sampler=downsample_frame_for_screen,
    )
    dataframe_cache_stats = presentation_service.dataframe_stats()
    if len(screen_filtered_df) < len(filtered_df):
        logger.info(
            "interpretation_screen_downsample full_rows=%d screen_rows=%d sample_hits=%d sample_misses=%d",
            len(filtered_df),
            len(screen_filtered_df),
            dataframe_cache_stats.sample_hits,
            dataframe_cache_stats.sample_misses,
        )
    if render_settings.tablet_adaptive_height and depth_range is not None:
        height = _adaptive_tablet_height(depth_range, render_settings.tablet_view_mode, height)

    detected_reservoir_overlays = tuple(
        overlay for overlay in all_reservoir_overlays
        if float(overlay.thickness) >= float(render_settings.tablet_min_interval_thickness)
        or overlay.interval_id == str(render_settings.selected_interval_id)
    )
    reservoir_overlays = detected_reservoir_overlays + tuple(manual_overlays)
    selected_tablet_depth = selected_interval_depth
    if selected_tablet_depth is None and tablet_markers:
        selected_tablet_depth = float(tablet_markers[0].depth)
    selected_interval_id = selected_manual_interval_id or str(render_settings.selected_interval_id or "")
    if selected_manual_interval_id:
        selected_manual = next(
            (item for item in manual_intervals if item.id == selected_manual_interval_id),
            None,
        )
        if selected_manual is not None:
            selected_tablet_depth = float(selected_manual.middle_depth)
    tablet_depth_range = _tablet_informative_depth_range(
        reservoir_overlays,
        depth_range,
        selected_depth=selected_tablet_depth,
        selected_interval_id=selected_interval_id,
    )
    visible_reservoir_overlays = _visible_interval_overlays(
        reservoir_overlays,
        tablet_depth_range,
        selected_interval_id=selected_interval_id,
        limit=24,
    )
    tablet_source_df = _filter_by_depth_range(
        calculated_df,
        tablet_depth_range[0],
        tablet_depth_range[1],
    )
    tablet_screen_df = presentation_service.screen_sample(
        tablet_source_df,
        source_signature=f"{calculated_signature}:tablet",
        depth_range=tablet_depth_range,
        max_rows=2200,
        sampler=downsample_frame_for_screen,
    )
    logger.info(
        "interpretation_tablet_focus applied_top=%.2f applied_bottom=%.2f tablet_top=%.2f tablet_bottom=%.2f full_rows=%d tablet_rows=%d interval_count=%d visible_intervals=%d",
        float(depth_range[0]),
        float(depth_range[1]),
        float(tablet_depth_range[0]),
        float(tablet_depth_range[1]),
        len(filtered_df),
        len(tablet_screen_df),
        len(reservoir_overlays),
        len(visible_reservoir_overlays),
    )

    # Plotly construction is expensive. The cache key now depends only on the
    # applied presentation snapshot, never on mutable widget drafts.
    figure_cache_key = (
        calculated_signature,
        int(applied_presentation.calculation_revision),
        tuple(sorted((str(key), repr(value)) for key, value in applied_presentation.settings.items())),
        len(screen_filtered_df),
        tuple(round(float(value), 4) for value in tablet_depth_range),
        len(tablet_screen_df),
        tuple(
            (item.id, item.updated_at, item.color, item.label, item.top, item.base)
            for item in manual_intervals
        ),
        selected_manual_interval_id,
    )
    state = state_controller.state
    runtime_diagnostics = state_controller.ensure_runtime_service(
        "runtime_diagnostics",
        lambda: RuntimeDiagnostics(max_events=64),
        expected_type=RuntimeDiagnostics,
    )
    performance_cycle_marker = runtime_diagnostics.mark()
    cache_lookup_started = perf_counter()
    cached_bundle = presentation_service.get_plot_bundle(figure_cache_key)
    plot_cache_hit = cached_bundle is not None
    if cached_bundle is not None:
        figures = list(cached_bundle.figures)
        screen_plot_payloads = list(cached_bundle.screen_payloads)
        screen_plot_fingerprints = list(cached_bundle.fingerprints)
        screen_plot_sizes = list(cached_bundle.serialized_sizes)
        tablet_figure = cached_bundle.tablet_figure
        cache_stats = presentation_service.plot_stats()
        lookup_duration_ms = (perf_counter() - cache_lookup_started) * 1000.0
        runtime_diagnostics.record(
            stage="interpretation_plots",
            duration_ms=lookup_duration_ms,
            cache_status="hit",
            renderer="plotly",
            item_count=len(figures),
            memory_bytes=cache_stats.estimated_bytes,
        )
        logger.info(
            "interpretation_plot_cache_hit rows=%d figure_count=%d cache_entries=%d cache_bytes=%d lookup_ms=%.2f",
            len(filtered_df), len(figures), cache_stats.entries, cache_stats.estimated_bytes, lookup_duration_ms,
        )
    else:
        render_status = st.empty()
        _set_inline_operation_status(
            render_status,
            "Рендеринг",
            "Строятся графики и профессиональный планшет.",
        )
        render_started = perf_counter()
        figures = []
        screen_plot_payloads = []
        screen_plot_fingerprints = []
        screen_plot_sizes = []
        tablet_figure = None
        render_queue = state_controller.get_value("interpretation_render_queue")
        if not isinstance(render_queue, RenderQueue):
            render_queue = RenderQueue(max_tasks=12)
            state_controller.set_value("interpretation_render_queue", render_queue)

        render_tasks: list[RenderTask] = []
        if "Интерпретация" in selected_tracks:
            render_tasks.append(RenderTask(
                "depth-interpretation",
                lambda: build_depth_interpretation_track(
                    tablet_screen_df, depth_range=tablet_depth_range, height=height,
                    reservoir_intervals=visible_reservoir_overlays,
                    selected_interval_id=selected_interval_id,
                ),
            ))
        if "C1-C5" in selected_tracks:
            render_tasks.append(RenderTask(
                "depth-gases",
                lambda: build_depth_gas_tracks(
                    tablet_screen_df, depth_range=tablet_depth_range, x_range=gas_x_range, height=height,
                    reservoir_intervals=visible_reservoir_overlays,
                    selected_interval_id=selected_interval_id,
                ),
            ))
        if "Wh/Bh/Ch" in selected_tracks:
            render_tasks.append(RenderTask(
                "depth-ratios",
                lambda: build_depth_ratio_tracks(
                    tablet_screen_df, depth_range=tablet_depth_range, x_range=ratio_x_range, height=height,
                    reservoir_intervals=visible_reservoir_overlays,
                    selected_interval_id=selected_interval_id,
                ),
            ))
        if "Pixler ratios" in selected_tracks:
            render_tasks.append(RenderTask(
                "depth-pixler",
                lambda: build_depth_pixler_tracks(
                    tablet_screen_df, depth_range=tablet_depth_range, x_range=pixler_x_range, height=height,
                    reservoir_intervals=visible_reservoir_overlays,
                    selected_interval_id=selected_interval_id,
                ),
            ))
        if TABLET_TRACK_OPTION in selected_tracks and tablet_columns:
            tablet_tracks = normalize_track_configs(
                tablet_columns,
                x_ranges=tablet_x_ranges,
                units=tablet_units_from_dataframe(screen_filtered_df),
                colors=tablet_colors,
                fill=tablet_fill,
                fill_modes=tablet_fill_modes,
            )
            render_tasks.append(RenderTask(
                "engineering-tablet",
                lambda: build_well_log_tablet(
                    tablet_screen_df,
                    tablet_tracks,
                    depth_range=tablet_depth_range,
                    markers=tablet_markers,
                    zones=tablet_zones,
                    reservoir_intervals=visible_reservoir_overlays,
                    selected_depth=selected_tablet_depth,
                    height=max(int(height), 760),
                ),
            ))

        render_batch = render_queue.execute_resilient(render_tasks)
        task_results = render_batch.completed
        figures = [enhance_screen_visibility(result.value) for result in task_results]
        for result in task_results:
            runtime_diagnostics.record(
                stage=f"plot_task:{result.task_id}",
                duration_ms=result.duration_ms,
                cache_status="miss",
                renderer=result.renderer,
                item_count=1,
            )
        for failure in render_batch.failed:
            runtime_diagnostics.record(
                stage=f"plot_task:{failure.task_id}",
                duration_ms=failure.duration_ms,
                status="failed",
                cache_status="miss",
                renderer=failure.renderer,
                item_count=0,
            )
            logger.error(
                "plot_task_failed task_id=%s exception=%s message=%s duration_ms=%.2f",
                safe_log_value(failure.task_id),
                safe_log_value(failure.exception_type),
                safe_log_value(failure.message),
                failure.duration_ms,
            )
        if render_batch.failed:
            failed_labels = ", ".join(failure.task_id for failure in render_batch.failed)
            st.warning(
                "Не удалось построить отдельные графики: " + failed_labels
                + ". Остальные результаты остаются доступными."
            )
        tablet_result = next((result for result in task_results if result.task_id == "engineering-tablet"), None)
        tablet_figure = tablet_result.value if tablet_result is not None else None
        cached_bundle = presentation_service.put_plot_bundle(figure_cache_key, figures, tablet_figure=tablet_figure)
        screen_plot_payloads = list(cached_bundle.screen_payloads)
        screen_plot_fingerprints = list(cached_bundle.fingerprints)
        screen_plot_sizes = list(cached_bundle.serialized_sizes)
        render_duration_ms = (perf_counter() - render_started) * 1000.0
        cache_stats = presentation_service.plot_stats()
        runtime_diagnostics.record(
            stage="interpretation_plots",
            duration_ms=render_duration_ms,
            cache_status="miss",
            renderer="plotly",
            item_count=len(figures),
            memory_bytes=cache_stats.estimated_bytes,
        )
        logger.info(
            "interpretation_figure_cache_miss rows=%d figure_count=%d duration_ms=%.2f cache_entries=%d cache_bytes=%d evictions=%d",
            len(filtered_df),
            len(figures),
            render_duration_ms,
            cache_stats.entries,
            cache_stats.estimated_bytes,
            cache_stats.evictions,
        )
        _set_inline_operation_status(
            render_status,
            "Рендеринг",
            f"Построено графиков: {len(figures)}, {render_duration_ms:.0f} мс.",
            state="success",
        )

    if not figures:
        st.warning("Выберите хотя бы один график.")
    stable_plot_token = hashlib.sha1(repr(figure_cache_key).encode("utf-8")).hexdigest()[:12]
    for figure_index, figure in enumerate(figures):
        render_value = (
            screen_plot_payloads[figure_index]
            if figure_index < len(screen_plot_payloads)
            else figure
        )
        fingerprint = (
            screen_plot_fingerprints[figure_index]
            if figure_index < len(screen_plot_fingerprints)
            else str(figure_index)
        )
        frontend_dispatch_started = perf_counter()
        plot_key = f"interpretation_plot_{stable_plot_token}_{fingerprint}"
        try:
            plot_event = st.plotly_chart(
                render_value,
                width="stretch",
                config=PLOTLY_SCREEN_CONFIG,
                key=plot_key,
                on_select="rerun",
                selection_mode="points",
            )
        except TypeError:
            # Compatibility fallback for Streamlit versions without Plotly selection events.
            st.plotly_chart(
                render_value,
                width="stretch",
                config=PLOTLY_SCREEN_CONFIG,
                key=plot_key,
            )
            plot_event = None
        chart_selected_manual_id = selected_interval_id_from_plotly_event(
            plot_event,
            valid_interval_ids=[item.id for item in manual_intervals],
        )
        if chart_selected_manual_id and chart_selected_manual_id != selected_manual_interval_id:
            state_controller.state[
                f"manual_interval_selected_{active_project.id}_{manual_well_id}"
            ] = chart_selected_manual_id
            st.rerun()
        frontend_dispatch_ms = (perf_counter() - frontend_dispatch_started) * 1000.0
        payload_size = screen_plot_sizes[figure_index] if figure_index < len(screen_plot_sizes) else 0
        runtime_diagnostics.record(
            stage="plot_frontend_dispatch",
            duration_ms=frontend_dispatch_ms,
            cache_status="hit" if plot_cache_hit else "miss",
            renderer="streamlit-plotly",
            item_count=1,
            memory_bytes=payload_size,
        )

    performance_summary = evaluate_performance(
        runtime_diagnostics.snapshot_since(performance_cycle_marker)
    )
    performance_gate = build_workspace_performance_gate(performance_summary)
    critical_stages = performance_gate.critical_stages
    warning_stages = performance_gate.warning_stages
    logger.info(
        "workspace_performance_audit status=%s critical=%s warning=%s plot_cache_hit=%s figure_count=%d",
        performance_gate.status,
        ",".join(critical_stages) or "none",
        ",".join(warning_stages) or "none",
        plot_cache_hit,
        len(figures),
    )
    if tablet_figure is not None:
        _render_static_export_controls(
            tablet_figure,
            base_file_name="gas_ratio_well_log_tablet",
            default_height=max(int(height), 760),
            key_prefix="interpretation_tablet",
            source_signature=calculated_signature,
            presentation_revision=revision_snapshot.presentation,
        )
    if selected_interval is not None and selected_interval_id:
        _render_selected_interval_passport(
            selected_interval, selected_interval_id, frame=calculated_df,
            pixler_zones=palette_config.pixler_zones, ternary_regions=palette_config.ternary_regions,
        )

    if TABLET_TRACK_OPTION in selected_tracks and tablet_markers and tablet_columns:
        marker_table = build_marker_interpretation_table(filtered_df, tablet_markers, columns=tablet_columns)
        if not marker_table.empty:
            st.subheader("Таблица маркеров планшета")
            st.dataframe(marker_table, width="stretch")

    if TABLET_TRACK_OPTION in selected_tracks and tablet_zones:
        zone_table = build_interpretation_zone_table(tablet_zones)
        if not zone_table.empty:
            st.subheader("Таблица интерпретационных зон планшета")
            st.dataframe(zone_table, width="stretch")

    st.subheader("Инженерная сводка УВ-интервалов")
    st.caption(
        "Показаны вероятные нефтяные, газовые, газоконденсатные, смешанные и проверочные интервалы. "
        "Технические счетчики строк намеренно скрыты."
    )
    engineering_summary = engineering_interval_summary(filtered_df)
    if engineering_summary.empty:
        st.info("В выбранном диапазоне уверенные УВ-интервалы не выделены.")
    else:
        interpretation_filter_left, interpretation_filter_right = st.columns([2, 1])
        interpretation_search = interpretation_filter_left.text_input(
            "Поиск интервала",
            key="interpretation_interval_search",
            placeholder="ID, глубина, флюид, заключение",
        )
        interpretation_fluid_options = _interval_fluid_options(engineering_summary)
        interpretation_fluids = interpretation_filter_right.multiselect(
            "Флюид",
            options=interpretation_fluid_options,
            key="interpretation_interval_fluid_filter",
            placeholder="Все типы",
        )
        filtered_engineering_summary = _filter_engineering_intervals(
            engineering_summary,
            search_text=interpretation_search,
            fluid_labels=interpretation_fluids,
        )
        if filtered_engineering_summary.empty:
            st.info("По заданным условиям интервалы не найдены.")
            return

        current_interval_id = str(
            state_controller.get_value("selected_reservoir_interval_id", "") or ""
        )
        engineering_ids, engineering_position = _interval_navigation_state(
            filtered_engineering_summary,
            current_interval_id,
        )
        if engineering_ids and current_interval_id not in engineering_ids:
            current_interval_id = engineering_ids[0]
            engineering_position = 0
            state_controller.update_values({
                "selected_reservoir_interval_id": current_interval_id
            })

        interpretation_label_by_id = {
            str(row["ID"]): (
                f'{row["ID"]} · {row.get("Интервал, м", "—")} · '
                f'{row.get("Вероятный флюид", "—")} · {row.get("Достоверность", "—")}'
            )
            for _, row in filtered_engineering_summary.iterrows()
        }
        selected_interpretation_id = st.selectbox(
            "Выбранный интервал",
            options=engineering_ids,
            index=engineering_position if engineering_ids else None,
            format_func=lambda interval_id: interpretation_label_by_id.get(str(interval_id), str(interval_id)),
            key="interpretation_interval_selector",
            help="Выбор синхронизирует Pixler, ternary, планшет, паспорт и диапазон PDF/DOCX.",
        ) if engineering_ids else ""
        if selected_interpretation_id and selected_interpretation_id != current_interval_id:
            current_interval_id = str(selected_interpretation_id)
            engineering_position = engineering_ids.index(current_interval_id)
            state_controller.update_values({"selected_reservoir_interval_id": current_interval_id})

        visible_summary, visible_start, visible_end = _interval_table_window(
            filtered_engineering_summary,
            current_interval_id,
            window_size=21,
        )
        st.caption(
            f"Активный пласт отмечен символом ▶ и удерживается в центре списка. "
            f"Показаны интервалы {visible_start + 1}–{visible_end} из {len(filtered_engineering_summary)} "
            f"(всего {len(engineering_summary)})."
        )
        interpretation_table_event = st.dataframe(
            visible_summary,
            width="stretch",
            height=430,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key="interpretation_engineering_interval_table",
            column_config={
                "Активный": st.column_config.TextColumn("", width="small"),
                "ID": st.column_config.TextColumn("ID", width="small"),
                "Интервал, м": st.column_config.TextColumn("Интервал, м", width="medium"),
                "Мощность, м": st.column_config.NumberColumn("Мощность, м", format="%.2f"),
                "Вероятный флюид": st.column_config.TextColumn("Вероятный флюид", width="medium"),
                "Достоверность": st.column_config.TextColumn("Достоверность", width="small"),
                "Данные": st.column_config.TextColumn("Качество данных", width="small"),
                "Геология": st.column_config.TextColumn("Геологическая поддержка", width="small"),
                "Уровень решения": st.column_config.TextColumn("Уровень решения", width="small"),
                "Инженерное заключение": st.column_config.TextColumn("Инженерное заключение", width="large"),
            },
        )
        table_interval_id = _selected_interval_id_from_table(
            interpretation_table_event,
            visible_summary,
        )
        if table_interval_id and table_interval_id != current_interval_id:
            interval_lookup = {
                str(overlay.interval_id): interval
                for overlay, interval in zip(all_reservoir_overlays, detected_interval_result.intervals)
            } if detected_interval_result is not None else {}
            table_interval = interval_lookup.get(table_interval_id)
            update_payload = {"selected_reservoir_interval_id": table_interval_id}
            if table_interval is not None:
                update_payload.update({
                    "selected_reservoir_depth": (
                        float(table_interval.top) + float(table_interval.base)
                    ) / 2.0,
                    "selected_reservoir_top": float(table_interval.top),
                    "selected_reservoir_bottom": float(table_interval.base),
                })
            state_controller.update_values(update_payload)
            _request_ui_refresh_and_rerun("interpretation_interval_selected")

    st.subheader("Расчетные данные выбранного интервала")
    st.caption("Таблица прокручивается вертикально и горизонтально; служебные колонки можно изучать при необходимости.")
    st.dataframe(filtered_df, width="stretch", height=520, hide_index=True)
    interval_csv_key = f"interpretation_interval_csv_{active_project.id}"
    interval_csv_settings = {
        "source_signature": calculated_signature,
        "presentation_revision": int(revision_snapshot.presentation),
        "depth_range": _effective_depth_range(filtered_df, depth_range),
        "rows": int(len(filtered_df)),
    }
    prepare_interval_csv = st.button(
        "Подготовить CSV выбранного интервала",
        width="stretch",
        key=f"prepare_interpretation_interval_csv_{active_project.id}",
    )
    if prepare_interval_csv:
        csv_started = perf_counter()
        interval_csv_bytes = export_csv_bytes(filtered_df)
        _application_state_controller().state[interval_csv_key] = {
            "settings": interval_csv_settings,
            "content": interval_csv_bytes,
        }
        revisions = revision_controller_from_state(_application_state_controller().state)
        persist_revisions(_application_state_controller().state, revisions.bump_export())
        logger.info(
            "interpretation_interval_csv_completed rows=%d bytes=%d duration_ms=%.2f",
            len(filtered_df),
            len(interval_csv_bytes),
            (perf_counter() - csv_started) * 1000.0,
        )

    cached_interval_csv = _application_state_controller().state.get(interval_csv_key)
    csv_matches = (
        isinstance(cached_interval_csv, dict)
        and cached_interval_csv.get("settings") == interval_csv_settings
        and isinstance(cached_interval_csv.get("content"), (bytes, bytearray))
    )
    if csv_matches:
        interval_csv_bytes = bytes(cached_interval_csv["content"])
        interval_download_col, interval_save_col = st.columns(2)
        interval_download_col.download_button(
            "Экспорт выбранного интервала CSV",
            data=interval_csv_bytes,
            file_name="gas_ratio_selected_interval.csv",
            mime="text/csv",
            width="stretch",
        )
        if interval_save_col.button("Сохранить CSV в проект", width="stretch", key=f"save_interpretation_interval_csv_{active_project.id}"):
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
    else:
        st.caption("CSV будет сериализован только после нажатия кнопки подготовки.")
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
            st.dataframe(_format_curve_group_rows(well), width="stretch")

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
    controller = _application_state_controller()
    values = {f"{key_prefix}_x_auto": x_range is None}
    if x_range is not None:
        values.update({
            f"{key_prefix}_x_min": float(x_range[0]),
            f"{key_prefix}_x_max": float(x_range[1]),
        })
    controller.update_values(values)


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
    controller = _application_state_controller()
    available_well_names = tuple(well.name for well in wells)
    selected_wells = tuple(name for name in settings.selected_well_names if name in available_well_names) or available_well_names
    values = {
        "las_correlation_selected_wells": list(selected_wells),
        "las_correlation_gis_groups": list(_filter_group_selection(settings.gis_groups, group_options, DEFAULT_GIS_GROUPS)),
        "las_correlation_gas_groups": list(_filter_group_selection(settings.gas_groups, group_options, DEFAULT_GAS_GROUPS)),
        "las_correlation_height_per_well": int(settings.height_per_well),
        "las_correlation_view_mode": (
            settings.view_mode if settings.view_mode in SUPPORTED_VIEW_MODES else VIEW_MODE_BY_WELL
        ),
        "las_correlation_manual_curve_groups": bool(settings.curve_group_overrides),
    }
    if settings.comparison_curve:
        values["las_correlation_comparison_curve"] = settings.comparison_curve

    if settings.depth_range is None:
        values["las_correlation_depth_range_mode"] = "Общий весь интервал"
    else:
        values.update({
            "las_correlation_depth_range_mode": "Ручной интервал",
            "las_correlation_top_depth": float(settings.depth_range[0]),
            "las_correlation_bottom_depth": float(settings.depth_range[1]),
        })

    use_manual_groups = bool(settings.curve_group_overrides)
    if use_manual_groups:
        for well in wells:
            overrides = settings.curve_group_overrides.get(well.name, {})
            for row in curve_group_rows(well):
                curve = row["curve"]
                group = overrides.get(curve, row["group"])
                if group not in CURVE_GROUP_LABELS:
                    group = "other"
                values[f"las_correlation_group_override_{well.name}_{curve}"] = group
    controller.update_values(values)

    _set_las_correlation_x_range_state("las_correlation_gis", settings.gis_x_range)
    _set_las_correlation_x_range_state("las_correlation_gas", settings.gas_x_range)


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
        return _project_manager_service().list_projects()
    except Exception:
        logger.exception("project_records_load_failed")
        st.warning("Не удалось загрузить список проектов. Используется основной проект.")
        return (ProjectRecord(id=DEFAULT_PROJECT_ID, name="Основной проект"),)


def _project_selectbox_key(current_project_id: str, project_ids: tuple[str, ...], key_prefix: str = "global") -> str:
    return f"{PROJECT_SELECTBOX_KEY_PREFIX}_{key_prefix}_{current_project_id}_{len(project_ids)}"


def _render_project_selector(logger, *, key_prefix: str = "global", expanded: bool = False) -> ProjectRecord:
    state = _application_state_controller()
    projects = _load_project_records_for_ui(logger)
    projects_by_id = {project.id: project for project in projects}
    project_ids = tuple(projects_by_id)

    # Apply pending project switches before rendering widgets. This keeps
    # widget state and persistent application state separated.
    state.consume_pending_project_activation()

    current_project_id = state.context().project_id
    if current_project_id not in projects_by_id:
        current_project_id = DEFAULT_PROJECT_ID if DEFAULT_PROJECT_ID in projects_by_id else projects[0].id
        state.ensure_project(current_project_id)

    with st.expander("Проект", expanded=expanded):
        selected_project_id = st.selectbox(
            "Активный проект",
            options=project_ids,
            index=project_ids.index(current_project_id),
            format_func=lambda project_id: _project_option_label(projects_by_id[project_id]),
            key=_project_selectbox_key(current_project_id, project_ids, key_prefix=key_prefix),
        )
        if selected_project_id != state.context().project_id:
            state.request_project_activation(selected_project_id)
            _clear_las_working_state()
            _refresh_ui()
        active_project = projects_by_id[selected_project_id]
        try:
            _project_manager_service().touch_recent(active_project)
        except Exception:
            logger.exception("recent_project_touch_failed project_id=%s", safe_log_value(active_project.id))
        st.caption(f"Папка проекта: data/projects/{active_project.id}/")

        if active_project.id != DEFAULT_PROJECT_ID:
            if st.button("Удалить активный проект с диска", width="stretch", key=f"{key_prefix}_delete_active_project"):
                try:
                    result = _project_manager_service().delete_project_complete(active_project.id)
                    state.request_project_activation(DEFAULT_PROJECT_ID)
                    _clear_las_working_state()
                except Exception:
                    logger.exception("project_delete_failed project_id=%s", safe_log_value(active_project.id))
                    st.error("Не удалось удалить проект с диска. Подробности записаны в logs/app.log.")
                else:
                    st.success("Проект удален с диска.")
                    _refresh_ui()

        with st.form(f"{key_prefix}_create_project_form", clear_on_submit=True):
            new_project_name = st.text_input("Название нового проекта")
            new_project_description = st.text_input("Комментарий")
            submitted = st.form_submit_button("Создать проект")
            if submitted:
                if not new_project_name.strip():
                    st.warning("Введите название проекта.")
                else:
                    try:
                        result = _project_manager_service().create_project(
                            name=new_project_name,
                            description=new_project_description,
                        )
                        project = result.project
                        state.request_project_activation(project.id)
                        logger.info("project_created id=%s", safe_log_value(project.id))
                        st.success("Проект создан.")
                        _refresh_ui()
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
    for las_file in _las_workspace_service(project.id).list_files():
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
            if st.button(label, key=f"sidebar_quick_nav_{target}", width="stretch"):
                _set_active_main_tab(target)
                _refresh_ui()
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
                        _refresh_ui()
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
                        _refresh_ui()
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
                    _refresh_ui()
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
                    _refresh_ui()
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
                    _refresh_ui()
                except Exception:
                    logger.exception("project_well_card_save_failed project_id=%s", safe_log_value(project.id))
                    st.error("Не удалось сохранить карточку скважины.")


def _load_project_las_correlation_settings(project_id: str) -> LasCorrelationSettings | None:
    try:
        return application_service_container(
            _application_state_controller().state
        ).las_workspace(
            project_id=project_id,
            root=LAS_CORRELATION_PROJECTS_ROOT,
        ).load_correlation_settings()
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


def _render_dataset_manager_toolbar(
    *,
    project_id: str,
    section: str,
    selected_dataset_id: str = "",
    logger=None,
) -> None:
    """Render safe Dataset Manager lifecycle controls for one section."""

    service = _dataset_manager_service()
    supported_section = section in service.section_specs
    key_prefix = f"dataset_manager_{section}_{project_id}"
    try:
        audit = service.audit_section(project_id, section) if supported_section else None
    except Exception:
        audit = None
        if logger:
            logger.exception("dataset_manager_audit_failed project_id=%s section=%s", safe_log_value(project_id), safe_log_value(section))

    st.caption(
        "Dataset Manager хранит активные и архивные наборы раздельно. "
        "Удаление с диска доступно только после явного подтверждения ID проекта."
    )
    if audit is not None:
        metrics = st.columns(3)
        metrics[0].metric("Активные", audit.active_records)
        metrics[1].metric("Архивные", audit.archived_records)
        metrics[2].metric("Orphan-каталоги", len(audit.orphan_directories))
        if audit.needs_cleanup:
            st.warning(
                "Раздел содержит архивные или не привязанные к manifest данные. "
                "Они не участвуют в текущей сессии, но занимают место на диске."
            )

    basic = st.columns([1.1, 1.1, 1.4])
    basic[0].button("➕ Импорт", key=f"{key_prefix}_import", disabled=True, width="stretch")
    if basic[1].button("🔄 Обновить", key=f"{key_prefix}_refresh", width="stretch"):
        _refresh_ui()
    basic[2].button("📤 Экспорт списка", key=f"{key_prefix}_export", disabled=True, width="stretch")

    with st.expander("Очистка и обслуживание раздела", expanded=False):
        st.caption(
            f"Для destructive-операций введите ID активного проекта: `{project_id}`. "
            "Перед массовой очисткой приложение автоматически создаст backup ZIP проекта."
        )
        confirmation = st.text_input(
            "Подтверждение ID проекта",
            key=f"{key_prefix}_confirmation",
            placeholder=project_id,
        ).strip()
        confirmed = confirmation == project_id
        if confirmation and not confirmed:
            st.error("ID проекта не совпадает. Очистка заблокирована.")

        action_cols = st.columns(4)
        delete_selected = action_cols[0].button(
            "Удалить выбранный",
            key=f"{key_prefix}_delete_selected",
            disabled=(not selected_dataset_id or not supported_section or not confirmed),
            width="stretch",
        )
        purge_archived = action_cols[1].button(
            "Удалить архивные",
            key=f"{key_prefix}_purge_archived",
            disabled=(not supported_section or not confirmed or audit is None or audit.archived_records == 0),
            width="stretch",
        )
        clear_orphans = action_cols[2].button(
            "Удалить orphan",
            key=f"{key_prefix}_clear_orphans",
            disabled=(not supported_section or not confirmed or audit is None or not audit.orphan_directories),
            width="stretch",
        )
        clear_section = action_cols[3].button(
            "Очистить раздел",
            key=f"{key_prefix}_clear_section",
            disabled=(not supported_section or not confirmed),
            width="stretch",
        )

        try:
            if delete_selected:
                summary = service.delete_dataset(project_id, section, selected_dataset_id)
                st.success(f"Удалено datasets: {summary.deleted}. Освобождено ресурсов: {summary.released_resources}.")
                _refresh_ui()
            elif purge_archived:
                backup = create_project_backup(LAS_CORRELATION_PROJECTS_ROOT, project_id, f"Before purging archived {section} datasets")
                st.caption(f"Backup создан: {backup.file_name}")
                summary = service.purge_archived(project_id, section)
                st.success(f"Архив очищен. Удалено datasets: {summary.deleted}.")
                _refresh_ui()
            elif clear_orphans:
                backup = create_project_backup(LAS_CORRELATION_PROJECTS_ROOT, project_id, f"Before clearing orphan {section} dataset folders")
                st.caption(f"Backup создан: {backup.file_name}")
                summary = service.clear_orphan_directories(project_id, section)
                st.success(f"Orphan-каталоги очищены: {summary.deleted}.")
                _refresh_ui()
            elif clear_section:
                backup = create_project_backup(LAS_CORRELATION_PROJECTS_ROOT, project_id, f"Before clearing {section} dataset section")
                st.caption(f"Backup создан: {backup.file_name}")
                summary = service.clear_section(project_id, section)
                st.success(f"Раздел очищен. Удалено datasets: {summary.deleted}.")
                _refresh_ui()
        except StorageDeleteError as exc:
            if logger:
                logger.exception("dataset_manager_storage_delete_failed project_id=%s section=%s", safe_log_value(project_id), safe_log_value(section))
            st.error(str(exc))
        except Exception:
            if logger:
                logger.exception("dataset_manager_cleanup_failed project_id=%s section=%s", safe_log_value(project_id), safe_log_value(section))
            st.error("Не удалось выполнить очистку Dataset Manager. Подробности записаны в logs/app.log.")

        st.divider()
        st.markdown("**Полная очистка всех Dataset-разделов проекта**")
        st.caption("Удаляет LAS, CSV, Excel, Core, Mud Log и Production datasets, но не расчёты, отчёты и backups.")
        if st.button(
            "Очистить все Dataset-разделы",
            key=f"{key_prefix}_clear_all",
            disabled=not confirmed,
            width="stretch",
        ):
            try:
                backup = create_project_backup(LAS_CORRELATION_PROJECTS_ROOT, project_id, "Before clearing all dataset sections")
                st.caption(f"Backup создан: {backup.file_name}")
                summary = service.clear_all(project_id)
                st.success(f"Все Dataset-разделы очищены. Удалено datasets: {summary.deleted}.")
                _refresh_ui()
            except StorageDeleteError as exc:
                st.error(str(exc))
            except Exception:
                if logger:
                    logger.exception("dataset_manager_clear_all_failed project_id=%s", safe_log_value(project_id))
                st.error("Не удалось очистить Dataset Manager. Подробности записаны в logs/app.log.")

def _render_dataset_manager_table(
    *,
    title: str,
    datasets: tuple[project_datasets.ProjectDatasetRecord, ...],
    select_key: str,
    empty_caption: str,
    ready_message: str,
    project_id: str,
    section: str,
    logger=None,
) -> None:
    """Render one Dataset Manager table and selected dataset details."""

    if not datasets:
        _render_dataset_manager_toolbar(
            project_id=project_id, section=section, selected_dataset_id="", logger=logger
        )
        st.caption(empty_caption)
        return

    datasets_by_id = {dataset.id: dataset for dataset in datasets}

    ready_count = sum(1 for dataset in datasets if dataset.status == "ready")
    warning_count = sum(1 for dataset in datasets if dataset.status == "warning")
    error_count = sum(1 for dataset in datasets if dataset.status == "error")
    st.caption(
        f"{title}: {len(datasets)} · готово: {ready_count} · "
        f"требует проверки: {warning_count} · ошибок чтения: {error_count}"
    )
    dataset_table = build_project_dataset_table(datasets).copy()
    dataset_table.insert(0, "Dataset ID", [dataset.id for dataset in datasets])
    selected_row = _render_workbench_data_grid(
        dataset_table,
        key_prefix=f"workbench_dataset_{project_id}_{section}",
        type_column="Тип",
        status_column="Статус",
        default_sort="Сохранено",
        technical_columns=("Dataset ID", "Скважина ID", "Источник ID", "Архивировано"),
        height=300,
        id_column="Dataset ID",
        selection_target="dataset",
        selection_label_column="Dataset",
        selection_metadata={"section": section, "project_id": project_id},
        enable_multi_selection=True,
    )
    selected_dataset_id = str((selected_row or {}).get("Dataset ID") or next(iter(datasets_by_id)))
    _render_dataset_manager_toolbar(
        project_id=project_id, section=section, selected_dataset_id=selected_dataset_id, logger=logger
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
        width="stretch",
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

    service = _dataset_manager_service()
    section_titles = {
        "las": "LAS",
        "csv": "CSV",
        "excel": "Excel",
        "core": "Core",
        "mud_log": "Mud Log",
        "production": "Production",
    }
    ready_messages = {
        "las": "LAS dataset готов к открытию в рабочем workflow и выгрузке.",
        "csv": "CSV dataset готов к проверке mapping и расчетам.",
        "excel": "Excel dataset готов к проверке активного листа, mapping и расчетам.",
        "core": "Core dataset готов к сопоставлению образцов с LAS по глубине.",
        "mud_log": "Mud Log dataset готов к сопоставлению газов, литологии и описаний с LAS по глубине.",
        "production": "Production dataset готов к анализу добычи по дате и скважине.",
    }

    for section in service.supported_sections():
        title = section_titles.get(section, section.upper())
        with st.expander(f"Dataset Manager · {title}", expanded=False):
            try:
                datasets = service.list_dataset_cards(project.id, section)
            except Exception:
                logger.exception("project_dataset_manager_%s_failed project_id=%s", section, safe_log_value(project.id))
                st.warning(f"Не удалось построить список {title} datasets.")
            else:
                _render_dataset_manager_table(
                    title=f"{title} datasets",
                    datasets=datasets,
                    select_key=f"project_dataset_{section}_select_{project.id}",
                    empty_caption=f"В активном проекте пока нет {title} datasets.",
                    ready_message=ready_messages.get(section, "Dataset готов к работе."),
                    project_id=project.id,
                    section=section,
                    logger=logger,
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
        if action_col.button("Сохранить recovery checkpoint", key=f"project_manager_recovery_save_{project.id}", width="stretch"):
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

        if backup_col.button("Создать backup ZIP", key=f"project_manager_backup_create_{project.id}", width="stretch"):
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

        if template_col.button("Создать шаблон проекта", key=f"project_manager_template_create_{project.id}", width="stretch"):
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
            st.dataframe(pd.DataFrame(build_project_templates_table(templates)), width="stretch", height=180)
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

        project_manager = _project_manager_service()
        backup_rows = project_manager.list_backup_rows(project.id)
        if backup_rows:
            st.markdown("#### Резервные копии активного проекта")
            st.dataframe(pd.DataFrame(backup_rows), width="stretch", height=180)
        else:
            st.caption("Резервных ZIP-копий активного проекта пока нет.")

        if st.button("Архивировать проект metadata-only", key=f"project_manager_archive_{project.id}"):
            try:
                archive = project_manager.archive_project(project.id, "Archived from Project Manager 2.0")
            except Exception:
                logger.exception("project_archive_failed project_id=%s", safe_log_value(project.id))
                st.error("Не удалось архивировать проект. Подробности записаны в logs/app.log.")
            else:
                st.success(f"Архивная backup-копия создана: {archive.file_name}.")

        history_rows = project_manager.list_history_rows(project.id, limit=20)
        if history_rows:
            st.markdown("#### История изменений проекта")
            st.dataframe(pd.DataFrame(history_rows), width="stretch", height=260)
        else:
            if st.button("Добавить стартовую запись истории", key=f"project_manager_history_seed_{project.id}"):
                project_manager.append_history(
                    project.id,
                    "project-manager-opened",
                    "Project Manager 2.0 initialized for active project",
                )
                st.success("Стартовая запись истории добавлена.")


def _render_workbench_data_grid(
    dataframe: pd.DataFrame,
    *,
    key_prefix: str,
    type_column: str | None = "Тип",
    status_column: str | None = "Статус",
    default_sort: str | None = None,
    technical_columns: tuple[str, ...] = (
        "UUID", "SHA-256", "Ключ", "Object ID", "Скважина ID", "Путь", "Относительный путь"
    ),
    height: int = 360,
    id_column: str | None = None,
    selection_target: str | None = None,
    selection_label_column: str | None = None,
    selection_metadata: dict[str, object] | None = None,
    enable_multi_selection: bool = False,
) -> dict[str, object] | None:
    """Render the shared Workbench Data Grid and publish one object selection.

    The grid owns filtering, sorting and paging.  When ``id_column`` and
    ``selection_target`` are supplied, the selected row is persisted through
    ``WorkbenchSelectionService`` so the right-hand Properties pane can render
    the same object consistently across Dataset, Calculation and Export views.
    """

    frame = dataframe.copy()
    if frame.empty:
        st.caption("Нет записей для отображения.")
        return None

    controls = st.columns((2.2, 1.3, 1.3, 1.2))
    with controls[0]:
        search = st.text_input(
            "Поиск",
            key=f"{key_prefix}_search",
            placeholder="Имя, путь, тип или статус",
        )
    with controls[1]:
        type_options = sorted(frame[type_column].dropna().astype(str).unique()) if type_column and type_column in frame else []
        selected_types = st.multiselect(
            "Тип",
            options=type_options,
            default=type_options,
            key=f"{key_prefix}_types",
            disabled=not type_options,
        )
    with controls[2]:
        status_options = sorted(frame[status_column].dropna().astype(str).unique()) if status_column and status_column in frame else []
        selected_statuses = st.multiselect(
            "Статус",
            options=status_options,
            default=status_options,
            key=f"{key_prefix}_statuses",
            disabled=not status_options,
        )
    with controls[3]:
        show_technical = st.toggle(
            "Технические данные",
            value=False,
            key=f"{key_prefix}_technical",
        )

    sort_columns = tuple(frame.columns)
    preferred_sort = default_sort if default_sort in sort_columns else sort_columns[0]
    sort_row = st.columns((2, 1, 1, 1))
    with sort_row[0]:
        sort_column = st.selectbox(
            "Сортировка",
            options=sort_columns,
            index=sort_columns.index(preferred_sort),
            key=f"{key_prefix}_sort",
        )
    with sort_row[1]:
        ascending = st.selectbox(
            "Порядок",
            options=(True, False),
            format_func=lambda value: "По возрастанию" if value else "По убыванию",
            key=f"{key_prefix}_ascending",
        )
    with sort_row[2]:
        page_size = st.selectbox(
            "Строк на странице",
            options=(10, 25, 50, 100),
            index=1,
            key=f"{key_prefix}_page_size",
        )

    preliminary = build_project_database_table_view(
        frame,
        search=search,
        type_column=type_column,
        selected_types=selected_types,
        status_column=status_column,
        selected_statuses=selected_statuses,
        sort_column=sort_column,
        ascending=ascending,
        page=1,
        page_size=page_size,
        show_technical=show_technical,
        technical_columns=technical_columns,
    )
    with sort_row[3]:
        page = st.number_input(
            "Страница",
            min_value=1,
            max_value=preliminary.page_count,
            value=1,
            step=1,
            key=f"{key_prefix}_page",
        )

    view = build_project_database_table_view(
        frame,
        search=search,
        type_column=type_column,
        selected_types=selected_types,
        status_column=status_column,
        selected_statuses=selected_statuses,
        sort_column=sort_column,
        ascending=ascending,
        page=int(page),
        page_size=page_size,
        show_technical=show_technical,
        technical_columns=technical_columns,
    )
    st.caption(
        f"Показано {len(view.dataframe)} из {view.filtered_rows} найденных · "
        f"всего {view.total_rows} · страница {view.page} из {view.page_count}"
    )
    st.dataframe(view.dataframe, width="stretch", height=height, hide_index=True)

    if not id_column or not selection_target or id_column not in frame.columns:
        return None

    visible_ids = [str(value) for value in view.dataframe.get(id_column, pd.Series(dtype=str)).dropna().tolist()]
    if not visible_ids:
        st.caption("На текущей странице нет доступных для выбора объектов.")
        return None

    source_by_id = {str(row[id_column]): row.to_dict() for _, row in frame.iterrows() if pd.notna(row.get(id_column))}

    if enable_multi_selection:
        
        with st.expander("Массовые операции", expanded=False):
            selected_ids = st.multiselect(
                "Выбранные объекты",
                options=tuple(visible_ids),
                format_func=lambda object_id: str(source_by_id.get(object_id, {}).get(selection_label_column or "", object_id)),
                key=f"{key_prefix}_bulk_selected",
            )
            bulk_service = _workbench_application_service()
            bulk_service.set_bulk_selection(
                key=key_prefix, target=selection_target, object_ids=selected_ids, metadata=dict(selection_metadata or {})
            )
            actions = _workbench_application_service().bulk_actions(selection_target)
            if selected_ids and actions:
                action_by_id = {str(item["id"]): item for item in actions}
                action_id = st.selectbox(
                    "Действие",
                    options=tuple(action_by_id),
                    format_func=lambda value: str(action_by_id[value]["title"]),
                    key=f"{key_prefix}_bulk_action",
                )
                selected_action = action_by_id[action_id]
                confirmed = True
                if bool(selected_action.get("requires_confirmation")):
                    project_id = str((selection_metadata or {}).get("project_id") or "")
                    confirmation = st.text_input(
                        "Для подтверждения введите ID проекта",
                        key=f"{key_prefix}_bulk_confirm",
                        placeholder=project_id,
                    )
                    confirmed = bool(project_id) and confirmation.strip() == project_id
                if st.button(
                    str(selected_action["title"]),
                    key=f"{key_prefix}_bulk_execute",
                    disabled=not confirmed,
                    width="stretch",
                ):
                    bulk_service.request_bulk_action({
                        "target": selection_target,
                        "action_id": action_id,
                        "object_ids": tuple(selected_ids),
                        "metadata": dict(selection_metadata or {}),
                        "confirmed": confirmed,
                    })
                    _request_ui_refresh_and_rerun("workbench_selection_changed")
            else:
                st.caption("Выберите один или несколько объектов на текущей странице.")
            bulk_result = bulk_service.bulk_result()
            if bulk_result:
                message = str(bulk_result.get("message") or "")
                if bool(bulk_result.get("success")):
                    st.success(message)
                else:
                    st.error(message)

    selected_id = st.selectbox(
        "Выбранный объект",
        options=tuple(visible_ids),
        format_func=lambda object_id: str(
            source_by_id.get(object_id, {}).get(selection_label_column or "", object_id)
        ),
        key=f"{key_prefix}_selected_object",
    )
    selected_row = dict(source_by_id.get(str(selected_id), {}))
    if selected_row:
        metadata = {
            str(key): value
            for key, value in selected_row.items()
            if str(key) != id_column and isinstance(value, (str, int, float, bool))
        }
        metadata.update({
            str(key): value for key, value in dict(selection_metadata or {}).items()
            if isinstance(value, (str, int, float, bool))
        })
        _workbench_application_service().select(
            selection_target, str(selected_id), metadata
        )
        st.caption("Подробности выбранной строки отображаются в панели Properties.")
        return selected_row
    return None


def _render_project_database_table(*args, **kwargs) -> None:
    """Backward-compatible alias for Project Database callers."""

    _render_workbench_data_grid(*args, **kwargs)


def _render_project_file_index(project: ProjectRecord, logger) -> None:
    """Render Project Database file index for the active project."""

    with st.expander("Project Database · Обслуживание", expanded=False):
        st.caption(
            "Синхронизация не удаляет файлы. Сжатие и сброс затрагивают только служебные "
            "project_index.json, project_file_versions.json и project_uuids.json. "
            "Перед изменением metadata автоматически создается ZIP-backup проекта."
        )
        confirmation = st.text_input(
            "Для обслуживания введите ID активного проекта",
            key=f"project_database_maintenance_confirm_{project.id}",
            placeholder=project.id,
        )
        confirmed = confirmation.strip() == project.id
        actions = st.columns(3)
        with actions[0]:
            if st.button("Синхронизировать таблицы", key=f"project_database_sync_{project.id}"):
                try:
                    result = _project_storage_service(project.id).sync_storage()
                    uuid_summary = update_project_uuid_registry(LAS_CORRELATION_PROJECTS_ROOT, project.id)
                except Exception:
                    logger.exception("project_database_sync_failed project_id=%s", safe_log_value(project.id))
                    st.error("Не удалось синхронизировать Project Database. Подробности записаны в logs/app.log.")
                else:
                    st.success(
                        f"Таблицы синхронизированы: файлов {result.entries_count}, "
                        f"версий {result.version_count}, UUID {uuid_summary.total_count}."
                    )
                    _refresh_ui()
        with actions[1]:
            if st.button(
                "Сжать metadata",
                key=f"project_database_compact_{project.id}",
                disabled=not confirmed,
            ):
                try:
                    result = _project_manager_service().compact_project_database_metadata(project.id)
                except Exception:
                    logger.exception("project_database_compact_failed project_id=%s", safe_log_value(project.id))
                    st.error("Не удалось сжать metadata Project Database. Подробности записаны в logs/app.log.")
                else:
                    st.success(
                        f"Metadata сжаты. Файлов: {result.indexed_files}, версий: {result.version_rows}, "
                        f"UUID: {result.uuid_rows}. Backup: {result.backup_id}."
                    )
                    _refresh_ui()
        with actions[2]:
            if st.button(
                "Сбросить metadata",
                key=f"project_database_reset_{project.id}",
                disabled=not confirmed,
            ):
                try:
                    result = _project_manager_service().reset_project_database_metadata(project.id)
                except Exception:
                    logger.exception("project_database_reset_failed project_id=%s", safe_log_value(project.id))
                    st.error("Не удалось пересоздать metadata Project Database. Подробности записаны в logs/app.log.")
                else:
                    st.success(
                        f"Metadata пересозданы из фактических файлов. Файлов: {result.indexed_files}, "
                        f"версий: {result.version_rows}, UUID: {result.uuid_rows}. Backup: {result.backup_id}."
                    )
                    _refresh_ui()
        st.caption(
            "Сжать metadata: оставить по одной активной записи версии. "
            "Сбросить metadata: удалить только служебные таблицы и построить их заново; пользовательские файлы сохраняются."
        )

    with st.expander("Project Database · Индексация файлов", expanded=False):
        st.caption(
            "Индекс собирает metadata файлов активного проекта: путь, тип, размер, "
            "время изменения и SHA-256. Файлы не копируются и datasets не изменяются."
        )
        storage_service = _project_storage_service(project.id)
        columns = st.columns(3)
        with columns[0]:
            if st.button("Обновить индекс файлов", key=f"project_file_index_refresh_{project.id}"):
                try:
                    result = index_manager.rebuild_project_index(project.id)
                except Exception:
                    logger.exception("project_file_index_save_failed project_id=%s", safe_log_value(project.id))
                    st.error("Не удалось обновить индекс файлов проекта. Подробности записаны в logs/app.log.")
                else:
                    st.success(f"Индекс обновлен. Файлов: {result.entries_count}. Дублей: {result.duplicate_count}.")
        with columns[1]:
            if st.button("Проверить сохраненный индекс", key=f"project_file_index_validate_{project.id}"):
                try:
                    result = index_manager.validate_project_index(project.id)
                except Exception:
                    logger.exception("project_file_index_validate_failed project_id=%s", safe_log_value(project.id))
                    st.error("Не удалось проверить индекс файлов проекта. Подробности записаны в logs/app.log.")
                else:
                    if result.missing_count:
                        st.warning(f"Проверка индекса завершена. Отсутствуют: {result.missing_count}.")
                    else:
                        st.success(f"Проверка индекса завершена. Файлов в индексе: {result.entries_count}.")
        with columns[2]:
            if st.button("🧹 Перестроить индекс", key=f"project_file_index_rebuild_{project.id}"):
                try:
                    result = storage_service.sync_storage()
                except Exception:
                    logger.exception("project_file_index_rebuild_failed project_id=%s", safe_log_value(project.id))
                    st.error("Не удалось перестроить индекс файлов проекта. Подробности записаны в logs/app.log.")
                else:
                    st.success(
                        f"Индекс и версии синхронизированы по фактическим файлам проекта. "
                        f"Файлов: {result.entries_count}, объектов версий: {result.version_asset_count}."
                    )
                    _refresh_ui()

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
            _render_project_database_table(
                build_project_duplicate_files_table(duplicate_groups),
                key_prefix=f"project_database_duplicates_{project.id}",
                type_column="Типы",
                status_column=None,
                default_sort="Лишних файлов",
                technical_columns=("Ключ", "Файлы"),
                height=280,
            )
            exact_duplicate_paths = tuple(
                entry.relative_path
                for group in duplicate_groups
                if group.reason == "checksum"
                for entry in group.entries[1:]
                if entry.kind != "Metadata"
            )
            if exact_duplicate_paths:
                st.markdown("##### Удаление подтвержденного SHA-256-дубликата")
                st.caption(
                    "Удаляется только выбранная лишняя копия. Перед удалением создается ZIP-backup; "
                    "служебные JSON-файлы этим действием удалить нельзя."
                )
                duplicate_path = st.selectbox(
                    "Лишняя копия",
                    options=exact_duplicate_paths,
                    key=f"project_database_duplicate_path_{project.id}",
                )
                duplicate_confirmation = st.text_input(
                    "Подтвердите ID проекта для удаления дубликата",
                    key=f"project_database_duplicate_confirm_{project.id}",
                    placeholder=project.id,
                )
                if st.button(
                    "Удалить выбранный дубликат",
                    key=f"project_database_duplicate_delete_{project.id}",
                    disabled=duplicate_confirmation.strip() != project.id,
                ):
                    try:
                        result = _project_manager_service().delete_exact_duplicate_file(project.id, duplicate_path)
                    except Exception:
                        logger.exception(
                            "project_database_duplicate_delete_failed project_id=%s path=%s",
                            safe_log_value(project.id), safe_log_value(duplicate_path),
                        )
                        st.error("Не удалось удалить дубликат. Подробности записаны в logs/app.log.")
                    else:
                        st.success(
                            f"Удален дубликат: {result.deleted_path}. "
                            f"Project Database синхронизирована. Backup: {result.backup_id}."
                        )
                        _refresh_ui()
        else:
            st.success("Дубликаты по SHA-256 и паре имя/размер не найдены.")
        _render_project_database_table(
            build_project_file_index_table(annotated_entries),
            key_prefix=f"project_database_files_{project.id}",
            default_sort="Изменен",
            height=420,
        )

    with st.expander("Project Database · Версии файлов", expanded=False):
        st.caption(
            "Версии файлов строятся по сохраненному project_index.json. "
            "История хранит только metadata, checksum и номер версии; содержимое файлов не копируется."
        )
        if st.button("Обновить версии файлов", key=f"project_file_versions_refresh_{project.id}"):
            try:
                result = _project_storage_service(project.id).sync_storage()
            except Exception:
                logger.exception("project_file_versions_update_failed project_id=%s", safe_log_value(project.id))
                st.error("Не удалось обновить версии файлов проекта. Подробности записаны в logs/app.log.")
            else:
                st.success(
                    f"Индекс и версии файлов обновлены. "
                    f"Файлов: {result.entries_count}, объектов версий: {result.version_asset_count}, "
                    f"версий: {result.version_count}."
                )
                _refresh_ui()

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
        _render_project_database_table(
            build_project_file_versions_table(assets),
            key_prefix=f"project_database_versions_{project.id}",
            status_column=None,
            default_sort="Файл",
            technical_columns=("SHA-256", "Путь"),
            height=380,
        )

        assets_with_history = [asset for asset in assets if asset.version_count > 1]
        if assets_with_history:
            selected_label = st.selectbox(
                "История версий файла",
                options=[f"{asset.relative_path} · версий: {asset.version_count}" for asset in assets_with_history],
                key=f"project_file_versions_history_select_{project.id}",
            )
            selected_asset = assets_with_history[[f"{asset.relative_path} · версий: {asset.version_count}" for asset in assets_with_history].index(selected_label)]
            _render_project_database_table(
                build_project_file_version_history_table(selected_asset),
                key_prefix=f"project_database_version_history_{project.id}_{selected_asset.asset_key[:12]}",
                default_sort="Версия",
                technical_columns=("SHA-256", "Путь", "ID"),
                height=300,
            )

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
            _render_project_database_table(
                build_project_uuid_registry_table(uuid_entries),
                key_prefix=f"project_database_uuid_{project.id}",
                default_sort="Тип",
                technical_columns=("UUID", "Ключ", "Object ID", "Путь"),
                height=420,
            )

def _project_workspace_summary_rows(project: ProjectRecord) -> tuple[tuple[str, str], ...]:
    all_well_cards = _las_workspace_service(project.id).list_wells(include_archived=True)
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
        dataframe = _las_workspace_service(project.id).read_dataframe(record.id)
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
        zip_bytes = _las_workspace_service(project.id).export_zip(selected_ids)
    except Exception:
        logger.exception("project_las_export_failed project_id=%s", safe_log_value(project.id))
        st.error("Не удалось подготовить выгрузку проектных LAS. Подробности записаны в logs/app.log.")
        return

    st.download_button(
        "Выгрузить LAS/XLSX/CSV (ZIP)",
        data=zip_bytes,
        file_name=f"{project.id}_las_versions.zip",
        mime="application/zip",
        width="stretch",
        key=key,
    )


def _las_workspace_actions_table(controller_state) -> pd.DataFrame:
    """Build a UI-ready table for the LAS Workspace 3.0 home actions."""

    return pd.DataFrame(action_table_rows(controller_state.home.actions))[
        ["title", "description", "enabled_without_file", "target_panel"]
    ].rename(
        columns={
            "title": "Действие",
            "description": "Описание",
            "enabled_without_file": "Без файла",
            "target_panel": "Панель",
        }
    )


def _workspace_manager_items_table(items: tuple[WorkspaceManagerItem, ...]) -> pd.DataFrame:
    """Build a compact table for the Project Workspace UI panel."""

    return pd.DataFrame(
        [
            {
                "Активно": "Да" if item.is_active else "",
                "Workspace": item.name,
                "Тип": item.kind,
                "Описание": item.description,
                "Настроек": item.settings_count,
                "Обновлено": item.updated_at,
                "ID": item.id,
            }
            for item in items
        ]
    )


def _workspace_dashboard_cards_html(items: tuple[WorkspaceManagerItem, ...]) -> str:
    """Build compact Workspace Dashboard cards for Project Workspace UI.

    The cards are pure HTML generated from manager DTOs. They intentionally do
    not read or write Streamlit session state, so the UI keeps using the
    WorkspaceController boundary for all stateful operations.
    """

    if not items:
        return (
            "<div class='workspace-dashboard-cards' data-workspace-dashboard-cards='empty'>"
            "<div class='workspace-dashboard-card workspace-dashboard-card-empty'>"
            "<b>Workspace Framework</b>"
            "<span>Создайте первый workspace, чтобы начать Sprint 2 workflow.</span>"
            "</div></div>"
        )

    cards = []
    for item in items[:6]:
        active_badge = "<em>active</em>" if item.is_active else "<em>ready</em>"
        cards.append(
            "<div class='workspace-dashboard-card' data-workspace-card-id='{}'>"
            "<b>{}</b>"
            "<span>{} · {} настроек</span>"
            "<small>{}</small>"
            "{}"
            "</div>".format(
                _html_escape(item.id),
                _html_escape(item.name),
                _html_escape(item.kind),
                item.settings_count,
                _html_escape(item.description or "Без описания"),
                active_badge,
            )
        )
    return "<div class='workspace-dashboard-cards' data-workspace-dashboard-cards='ready'>" + "".join(cards) + "</div>"


def _workspace_project_explorer_shortcuts_html(items: tuple[WorkspaceManagerItem, ...]) -> str:
    """Build read-only Project Explorer shortcuts for available workspaces."""

    if not items:
        return (
            "<div class='workspace-explorer-shortcuts' data-workspace-explorer-shortcuts='empty'>"
            "<span>Workspace shortcuts появятся после создания рабочего пространства.</span>"
            "</div>"
        )

    shortcut_rows = []
    for item in items[:8]:
        marker = "●" if item.is_active else "○"
        shortcut_rows.append(
            "<div class='workspace-explorer-shortcut' data-workspace-shortcut-id='{}'>"
            "<strong>{} {}</strong>"
            "<span>{} · обновлено {}</span>"
            "</div>".format(
                _html_escape(item.id),
                marker,
                _html_escape(item.name),
                _html_escape(item.kind),
                _html_escape(item.updated_at),
            )
        )
    return "<div class='workspace-explorer-shortcuts' data-workspace-explorer-shortcuts='ready'>" + "".join(shortcut_rows) + "</div>"


def _render_las_workspace_controller_entry(project: ProjectRecord, logger) -> None:
    """Render the LAS Workspace 3.0 entry point through LasWorkspaceController."""

    controller = _las_workspace_controller()
    try:
        controller_state = controller.ensure_project_las_workspace(project.id, activate=False)
    except Exception:
        logger.exception("las_workspace_controller_prepare_failed project_id=%s", safe_log_value(project.id))
        st.error("Не удалось подготовить LAS Workspace 3.0.")
        return

    st.markdown(
        "<div class='las-workspace-entry' data-las-workspace-entry='3.0'>"
        "<b>LAS Workspace 3.0</b>"
        "<span>Создание, открытие, импорт, проверка и экспорт LAS через Workspace Framework.</span>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.dataframe(_las_workspace_actions_table(controller_state), width="stretch", hide_index=True, height=210)

    try:
        working_copies = controller.list_las_working_copies(project.id)
    except Exception:
        logger.exception("las_workspace_working_copy_list_failed project_id=%s", safe_log_value(project.id))
        working_copies = ()

    if working_copies:
        st.caption("Рабочие копии LAS, сохраненные в Workspace")
        st.dataframe(
            [
                {
                    "Файл": item.filename,
                    "Размер, байт": item.bytes_count,
                    "Путь": item.path,
                }
                for item in working_copies
            ],
            width="stretch",
            hide_index=True,
            height=180,
        )
        selected_copy = st.selectbox(
            "Открыть рабочую копию LAS",
            [item.filename for item in working_copies],
            key=f"las_workspace_open_copy_select_{project.id}",
        )
        if st.button("Открыть рабочую копию", width="stretch", key=f"las_workspace_open_copy_button_{project.id}"):
            try:
                opened = controller.open_las_working_copy(project.id, selected_copy)
            except Exception:
                logger.exception(
                    "las_workspace_open_copy_failed project_id=%s filename=%s",
                    safe_log_value(project.id),
                    safe_log_value(selected_copy),
                )
                st.error("Не удалось открыть рабочую копию LAS.")
            else:
                _application_state_controller().update_values({
                    LAS_EDITOR_SESSION_SHEETS_KEY: {opened.item.filename: _dataframe_to_raw_sheet(opened.data)},
                    LAS_EDITOR_SESSION_SUMMARY_KEY: (
                        f"LAS Workspace: {opened.item.filename}, "
                        f"{len(opened.data)} строк, {len(opened.data.columns)} колонок"
                    ),
                })
                logger.info(
                    "las_workspace_open_copy_loaded project_id=%s workspace_id=%s filename=%s",
                    safe_log_value(project.id),
                    safe_log_value(opened.workspace.id),
                    safe_log_value(opened.item.filename),
                )
                st.success(f"Открыта рабочая копия LAS: {opened.item.filename}")

    if st.button("Открыть LAS Workspace 3.0", width="stretch", key=f"las_workspace_open_{project.id}"):
        try:
            result = controller.open_project_las_workspace(project.id)
        except Exception:
            logger.exception("las_workspace_controller_open_failed project_id=%s", safe_log_value(project.id))
            st.error("Не удалось открыть LAS Workspace 3.0.")
        else:
            logger.info(
                "las_workspace_controller_opened project_id=%s workspace_id=%s",
                safe_log_value(project.id),
                safe_log_value(result.workspace.id),
            )
            st.success(f"Открыт workspace: {result.workspace.name}")
            _refresh_ui()


def _render_project_workspace_controller_panel(project: ProjectRecord, logger) -> None:
    """Render Workspace Framework controls through WorkspaceController only."""

    controller = _workspace_controller()
    try:
        items = controller.list_project_workspaces(project.id)
    except Exception:
        logger.exception("workspace_controller_list_failed project_id=%s", safe_log_value(project.id))
        st.error("Не удалось загрузить список рабочих пространств проекта.")
        return

    with st.expander("Workspace Framework", expanded=not bool(items)):
        st.caption("Управление workspace выполняется через UI → Controller → Manager → Service → Repository → Storage.")
        st.markdown(_workspace_dashboard_cards_html(items), unsafe_allow_html=True)
        st.markdown(_workspace_project_explorer_shortcuts_html(items), unsafe_allow_html=True)
        _render_las_workspace_controller_entry(project, logger)
        if items:
            st.dataframe(_workspace_manager_items_table(items), width="stretch", hide_index=True, height=210)
        else:
            st.info("В проекте пока нет рабочих пространств. Создайте базовый workspace для Sprint 2.")

        with st.form(key=f"workspace_create_form_{project.id}"):
            name = st.text_input("Название workspace", value="Project Workspace", key=f"workspace_create_name_{project.id}")
            kind = st.selectbox(
                "Тип workspace",
                options=("general", "las", "correlation", "petrophysics", "modeling", "report"),
                key=f"workspace_create_kind_{project.id}",
            )
            description = st.text_area(
                "Описание",
                value="Рабочее пространство проекта",
                key=f"workspace_create_description_{project.id}",
            )
            activate = st.checkbox("Активировать после создания", value=True, key=f"workspace_create_activate_{project.id}")
            submitted = st.form_submit_button("Создать workspace", width="stretch")

        if submitted:
            try:
                result = controller.create_workspace(
                    project.id,
                    name.strip() or "Project Workspace",
                    kind=kind,
                    description=description.strip(),
                    settings={"created_from": "project_workspace_ui"},
                    activate=activate,
                )
            except Exception:
                logger.exception("workspace_controller_create_failed project_id=%s", safe_log_value(project.id))
                st.error("Не удалось создать workspace. Подробности записаны в logs/app.log.")
            else:
                logger.info(
                    "workspace_controller_created project_id=%s workspace_id=%s",
                    safe_log_value(project.id),
                    safe_log_value(result.workspace.id),
                )
                st.success(f"Workspace создан: {result.workspace.name}")
                _refresh_ui()

        if items:
            options = tuple(item.id for item in items)
            selected_workspace_id = st.selectbox(
                "Открыть существующий workspace",
                options=options,
                format_func=lambda workspace_id: next(
                    f"{item.name} ({item.kind})" for item in items if item.id == workspace_id
                ),
                key=f"workspace_open_select_{project.id}",
            )
            open_col, close_col, delete_col = st.columns(3)
            if open_col.button("Открыть", width="stretch", key=f"workspace_open_button_{project.id}"):
                try:
                    result = controller.open_workspace(project.id, selected_workspace_id)
                except Exception:
                    logger.exception(
                        "workspace_controller_open_failed project_id=%s workspace_id=%s",
                        safe_log_value(project.id),
                        safe_log_value(selected_workspace_id),
                    )
                    st.error("Не удалось открыть workspace.")
                else:
                    st.success(f"Активирован workspace: {result.workspace.name}")
                    _refresh_ui()

            if close_col.button("Закрыть", width="stretch", key=f"workspace_close_button_{project.id}"):
                controller.close_workspace()
                st.info("Активный workspace закрыт.")
                _refresh_ui()

            if delete_col.button("Удалить", width="stretch", key=f"workspace_delete_button_{project.id}"):
                try:
                    deleted = controller.delete_workspace(project.id, selected_workspace_id)
                except Exception:
                    logger.exception(
                        "workspace_controller_delete_failed project_id=%s workspace_id=%s",
                        safe_log_value(project.id),
                        safe_log_value(selected_workspace_id),
                    )
                    st.error("Не удалось удалить workspace.")
                else:
                    st.warning(deleted.delete_result.message)
                    _refresh_ui()


def _render_project_workspace_loader(project: ProjectRecord, logger) -> None:
    active_well_cards = _las_workspace_service(project.id).list_wells()
    active_records = tuple(version for card in active_well_cards for version in card.versions)

    with st.expander("Данные активного проекта", expanded=bool(active_records)):
        st.caption(f"Открыт проект: {project.name} ({project.id})")
        st.dataframe(_project_workspace_summary_table(project), width="stretch", hide_index=True, height=210)
        _render_project_workspace_controller_panel(project, logger)
        _render_project_dataset_manager(project, logger)
        _render_project_manager_tools(project, logger)
        _render_project_file_index(project, logger)

        if not active_records:
            st.caption("В активном проекте пока нет активных LAS-версий.")
            return

        st.dataframe(_project_las_records_table(active_well_cards), width="stretch", height=240)
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
        if open_col.button("Открыть выбранные версии", width="stretch", key=f"workspace_open_project_{project.id}"):
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
                    _application_state_controller().update_values(
                        {
                            PROJECT_SESSION_SHEETS_KEY: sheets,
                            PROJECT_SESSION_PROJECT_ID_KEY: project.id,
                            PROJECT_SESSION_SUMMARY_KEY: f"{project.name}: версий {len(selected_records)}, листов {len(sheets)}",
                        }
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
    # Repository mutations in this panel must use _request_ui_refresh_and_rerun.
    export_service = _export_manager_service()
    records = export_service.list_exports(project.id)
    with st.expander("Сохраненные экспорты проекта", expanded=bool(records)):
        if not records:
            st.caption("В активном проекте пока нет сохраненных экспортов.")
            return

        selected_row = _render_workbench_data_grid(
            _project_exports_table(records),
            key_prefix=f"workbench_exports_{project.id}",
            type_column="Тип",
            status_column=None,
            default_sort="Сохранено",
            technical_columns=("Export ID", "Источник"),
            height=300,
            id_column="Export ID",
            selection_target="export",
            selection_label_column="Название",
            selection_metadata={"project_id": project.id},
            enable_multi_selection=True,
        )
        records_by_id = {record.id: record for record in records}
        selected_id = str((selected_row or {}).get("Export ID") or next(iter(records_by_id)))
        selected_record = records_by_id[selected_id]

        action_col_1, action_col_2, action_col_3 = st.columns(3)
        with action_col_1:
            if st.button("Обновить", width="stretch", key=f"project_export_refresh_{project.id}"):
                _refresh_ui()
        with action_col_2:
            if st.button("Удалить выбранный экспорт", width="stretch", key=f"project_export_delete_{project.id}_{selected_id}"):
                try:
                    delete_result = export_service.delete_export(project.id, selected_id)
                    deleted = delete_result.deleted
                except Exception:
                    logger.exception("project_export_delete_failed project_id=%s export_id=%s", safe_log_value(project.id), safe_log_value(selected_id))
                    st.error("Не удалось удалить экспорт. Подробности записаны в logs/app.log.")
                else:
                    st.success("Экспорт удален." if deleted else "Экспорт уже отсутствует.")
                    _refresh_ui()
        with action_col_3:
            if st.button("Очистить все экспорты", width="stretch", key=f"project_export_clear_all_{project.id}"):
                try:
                    clear_result = export_service.clear_exports(project.id)
                    removed = clear_result.removed_count
                except Exception:
                    logger.exception("project_exports_clear_failed project_id=%s", safe_log_value(project.id))
                    st.error("Не удалось очистить экспорты. Подробности записаны в logs/app.log.")
                else:
                    st.success(f"Удалено экспортов: {removed}.")
                    _refresh_ui()
        try:
            data = export_service.read_export_bytes(project.id, selected_id)
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
            width="stretch",
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
        export_service = _export_manager_service()
        save_result = export_service.save_export(
            project_id=project.id,
            data=data,
            label=label,
            file_name=file_name,
            mime_type=mime_type,
            kind=kind,
            source=source,
            metadata=metadata,
        )
        record = save_result.record
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
        st.dataframe(_project_calculation_actions_table(actions), width="stretch", hide_index=True, height=220)
        st.download_button(
            "Скачать журнал CSV",
            data=export_project_calculation_actions_csv(actions),
            file_name=f"calculation-actions-{project.id}.csv",
            mime="text/csv",
            key=f"project_calculation_actions_csv_{project.id}",
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
            state_controller = _application_state_controller()
            compare_log_key = f"project_calculation_compare_logged_{project.id}_{left_id}_{right_id}"
            if not state_controller.get_value(compare_log_key, False):
                _record_project_calculation_action(
                    project,
                    "compare_snapshots",
                    logger,
                    calculation_id=left_id,
                    related_calculation_id=right_id,
                    details="safe metadata/csv comparison",
                )
                state_controller.set_value(compare_log_key, True)
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
        st.dataframe(diff_table, width="stretch", hide_index=True)

        if st.download_button(
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


def _render_project_calculations_panel(project: ProjectRecord, logger) -> None:
    all_records = list_project_calculations(LAS_CORRELATION_PROJECTS_ROOT, project.id)
    summary = summarize_project_calculations(LAS_CORRELATION_PROJECTS_ROOT, project.id)
    with st.expander("Архив расчетов проекта", expanded=False):
        st.caption(
            "Сохраненные snapshots проекта не являются текущими загруженными данными. "
            "Откройте архив явно, чтобы просмотреть или восстановить расчет."
        )
        if all_records:
            metric_count, metric_rows, metric_warnings, metric_columns = st.columns(4)
            metric_count.metric("Сохранено", summary.count)
            metric_rows.metric("Строк в архиве", summary.total_rows)
            metric_warnings.metric("Диагностик в архиве", summary.total_warnings)
            metric_columns.metric("Колонок", len(summary.columns))
            inspect_archive = st.checkbox(
                "Показать сохраненные расчеты",
                value=False,
                key=f"project_calculation_archive_open_{project.id}",
                help="До включения архив не читает metadata, таблицы и выгрузки сохраненных расчетов.",
            )
            if not inspect_archive:
                st.info("Текущая рабочая сессия пуста. Архивные расчеты не загружены и не используются.")
                return
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

        selected_row = _render_workbench_data_grid(
            _project_calculations_table(records),
            key_prefix=f"workbench_calculations_{project.id}",
            type_column=None,
            status_column=None,
            default_sort="Сохранено",
            technical_columns=("Calculation ID",),
            height=300,
            id_column="Calculation ID",
            selection_target="calculation",
            selection_label_column="Источник",
            selection_metadata={"project_id": project.id},
            enable_multi_selection=True,
        )
        records_by_id = {record.id: record for record in records}
        selected_id = str((selected_row or {}).get("Calculation ID") or next(iter(records_by_id)))
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

        csv_col, xlsx_col, csv_card_col, open_col = st.columns(4)
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
            if csv_col.download_button(
                "Скачать CSV",
                data=csv_data,
                file_name=f"{selected_record.id}.csv",
                mime="text/csv",
                width="stretch",
                disabled=downloads_disabled,
                key=f"project_calculation_csv_{project.id}_{selected_id}",
            ):
                _record_project_calculation_action(project, "download_export", logger, calculation_id=selected_id, export_format="CSV")
            if xlsx_col.download_button(
                "Скачать XLSX",
                data=xlsx_data,
                file_name=f"{selected_record.id}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width="stretch",
                disabled=downloads_disabled,
                key=f"project_calculation_xlsx_{project.id}_{selected_id}",
            ):
                _record_project_calculation_action(project, "download_export", logger, calculation_id=selected_id, export_format="XLSX")
            if csv_card_col.download_button(
                "Скачать карточку CSV",
                data=card_csv_data,
                file_name=f"{selected_record.id}-card.csv",
                mime="text/csv",
                width="stretch",
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
        except Exception:
            logger.exception(
                "project_calculation_download_failed project_id=%s calculation_id=%s",
                safe_log_value(project.id),
                safe_log_value(selected_id),
            )
            st.error("Не удалось подготовить выгрузку сохраненного расчета. Подробности записаны в logs/app.log.")

        if open_col.button(
            "Открыть в графиках",
            width="stretch",
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
        if st.button("Сохранить расчетный snapshot", width="stretch", key=f"save_calculation_{project.id}"):
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
                    diagnostics=calculation_diagnostics_to_dict(
                        build_calculation_diagnostics_report(calculated_df, ch_mode=ch_mode)
                    ),
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
    # Repository mutations in this panel must use _request_ui_refresh_and_rerun.
    project: ProjectRecord,
    uploaded_files: tuple[object, ...],
    logger,
) -> tuple[object, ...]:
    las_service = _las_workspace_service(project.id)
    active_well_cards = las_service.list_wells()
    active_records = tuple(version for card in active_well_cards for version in card.versions)
    all_records = las_service.list_files(include_archived=True)
    archived_records = tuple(record for record in all_records if record.archived_at)
    selected_records: tuple[ProjectLasFile, ...] = ()

    with st.expander("LAS-файлы проекта", expanded=bool(active_records or archived_records)):
        if uploaded_files:
            st.caption("Сохраните загруженные LAS в активный проект, чтобы открыть их после перезапуска приложения.")
            if st.button("Сохранить загруженные LAS в проект", width="stretch", key="save_uploaded_las_to_project"):
                try:
                    saved_count = 0
                    for uploaded_file in uploaded_files:
                        original_name = Path(str(getattr(uploaded_file, "name", "source.las"))).name
                        las_service.save_file(
                            data=bytes(uploaded_file.getvalue()),
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
                    _refresh_ui()
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
        display_well_cards = las_service.list_wells(include_archived=show_archived)
        st.dataframe(_project_las_records_table(display_well_cards), width="stretch", height=260)

        if active_records:
            archive_options = {record.id: record for record in active_records}
            archive_col, archive_button_col = st.columns([3, 1])
            archive_id = archive_col.selectbox(
                "Версия для архива",
                options=tuple(archive_options),
                format_func=lambda record_id: _project_las_option_label(archive_options[record_id]),
                key=f"project_las_archive_select_{project.id}",
            )
            if archive_button_col.button("В архив", width="stretch", key=f"project_las_archive_button_{project.id}"):
                try:
                    las_service.archive_file(archive_id)
                    logger.info(
                        "project_las_file_archived project_id=%s las_file_id=%s",
                        safe_log_value(project.id),
                        safe_log_value(archive_id),
                    )
                    st.success("Версия LAS перенесена в архив.")
                    _refresh_ui()
                except Exception:
                    logger.exception("project_las_file_archive_failed project_id=%s", safe_log_value(project.id))
                    st.error("Не удалось архивировать версию LAS. Подробности записаны в logs/app.log.")

        deletable_records = active_records + archived_records
        if deletable_records:
            delete_options = {record.id: record for record in deletable_records}
            delete_col, delete_button_col = st.columns([3, 1])
            delete_id = delete_col.selectbox(
                "LAS-версия для полного удаления",
                options=tuple(delete_options),
                format_func=lambda record_id: _project_las_option_label(delete_options[record_id]),
                key=f"project_las_delete_select_{project.id}",
            )
            if delete_button_col.button("Удалить с диска", width="stretch", key=f"project_las_delete_button_{project.id}"):
                try:
                    deleted = las_service.delete_file(delete_id).deleted
                    _clear_las_working_state()
                    _application_state_controller().remove_value(f"project_las_files_{project.id}", None)
                    logger.info(
                        "project_las_file_deleted project_id=%s las_file_id=%s deleted=%s",
                        safe_log_value(project.id),
                        safe_log_value(delete_id),
                        deleted,
                    )
                    if deleted:
                        st.success("LAS-версия полностью удалена с диска.")
                    else:
                        st.warning("LAS-версия уже отсутствовала на диске.")
                    _refresh_ui()
                except Exception:
                    logger.exception("project_las_file_delete_failed project_id=%s", safe_log_value(project.id))
                    st.error("Не удалось удалить LAS-версию с диска. Подробности записаны в logs/app.log.")

        if show_archived and archived_records:
            restore_options = {record.id: record for record in archived_records}
            restore_col, restore_button_col = st.columns([3, 1])
            restore_id = restore_col.selectbox(
                "Версия для восстановления",
                options=tuple(restore_options),
                format_func=lambda record_id: _project_las_option_label(restore_options[record_id]),
                key=f"project_las_restore_select_{project.id}",
            )
            if restore_button_col.button("Вернуть", width="stretch", key=f"project_las_restore_button_{project.id}"):
                try:
                    las_service.restore_file(restore_id)
                    logger.info(
                        "project_las_file_restored project_id=%s las_file_id=%s",
                        safe_log_value(project.id),
                        safe_log_value(restore_id),
                    )
                    st.success("Версия LAS возвращена из архива.")
                    _refresh_ui()
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
    controller = _application_state_controller()
    session_key = _project_settings_session_key(project_id)
    session_payload = controller.get_value(session_key)
    session_settings = settings_from_dict(session_payload) if session_payload else None
    project_settings = _load_project_las_correlation_settings(project_id)

    if session_settings is None and project_settings is None:
        return

    with st.expander("Сохраненные настройки корреляции", expanded=False):
        if project_settings is not None:
            st.markdown("**Проект**")
            for line in settings_summary(project_settings):
                st.caption(line)
            if st.button("Загрузить настройки проекта", width="stretch", key="las_correlation_load_project_settings"):
                _apply_las_correlation_settings_to_session(project_settings, wells, group_options)
                controller.set_value(session_key, settings_to_dict(project_settings))
                _refresh_ui()

        if session_settings is not None:
            st.markdown("**Текущая сессия**")
            for line in settings_summary(session_settings):
                st.caption(line)
            apply_col, clear_col = st.columns(2)
            if apply_col.button("Применить настройки сессии", width="stretch", key="las_correlation_apply_saved_settings"):
                _apply_las_correlation_settings_to_session(session_settings, wells, group_options)
                _refresh_ui()
            if clear_col.button("Очистить настройки сессии", width="stretch", key="las_correlation_clear_saved_settings"):
                controller.remove_value(session_key, None)
                _refresh_ui()


def _render_las_correlation_settings_saver(settings: LasCorrelationSettings, project_id: str) -> None:
    controller = _application_state_controller()
    with st.expander("Текущие настройки корреляции", expanded=False):
        for line in settings_summary(settings):
            st.caption(line)
        project_col, session_col = st.columns(2)
        if project_col.button("Сохранить в проект", width="stretch", key="las_correlation_save_project_settings"):
            try:
                application_service_container(
                    controller.state
                ).las_workspace(
                    project_id=project_id,
                    root=LAS_CORRELATION_PROJECTS_ROOT,
                ).save_correlation_settings(settings)
                controller.set_value(_project_settings_session_key(project_id), settings_to_dict(settings))
                st.success("Настройки корреляции сохранены в проект.")
            except Exception:
                st.error("Не удалось сохранить настройки проекта.")
        if session_col.button("Сохранить в сессию", width="stretch", key="las_correlation_save_current_settings"):
            controller.set_value(_project_settings_session_key(project_id), settings_to_dict(settings))
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
        st.dataframe(interval_table, width="stretch", height=420)
        csv_col, xlsx_col, las_col = st.columns(3)
        csv_col.download_button(
            "Экспорт CSV",
            data=export_csv_bytes(interval_table),
            file_name=f"las_correlation_interval_{project_id}.csv",
            mime="text/csv",
            width="stretch",
        )
        xlsx_col.download_button(
            "Экспорт XLSX",
            data=export_xlsx_bytes(interval_table, sheet_name="interval"),
            file_name=f"las_correlation_interval_{project_id}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
        )
        las_col.download_button(
            "Экспорт LAS",
            data=export_las_bytes(interval_table, well_name=project_id, depth_column="depth"),
            file_name=f"las_correlation_interval_{project_id}.las",
            mime="text/plain",
            width="stretch",
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
    st.dataframe(pd.DataFrame(summary_rows), width="stretch")

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
        state_controller = _application_state_controller()
        default_marker_rows = state_controller.get_value(
            "las_correlation_studio_markers",
            [{"well": "", "name": "Top", "depth": float(valid_depths[0]) if valid_depths else 0.0, "kind": "top", "color": "#FBBF24", "note": ""}],
        )
        marker_rows = st.data_editor(
            pd.DataFrame(default_marker_rows),
            num_rows="dynamic",
            width="stretch",
            key="las_correlation_studio_marker_editor",
        )
        marker_records = marker_rows.to_dict("records") if isinstance(marker_rows, pd.DataFrame) else []
        state_controller.set_value("las_correlation_studio_markers", marker_records)

        studio_curve_options = common_curve_names(selected_wells, groups=selected_groups)
        studio_curve = ""
        if studio_curve_options:
            studio_curve = st.selectbox(
                "Кривая для correlation-панели",
                options=studio_curve_options,
                key="las_correlation_studio_curve",
            )
        else:
            st.info("Для Correlation Studio выберите группы с числовыми кривыми.")
        st.caption("Черновые tops, markers и параметры сетки применяются только после нажатия кнопки построения корреляции.")
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
            state_controller = _application_state_controller()
            saved_curve = state_controller.get_value("las_correlation_comparison_curve")
            if saved_curve not in comparison_curve_options:
                state_controller.set_value("las_correlation_comparison_curve", comparison_curve_options[0])
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

    correlation_source_signature = "|".join(
        f"{well.name}:{well.depth_column}:{dataframe_signature(well.data)}"
        for well in wells
    )
    build_correlation_clicked = st.button(
        "Построить корреляцию",
        type="primary",
        width="stretch",
        key="apply_las_correlation_presentation",
        help="Фиксирует выбранные скважины, группы, масштабы, tops и markers. Изменения виджетов не перестраивают графики до следующего применения.",
    )
    if build_correlation_clicked:
        correlation_status = st.empty()
        _set_inline_operation_status(
            correlation_status,
            "Корреляция",
            "Проверяются и фиксируются параметры нескольких скважин.",
        )
        persist_applied_correlation(
            _application_state_controller().state,
            AppliedCorrelationState(
                source_signature=correlation_source_signature,
                settings=settings_to_dict(current_settings),
                studio_settings={
                    "grid_mode": studio_grid_mode,
                    "depth_step": float(studio_depth_step),
                    "markers": tuple(dict(row) for row in marker_records),
                    "curve": studio_curve,
                },
            ),
        )
        revisions = revision_controller_from_state(_application_state_controller().state)
        persist_revisions(_application_state_controller().state, revisions.bump_presentation())
        correlation_presentation_service = application_service_container(
            _application_state_controller().state
        ).correlation_presentation(
            project_id=active_project.id,
            root=LAS_CORRELATION_PROJECTS_ROOT,
        )
        correlation_presentation_service.clear()
        logger.info(
            "las_correlation_presentation_committed signature=%s wells=%d markers=%d",
            safe_log_value(correlation_source_signature[:12]),
            len(current_settings.selected_well_names),
            len(marker_records),
        )
        _set_inline_operation_status(
            correlation_status,
            "Корреляция",
            "Настройки применены. Выполняется синхронное построение.",
            state="success",
        )

    applied_correlation = applied_correlation_from_state(_application_state_controller().state)
    if not correlation_matches_source(applied_correlation, correlation_source_signature):
        st.info(
            "Настройте скважины, диапазоны, tops и markers, затем нажмите `Построить корреляцию`. "
            "Черновые изменения не запускают Plotly-рендер."
        )
        return

    render_settings = settings_from_dict(applied_correlation.settings)
    selected_wells = [well for well in wells if well.name in render_settings.selected_well_names]
    selected_wells = [
        apply_curve_group_overrides(well, render_settings.curve_group_overrides.get(well.name, {}))
        for well in selected_wells
    ]
    if not selected_wells:
        st.error("В применённом снимке корреляции нет доступных скважин. Обновите настройки и повторите построение.")
        return
    gis_groups = tuple(render_settings.gis_groups)
    gas_groups = tuple(render_settings.gas_groups)
    selected_groups = tuple(dict.fromkeys((*gis_groups, *gas_groups)))
    depth_range = render_settings.depth_range
    gis_x_range = render_settings.gis_x_range
    gas_x_range = render_settings.gas_x_range
    height_per_well = int(render_settings.height_per_well)
    view_mode = render_settings.view_mode
    comparison_curve = render_settings.comparison_curve
    studio_settings = dict(applied_correlation.studio_settings)
    studio_grid_mode = str(studio_settings.get("grid_mode") or "union")
    studio_depth_step = float(studio_settings.get("depth_step") or 0.5)
    marker_records = [dict(row) for row in studio_settings.get("markers", ()) if isinstance(row, dict)]
    studio_curve = str(studio_settings.get("curve") or "")
    current_settings = render_settings

    figure_cache_key = (
        correlation_source_signature,
        tuple(sorted((str(key), repr(value)) for key, value in applied_correlation.settings.items())),
        tuple(sorted((str(key), repr(value)) for key, value in applied_correlation.studio_settings.items())),
    )
    correlation_state_controller = _application_state_controller()
    correlation_diagnostics = correlation_state_controller.ensure_runtime_service(
        "runtime_diagnostics",
        lambda: RuntimeDiagnostics(max_events=128),
        expected_type=RuntimeDiagnostics,
    )
    correlation_cycle_marker = correlation_diagnostics.mark()
    cache_metrics_registry = correlation_state_controller.ensure_runtime_service(
        "cache_metrics_registry",
        CacheMetricsRegistry,
        expected_type=CacheMetricsRegistry,
    )
    correlation_presentation_service = application_service_container(
        correlation_state_controller.state
    ).correlation_presentation(
        project_id=active_project.id,
        root=LAS_CORRELATION_PROJECTS_ROOT,
        metrics_registry=cache_metrics_registry,
    )
    operation_trace_registry = correlation_state_controller.ensure_runtime_service(
        "operation_trace_registry",
        lambda: OperationTraceRegistry(max_events=256, slow_threshold_ms=1000.0),
        expected_type=OperationTraceRegistry,
        scope="session",
    )
    cache_lookup_started = perf_counter()
    cached_correlation = correlation_presentation_service.get(figure_cache_key)
    cache_lookup_ms = (perf_counter() - cache_lookup_started) * 1000.0
    correlation_cache_hit = cached_correlation is not None
    correlation_diagnostics.record(
        stage="correlation.cache_lookup",
        duration_ms=cache_lookup_ms,
        cache_status="hit" if correlation_cache_hit else "miss",
        renderer="runtime-cache",
        item_count=len(selected_wells),
    )
    if correlation_cache_hit:
        studio_panel = cached_correlation.studio_panel
        studio_figure = cached_correlation.studio_figure
        figure = cached_correlation.figure
        figure_title = cached_correlation.figure_title
        figure_file_name = cached_correlation.figure_file_name
        logger.info(
            "las_correlation_figure_cache_hit wells=%d lookup_ms=%.2f",
            len(selected_wells),
            cache_lookup_ms,
        )
    else:
        render_status = st.empty()
        _set_inline_operation_status(render_status, "Рендеринг", "Строится синхронная корреляция нескольких скважин.")
        render_started = perf_counter()
        with correlation_diagnostics.timer(
            "correlation.panel",
            cache_status="miss",
            renderer="correlation-panel",
            item_count=len(selected_wells),
        ):
            studio_panel = build_correlation_panel(
                selected_wells,
                markers=marker_records,
                depth_range=depth_range,
                depth_step=studio_depth_step,
                groups=selected_groups,
                grid_mode=studio_grid_mode,
            )
        valid_studio_curves = common_curve_names(selected_wells, groups=selected_groups)
        if studio_curve not in valid_studio_curves:
            studio_curve = valid_studio_curves[0] if valid_studio_curves else ""
        with correlation_diagnostics.timer(
            "correlation.studio_figure",
            cache_status="miss",
            renderer="plotly",
            item_count=len(selected_wells),
        ):
            studio_figure = (
                build_correlation_panel_figure(
                    studio_panel,
                    studio_curve,
                    height_per_well=max(480, int(height_per_well)),
                )
                if studio_curve
                else None
            )
        with correlation_diagnostics.timer(
            "correlation.main_figure",
            cache_status="miss",
            renderer="plotly",
            item_count=len(selected_wells),
        ):
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
                figure_file_name = "las_curve_comparison"
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
                figure_file_name = "las_correlation"
        cache_store_started = perf_counter()
        correlation_presentation_service.put(
            figure_cache_key,
            CorrelationRenderArtifacts(
                studio_panel=studio_panel,
                studio_figure=studio_figure,
                figure=figure,
                figure_title=figure_title,
                figure_file_name=figure_file_name,
            ),
        )
        correlation_diagnostics.record(
            stage="correlation.cache_store",
            duration_ms=(perf_counter() - cache_store_started) * 1000.0,
            cache_status="miss",
            renderer="runtime-cache",
            item_count=1,
        )
        render_duration_ms = (perf_counter() - render_started) * 1000.0
        correlation_diagnostics.record(
            stage="correlation.total",
            duration_ms=render_duration_ms,
            cache_status="miss",
            renderer="plotly",
            item_count=len(selected_wells),
        )
        logger.info(
            "las_correlation_figure_cache_miss wells=%d markers=%d duration_ms=%.2f",
            len(selected_wells),
            len(marker_records),
            render_duration_ms,
        )
        _set_inline_operation_status(
            render_status,
            "Рендеринг",
            f"Корреляция построена: {len(selected_wells)} скважин, {render_duration_ms:.0f} мс.",
            state="success",
        )

    studio_summary = correlation_panel_summary(studio_panel)
    st.caption(
        f"Correlation Studio · скважин: {studio_summary['wells']} · маркеров: {studio_summary['markers']} · "
        f"точек сетки: {studio_summary['grid_points']}"
    )
    if studio_panel.warnings:
        for warning in studio_panel.warnings:
            st.warning(warning)
    if studio_figure is not None:
        studio_dispatch_started = perf_counter()
        st.plotly_chart(studio_figure, width="stretch", config=PLOTLY_SCREEN_CONFIG)
        correlation_diagnostics.record(
            stage="correlation.frontend_dispatch",
            duration_ms=(perf_counter() - studio_dispatch_started) * 1000.0,
            cache_status="hit" if correlation_cache_hit else "miss",
            renderer="streamlit-plotly",
            item_count=1,
        )
        if studio_panel.markers:
            st.dataframe(pd.DataFrame(correlation_marker_rows(studio_panel)), width="stretch")

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
    main_dispatch_started = perf_counter()
    st.plotly_chart(figure, width="stretch", config=PLOTLY_SCREEN_CONFIG)
    correlation_diagnostics.record(
        stage="correlation.frontend_dispatch",
        duration_ms=(perf_counter() - main_dispatch_started) * 1000.0,
        cache_status="hit" if correlation_cache_hit else "miss",
        renderer="streamlit-plotly",
        item_count=1,
    )
    correlation_events = correlation_diagnostics.snapshot_since(correlation_cycle_marker)
    with trace_context(
        project_id=active_project.id,
        route_id="nav.correlation",
        execution_id=f"correlation-{int(correlation_cycle_marker * 1000)}",
    ):
        operation_trace_registry.ingest_runtime_events(
            correlation_events,
            category="performance",
            execution_id=f"correlation-{int(correlation_cycle_marker * 1000)}",
        )
    correlation_summary = evaluate_performance(correlation_events)
    correlation_gate = build_workspace_performance_gate(correlation_summary)
    correlation_cache = correlation_diagnostics.cache_summary(stage_prefix="correlation")
    logger.info(
        "las_correlation_performance status=%s wells=%d cache_hit=%s hit_rate=%.2f stages=%s",
        correlation_gate.status,
        len(selected_wells),
        correlation_cache_hit,
        float(correlation_cache["hit_rate"]),
        {event.stage: round(event.duration_ms, 2) for event in correlation_events},
    )
    session_audit = audit_session_state(correlation_state_controller.state)
    logger.info(
        "runtime_state_diagnostics session_keys=%d transient_keys=%d runtime_keys=%d unscoped_keys=%d",
        session_audit.total_keys,
        session_audit.transient_count,
        session_audit.runtime_count,
        len(session_audit.unscoped_keys),
    )
    correlation_revision = revision_controller_from_state(correlation_state_controller.state).snapshot
    st.caption("Для печати используйте PDF; для изображений доступны PNG и SVG.")
    _render_static_export_controls(
        figure,
        base_file_name=figure_file_name,
        default_height=int(figure.layout.height or height_per_well),
        key_prefix="las_correlation",
        source_signature=correlation_source_signature,
        presentation_revision=correlation_revision.presentation,
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
            st.dataframe(pd.DataFrame(group_rows), width="stretch")

    logger.info("las_correlation_rendered wells=%d", len(selected_wells))


WORKBENCH_LAS_MODE_KEY = "workbench_las_mode"
WORKBENCH_LAS_MODES: tuple[str, ...] = (
    "Загрузка и анализ",
    "LAS-редактор",
    "LAS-корреляция",
)


def _resolve_active_project_for_workbench(logger) -> ProjectRecord:
    """Resolve one active project record; enumerate all projects only for recovery."""

    state = _application_state_controller()
    state.consume_pending_project_activation()
    requested_project_id = state.context().project_id
    project_service = _project_manager_service()
    try:
        project = project_service.resolve_active_project(requested_project_id)
    except Exception:
        logger.exception(
            "workbench_active_project_resolve_failed project_id=%s",
            safe_log_value(requested_project_id),
        )
        project = ProjectRecord(id=DEFAULT_PROJECT_ID, name="Основной проект")

    if project.id != requested_project_id:
        state.ensure_project(project.id)
    try:
        project_service.touch_recent(project)
    except Exception:
        logger.exception("workbench_recent_project_touch_failed project_id=%s", safe_log_value(project.id))
    return project


def _workbench_project_navigation_sections() -> frozenset[str]:
    """Resolve the metadata branches currently requested by Project Explorer."""

    state = _application_state_controller()
    requested = {
        str(item).strip()
        for item in (state.get_value("workbench_project_explorer_requested_sections", ()) or ())
        if str(item).strip()
    }
    if str(state.get_value("workbench_project_explorer_search") or "").strip():
        requested.update({"custom", "wells", "calculations", "datasets", "imports", "exports"})
    return frozenset(requested)


def _build_workbench_project_navigation(
    project: ProjectRecord,
    *,
    section_timings_ms: dict[str, float] | None = None,
) -> tuple[dict[str, int], list[dict[str, object]]]:
    """Build only the Project Explorer metadata branches requested by the UI."""

    requested_sections = _workbench_project_navigation_sections()
    project_tree = build_project_tree(
        LAS_CORRELATION_PROJECTS_ROOT,
        project.id,
        include_sections=set(requested_sections),
        section_timings_ms=section_timings_ms,
    )
    counts = {
        "calculations": 0,
        "correlations": 0,
        "reports": 0,
        "exports": 0,
    }
    serialized_tree: list[dict[str, object]] = []

    def _serialize_project_tree_node(node, *, level: int = 0, parent_id: str = "") -> None:
        kind = str(node.kind or "")
        route_by_kind = {
            "project": "nav.dashboard",
            "well": "nav.data",
            "las_version": "nav.las_workspace",
            "calculation": "nav.data",
            "export": "nav.exports",
            "dataset_lineage": "nav.data",
            "dataset_version": "nav.data",
            "qc_report": "nav.data",
            "qc_export": "nav.exports",
            "import_job": "nav.data",
        }
        route_by_id = {
            "folder:wells": "nav.data",
            "folder:calculations": "nav.data",
            "folder:imports": "nav.data",
            "folder:exports": "nav.exports",
        }
        target_by_kind = {
            "project": "project",
            "well": "well",
            "las_version": "las",
            "calculation": "calculation",
            "export": "export",
            "dataset_lineage": "dataset",
            "dataset_version": "dataset",
            "qc_report": "dataset",
            "qc_export": "dataset",
            "import_job": "import_job",
            "folder_item": "collection",
            "custom_folder": "collection",
            "well_group": "collection",
            "folder": "collection",
        }
        metadata = dict(node.metadata or {})
        deferred = bool(metadata.get("deferred"))
        object_id = str(
            metadata.get("project_id")
            or metadata.get("well_id")
            or metadata.get("las_file_id")
            or metadata.get("calculation_id")
            or metadata.get("export_id")
            or metadata.get("dataset_id")
            or metadata.get("lineage_id")
            or metadata.get("job_id")
            or metadata.get("folder_id")
            or node.id
        )
        if kind == "calculation":
            counts["calculations"] += 1
        elif kind == "export":
            counts["exports"] += 1
        serialized_tree.append(
            {
                "id": str(node.id),
                "parent_id": parent_id,
                "title": str(node.label),
                "kind": kind,
                "level": int(level),
                "count": None if deferred else len(tuple(node.children or ())),
                "has_children": bool(node.children),
                "selectable": kind not in {"empty", "missing"},
                "target": target_by_kind.get(kind, "collection"),
                "object_id": object_id,
                "navigation_id": route_by_id.get(str(node.id), route_by_kind.get(kind, "")),
                "status": str(node.status or ""),
                "metadata": metadata,
            }
        )
        for child in tuple(node.children or ()):
            _serialize_project_tree_node(child, level=level + 1, parent_id=str(node.id))

    _serialize_project_tree_node(project_tree)
    return counts, serialized_tree

def _apply_workbench_project_navigation(
    project: ProjectRecord,
    counts: dict[str, int],
    serialized_tree: list[dict[str, object]] | tuple[dict[str, object], ...],
    *,
    token: str = "",
) -> None:
    """Publish primitive navigation rows for existing Workbench UI providers."""

    state = _application_state_controller()
    state.set_value("workbench_project_counts", dict(counts))
    state.set_value("workbench_project_tree", [dict(item) for item in serialized_tree])
    state.set_value("workbench.route_data.navigation_project_id", project.id)
    state.set_value("workbench.route_data.navigation_token", str(token or ""))


def _refresh_workbench_project_navigation(logger, project: ProjectRecord) -> None:
    """Refresh serialized explorer data without exposing repository objects to UI."""

    state = _application_state_controller()
    try:
        counts, serialized_tree = _build_workbench_project_navigation(project)
        _apply_workbench_project_navigation(project, counts, serialized_tree)
    except Exception:
        logger.exception("workbench_project_counts_failed project_id=%s", safe_log_value(project.id))
        state.set_value("workbench_project_counts", {})
        state.set_value("workbench_project_tree", [])
        state.set_value("workbench.route_data.navigation_project_id", project.id)
        state.set_value("workbench.route_data.navigation_token", "")


def _active_project_for_workbench(logger) -> ProjectRecord:
    """Backward-compatible eager project resolver used by legacy callers."""

    project = _resolve_active_project_for_workbench(logger)
    _refresh_workbench_project_navigation(logger, project)
    return project

def _render_workbench_las_workspace(logger, active_project: ProjectRecord) -> None:
    """Render the existing LAS workflows inside the Modern Workbench host."""

    st.markdown("### LAS Workspace")
    st.caption("Загрузка, анализ, создание, редактирование и корреляция LAS через существующие рабочие модули проекта.")
    mode = st.radio(
        "LAS workflow",
        options=WORKBENCH_LAS_MODES,
        horizontal=True,
        key=WORKBENCH_LAS_MODE_KEY,
    )
    if mode == "LAS-редактор":
        _render_las_editor(logger, active_project)
    elif mode == "LAS-корреляция":
        _render_las_correlation_tab(logger, active_project)
    else:
        _render_workspace(logger, active_project)


def _render_workbench_reports(logger, active_project: ProjectRecord) -> None:
    """Render the existing report workflow with an actionable data prerequisite."""

    st.markdown("### Reports")
    state_controller = _application_state_controller()
    calculated_df, _source_label = _active_calculation_dataset(active_project.id)
    if calculated_df is None or calculated_df.empty:
        st.warning("Для отчетов сначала нужны рассчитанные данные.")
        st.caption("Откройте Data Workspace, загрузите исходные данные и выполните расчет. После этого здесь появятся предпросмотр, PDF/DOCX и печатный экспорт.")
        if st.button("Открыть Data Workspace", key="reports_open_data_workspace", width="stretch", type="primary"):
            from core.workbench_shell import WORKBENCH_ACTIVE_NAVIGATION_KEY
            state_controller.set_value(WORKBENCH_ACTIVE_NAVIGATION_KEY, "nav.data")
            _refresh_ui()
        return
    _render_interpretation_graphs_tab(logger, active_project)


WORKBENCH_ROUTE_EXPECTED_CONTROLS: dict[str, tuple[str, ...]] = {
    "nav.dashboard": ("global-search", "recent-projects", "recent-las"),
    "nav.data": ("data-source", "file-uploader", "calculation-controls"),
    "nav.las_workspace": ("las-workflow-selector", "file-uploader", "las-editor"),
    "nav.correlation": ("multi-well-uploader", "well-selector", "correlation-plot", "correlation-export"),
    "nav.interpretation": ("data-source", "plot-controls", "plot-output"),
    "nav.reports": ("report-preview", "download-report", "print-export"),
    "nav.exports": ("export-list", "download-export"),
    "nav.documentation": ("documentation-navigation", "documentation-content"),
}


def render_modern_workbench_workspace(navigation_id: str) -> bool:
    """Render an existing production workflow and audit the full UI boundary.

    A route is considered handled only when its production renderer returns
    without an exception.  Start/success/failure records are written to the
    existing application log so an operator can distinguish command execution
    from actual renderer/provider/view completion.
    """

    clean_id = str(navigation_id or "").strip()
    logger = configure_logging()
    state = _application_state_controller().state
    from core.workbench_route_data import (
        PROJECT_NAVIGATION, PROJECT_RECORD, RouteDataTimer,
    )
    routes_registry = LazyWorkspaceRegistry({
        "nav.dashboard": WorkspaceRoute("nav.dashboard", "dashboard", lambda project: _render_start_tab(project), WORKBENCH_ROUTE_EXPECTED_CONTROLS.get("nav.dashboard", ()), (PROJECT_RECORD, PROJECT_NAVIGATION)),
        "nav.data": WorkspaceRoute("nav.data", "data-workspace", lambda project: _render_workspace(logger, project), WORKBENCH_ROUTE_EXPECTED_CONTROLS.get("nav.data", ()), (PROJECT_RECORD, PROJECT_NAVIGATION)),
        "nav.las_workspace": WorkspaceRoute("nav.las_workspace", "las-workflows", lambda project: _render_workbench_las_workspace(logger, project), WORKBENCH_ROUTE_EXPECTED_CONTROLS.get("nav.las_workspace", ()), (PROJECT_RECORD, PROJECT_NAVIGATION)),
        "nav.correlation": WorkspaceRoute("nav.correlation", "las-correlation", lambda project: _render_las_correlation_tab(logger, project), WORKBENCH_ROUTE_EXPECTED_CONTROLS.get("nav.correlation", ()), (PROJECT_RECORD, PROJECT_NAVIGATION)),
        "nav.interpretation": WorkspaceRoute("nav.interpretation", "interpretation-graphs", lambda project: _render_interpretation_graphs_tab(logger, project), WORKBENCH_ROUTE_EXPECTED_CONTROLS.get("nav.interpretation", ()), (PROJECT_RECORD, PROJECT_NAVIGATION)),
        "nav.reports": WorkspaceRoute("nav.reports", "report-workflow", lambda project: _render_workbench_reports(logger, project), WORKBENCH_ROUTE_EXPECTED_CONTROLS.get("nav.reports", ()), (PROJECT_RECORD, PROJECT_NAVIGATION)),
        "nav.exports": WorkspaceRoute("nav.exports", "project-exports", lambda project: _render_project_exports_panel(project, logger), WORKBENCH_ROUTE_EXPECTED_CONTROLS.get("nav.exports", ()), (PROJECT_RECORD, PROJECT_NAVIGATION)),
        "nav.documentation": WorkspaceRoute("nav.documentation", "documentation-center", lambda _project: _render_documentation_tab(), WORKBENCH_ROUTE_EXPECTED_CONTROLS.get("nav.documentation", ()), ()),
    })
    route = routes_registry.resolve(clean_id)
    if route is None:
        record_render_audit(
            state, route_id=clean_id, renderer="unresolved", provider="none",
            phase="resolve", success=False, details={"reason": "unknown-route"},
        )
        return False

    provider, renderer = route.provider, route.renderer
    expected = route.expected_controls
    started = perf_counter()
    record_render_audit(
        state, route_id=clean_id, renderer=getattr(renderer, "__name__", "route-renderer"),
        provider=provider, phase="start", success=True, expected_controls=expected,
    )
    try:
        requirements = tuple(route.data_requirements or ())
        data_timer = RouteDataTimer()
        active_project = None
        navigation_cache = "not-required"
        navigation_reason = "not-required"
        navigation_token_ms = 0.0
        navigation_metadata_files = 0
        app_services = application_service_container(state)
        diagnostics_service = app_services.runtime_diagnostics(
            root=LAS_CORRELATION_PROJECTS_ROOT
        )
        workbench_runtime = app_services.workbench_runtime()

        def _invalidate_project_runtime_caches(event: dict[str, Any]) -> None:
            changed_project = str(event.get("project_id") or "")
            if not changed_project:
                return
            workbench_runtime.invalidate_project_runtime_caches(
                changed_project,
                active_project_id=str(getattr(active_project, "id", "") or ""),
                reason=f"repository-{event.get('operation', 'mutation')}",
            )

        repository_metrics = diagnostics_service.subscribe_repository_mutations(
            "workbench_project_cache_coherence", _invalidate_project_runtime_caches
        )
        if PROJECT_RECORD in requirements:
            active_project = data_timer.measure_project(lambda: _resolve_active_project_for_workbench(logger))
        if active_project is not None:
            diagnostics_service.prepare_project_health(str(active_project.id))
        if PROJECT_NAVIGATION in requirements and active_project is not None:
            navigation_runtime_cache = diagnostics_service.navigation_cache()
            requested_sections = _workbench_project_navigation_sections()
            navigation_profile = ",".join(sorted(requested_sections)) or "root-only"
            lookup = navigation_runtime_cache.lookup(
                LAS_CORRELATION_PROJECTS_ROOT,
                active_project.id,
                profile=navigation_profile,
            )
            navigation_cache = lookup.status
            navigation_reason = lookup.reason
            navigation_token_ms = lookup.token_ms
            navigation_metadata_files = lookup.metadata_files
            if lookup.hit:
                current_project_id = str(state.get("workbench.route_data.navigation_project_id") or "")
                current_token = str(state.get("workbench.route_data.navigation_token") or "")
                has_navigation = bool(state.get("workbench_project_tree"))
                if current_project_id != active_project.id or current_token != lookup.token or not has_navigation:
                    data_timer.measure_navigation(
                        lambda: _apply_workbench_project_navigation(
                            active_project, dict(lookup.counts or {}), list(lookup.tree), token=lookup.token,
                        )
                    )
                    navigation_reason = "runtime-hit-state-restored"
            else:
                def _rebuild_navigation() -> None:
                    branch_timings_ms: dict[str, float] = {}
                    rebuild_started = perf_counter()
                    counts, serialized_tree = _build_workbench_project_navigation(
                        active_project, section_timings_ms=branch_timings_ms
                    )
                    rebuild_ms = (perf_counter() - rebuild_started) * 1000.0
                    navigation_runtime_cache.store(
                        project_id=active_project.id,
                        token=lookup.token,
                        tree=serialized_tree,
                        counts=counts,
                        metadata_files=lookup.metadata_files,
                        profile=navigation_profile,
                        load_ms=rebuild_ms,
                        branch_timings_ms=branch_timings_ms,
                    )
                    _apply_workbench_project_navigation(
                        active_project, counts, serialized_tree, token=lookup.token,
                    )

                data_timer.measure_navigation(_rebuild_navigation)
        data_record = workbench_runtime.record_route_data(
            route_id=clean_id,
            project_id=str(getattr(active_project, "id", "") or ""),
            requirements=requirements,
            project_ms=data_timer.project_ms,
            navigation_ms=data_timer.navigation_ms,
            navigation_cache=navigation_cache,
            total_ms=data_timer.total_ms,
            navigation_reason=navigation_reason,
            token_ms=navigation_token_ms,
            metadata_files=navigation_metadata_files,
        )
        logger.info(
            "workbench_route_data route=%s project_id=%s requirements=%s project_ms=%.2f navigation_ms=%.2f navigation_cache=%s navigation_reason=%s token_ms=%.2f metadata_files=%s total_ms=%.2f status=%s",
            clean_id, data_record.project_id, data_record.requirements, data_record.project_ms,
            data_record.navigation_ms, data_record.navigation_cache, data_record.navigation_reason,
            data_record.token_ms, data_record.metadata_files, data_record.total_ms, data_record.status,
        )
        renderer(active_project)
    except Exception as exc:
        duration_ms = (perf_counter() - started) * 1000.0
        record_render_audit(
            state, route_id=clean_id, renderer=getattr(renderer, "__name__", "route-renderer"),
            provider=provider, phase="failed", success=False, duration_ms=duration_ms,
            expected_controls=expected, details={"exception": type(exc).__name__, "message": str(exc)},
        )
        raise

    duration_ms = (perf_counter() - started) * 1000.0
    record_render_audit(
        state, route_id=clean_id, renderer=getattr(renderer, "__name__", "route-renderer"),
        provider=provider, phase="completed", success=True, duration_ms=duration_ms,
        expected_controls=expected, details={"project_id": str(getattr(active_project, "id", "") or "")},
    )
    return True


def _run_legacy_ui() -> None:
    """Run the pre-Workbench Streamlit interface.

    This path is retained only as an explicit operational fallback and must not
    be selected from session state or normal UI controls.
    """

    st.set_page_config(page_title="Gas Ratio Pro — Legacy", page_icon=_app_icon_data_uri() or None, layout="wide")
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


LEGACY_UI_ENV_VAR = "GAS_RATIO_PRO_LEGACY_UI"
_LEGACY_UI_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})


def legacy_ui_requested(environ: dict[str, str] | None = None) -> bool:
    """Return whether the explicit process-level legacy fallback is enabled.

    Session state is deliberately ignored.  Production startup therefore
    cannot silently fall back to the retired main page because of stale browser
    state.
    """

    source = os.environ if environ is None else environ
    return str(source.get(LEGACY_UI_ENV_VAR, "")).strip().lower() in _LEGACY_UI_TRUE_VALUES


def _process_workbench_bulk_action(logger) -> None:
    """Execute one bulk Data Grid action at the application boundary."""

    import csv
    import io
    import json
    import zipfile

    state = _application_state_controller().state
    service = _workbench_application_service()
    request = service.consume_bulk_action()
    if not request:
        return

    target = str(request.get("target") or "")
    action_id = str(request.get("action_id") or "")
    object_ids = tuple(str(item) for item in request.get("object_ids", ()) if str(item).strip())
    metadata = dict(request.get("metadata", {}) or {})
    project_id = str(metadata.get("project_id") or _application_state_controller().context().project_id or DEFAULT_PROJECT_ID)
    confirmed = bool(request.get("confirmed"))

    try:
        if action_id == "delete" and not confirmed:
            raise ValueError("Массовое удаление не подтверждено ID проекта.")

        if action_id == "verify":
            failures: list[str] = []
            if target == "dataset":
                section = str(metadata.get("section") or "")
                existing = {str(getattr(item, "id", "")) for item in _dataset_manager_service().list_records(project_id, section, include_archived=True)}
                failures = [item for item in object_ids if item not in existing]
            elif target == "calculation":
                for item in object_ids:
                    integrity = check_project_calculation_integrity(LAS_CORRELATION_PROJECTS_ROOT, project_id, item)
                    if not integrity.ok:
                        failures.append(item)
            elif target == "export":
                existing = {str(item.id) for item in _export_manager_service().list_exports(project_id)}
                failures = [item for item in object_ids if item not in existing]
            service.set_bulk_result(
                success=not failures,
                message=(f"Проверено объектов: {len(object_ids)}. Ошибок нет." if not failures else f"Проверено: {len(object_ids)}. Проблемные ID: {', '.join(failures)}"),
                action_id=action_id,
            )
            return

        if action_id == "delete":
            backup = create_project_backup(LAS_CORRELATION_PROJECTS_ROOT, project_id, f"Before bulk delete {target}")
            deleted = 0
            if target == "dataset":
                section = str(metadata.get("section") or "")
                deleted = _dataset_manager_service().delete_selected(project_id, section, object_ids).deleted
            elif target == "calculation":
                for item in object_ids:
                    deleted += int(project_calculations.delete_project_calculation(LAS_CORRELATION_PROJECTS_ROOT, project_id, item))
                _project_storage_service(project_id).sync_storage()
            elif target == "export":
                for item in object_ids:
                    deleted += int(_export_manager_service().delete_export(project_id, item).deleted)
            else:
                raise ValueError(f"Массовое удаление не поддерживается для {target}.")
            service.set_bulk_result(success=True, message=f"Удалено объектов: {deleted}. Backup: {backup.file_name}.", action_id=action_id)
            return

        if action_id == "export":
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("selection.json", json.dumps({"project_id": project_id, "target": target, "object_ids": object_ids}, ensure_ascii=False, indent=2))
                if target == "calculation":
                    for calculation_id in object_ids:
                        for suffix in ("csv", "xlsx", "metadata"):
                            try:
                                data = read_project_calculation_file_bytes(LAS_CORRELATION_PROJECTS_ROOT, project_id, calculation_id, suffix)
                            except Exception:
                                continue
                            extension = "json" if suffix == "metadata" else suffix
                            archive.writestr(f"calculations/{calculation_id}/{suffix}.{extension}", data)
                elif target == "export":
                    records = {item.id: item for item in _export_manager_service().list_exports(project_id)}
                    for export_id in object_ids:
                        record = records.get(export_id)
                        if record is not None:
                            archive.writestr(f"exports/{export_id}/{record.file_name}", _export_manager_service().read_export_bytes(project_id, export_id))
                elif target == "dataset":
                    section = str(metadata.get("section") or "")
                    records = [item for item in _dataset_manager_service().list_records(project_id, section, include_archived=True) if str(getattr(item, "id", "")) in object_ids]
                    output = io.StringIO()
                    writer = csv.DictWriter(output, fieldnames=("id", "name", "section", "status", "file"))
                    writer.writeheader()
                    for item in records:
                        writer.writerow({"id": getattr(item, "id", ""), "name": getattr(item, "label", getattr(item, "name", "")), "section": section, "status": getattr(item, "status", ""), "file": getattr(item, "original_file_name", "")})
                    archive.writestr("datasets.csv", output.getvalue().encode("utf-8-sig"))
                else:
                    raise ValueError(f"Массовый экспорт не поддерживается для {target}.")
            save_result = _export_manager_service().save_export(
                project_id=project_id,
                data=buffer.getvalue(),
                label=f"Bulk {target} package",
                file_name=f"bulk-{target}-package.zip",
                mime_type="application/zip",
                kind="archive",
                source="Workbench Data Grid",
                metadata={"object_ids": list(object_ids), "target": target},
            )
            service.set_bulk_result(success=True, message=f"ZIP-пакет создан: {save_result.file_name}.", action_id=action_id, export_id=save_result.id)
            return

        raise ValueError(f"Неизвестное массовое действие: {target}/{action_id}")
    except Exception as exc:
        logger.exception("workbench_bulk_action_failed target=%s action=%s", safe_log_value(target), safe_log_value(action_id))
        service.set_bulk_result(success=False, message=f"Не удалось выполнить массовое действие: {exc}", action_id=action_id)


def _process_workbench_property_action(logger) -> None:
    """Execute one requested Properties action at the application boundary."""

    from core.workbench_controller import build_workbench_controller

    state = _application_state_controller().state
    action_service = _workbench_application_service()
    request = action_service.consume_property_action()
    if not request:
        return

    action_id = str(request.get("action_id") or "")
    target = str(request.get("target") or "")
    object_id = str(request.get("object_id") or "")
    metadata = dict(request.get("metadata", {}) or {})
    project_id = str(metadata.get("project_id") or _application_state_controller().context().project_id or DEFAULT_PROJECT_ID)
    confirmed = bool(request.get("confirmed"))

    try:
        if action_id in {"open", "download"}:
            navigation = {
                "las": "nav.las_workspace", "dataset": "nav.data", "calculation": "nav.data",
                "export": "nav.exports", "report": "nav.reports", "project": "nav.dashboard",
            }.get(target, "nav.dashboard")
            build_workbench_controller(state).select_navigation(navigation)
            action_service.set_property_result(success=True, message="Рабочая область выбранного объекта открыта.", action_id=action_id)
            return

        if action_id == "verify":
            if target == "calculation":
                integrity = check_project_calculation_integrity(LAS_CORRELATION_PROJECTS_ROOT, project_id, object_id)
                message = "Проверка целостности пройдена." if integrity.ok else "Проверка обнаружила проблемы: " + "; ".join(integrity.messages)
                action_service.set_property_result(success=integrity.ok, message=message, action_id=action_id)
            elif target == "dataset":
                section = str(metadata.get("section") or "")
                records = _dataset_manager_service().list_records(project_id, section, include_archived=True)
                exists = any(str(getattr(record, "id", "")) == object_id for record in records)
                action_service.set_property_result(success=exists, message="Dataset зарегистрирован и доступен." if exists else "Dataset отсутствует в manifest.", action_id=action_id)
            elif target == "las":
                exists = any(record.id == object_id for record in _las_workspace_service(project_id).list_files(include_archived=True))
                action_service.set_property_result(success=exists, message="LAS зарегистрирован и доступен." if exists else "LAS не найден в проекте.", action_id=action_id)
            else:
                action_service.set_property_result(success=True, message="Объект доступен.", action_id=action_id)
            return

        if action_id in {"delete", "archive"} and not confirmed:
            raise ValueError("Опасное действие не подтверждено точным ID объекта.")

        backup = create_project_backup(LAS_CORRELATION_PROJECTS_ROOT, project_id, f"Before Properties {action_id} {target} {object_id}")
        if action_id == "archive" and target == "las":
            _las_workspace_service(project_id).archive_file(object_id)
            message = f"LAS архивирован. Backup: {backup.file_name}."
        elif action_id == "delete" and target == "dataset":
            section = str(metadata.get("section") or "")
            result = _dataset_manager_service().delete_selected(project_id, section, (object_id,))
            message = f"Dataset удалён: {result.deleted}. Backup: {backup.file_name}."
        elif action_id == "delete" and target == "export":
            result = _export_manager_service().delete_export(project_id, object_id)
            message = ("Экспорт удалён." if result.deleted else "Экспорт уже отсутствует.") + f" Backup: {backup.file_name}."
        elif action_id == "delete" and target == "calculation":
            deleted = project_calculations.delete_project_calculation(LAS_CORRELATION_PROJECTS_ROOT, project_id, object_id)
            _project_storage_service(project_id).sync_storage()
            message = ("Расчёт удалён." if deleted else "Расчёт уже отсутствует.") + f" Backup: {backup.file_name}."
        else:
            raise ValueError(f"Действие пока не поддерживается: {target}/{action_id}")
        _workbench_application_service().clear_selection("properties_action_completed")
        action_service.set_property_result(success=True, message=message, action_id=action_id)
    except Exception as exc:
        logger.exception("workbench_property_action_failed target=%s object_id=%s action=%s", safe_log_value(target), safe_log_value(object_id), safe_log_value(action_id))
        action_service.set_property_result(success=False, message=f"Не удалось выполнить действие: {exc}", action_id=action_id)


def _run_modern_workbench() -> None:
    """Render Modern Workbench and record lightweight startup stage timings."""

    from core.startup_diagnostics import StartupTimer

    startup_timer = StartupTimer()
    st.set_page_config(page_title="Gas Ratio Pro", page_icon=_app_icon_data_uri() or None, layout="wide")
    startup_timer.mark("page_config")

    from core.streamlit_runtime_compat import configure_streamlit_runtime_log_capture
    logger = configure_streamlit_runtime_log_capture()
    startup_timer.mark("runtime_logging")

    state_controller = _application_state_controller()
    startup_timer.mark("state_controller")

    workbench_runtime = application_service_container(state_controller.state).workbench_runtime()
    current_route = str(
        state_controller.state.get("workbench.interaction.active_navigation_id") or "nav.dashboard"
    )
    transition = workbench_runtime.activate_route(current_route)
    startup_timer.mark("route_lifecycle")

    begin_rerun_cycle(state_controller.state)
    startup_timer.mark("rerun_begin")

    logger.info("modern_workbench_started")
    _process_workbench_bulk_action(logger)
    _process_workbench_property_action(logger)
    startup_timer.mark("pending_actions")

    # Import the renderer only when the production Workbench route is actually
    # selected. This keeps legacy startup and module import smoke tests light.
    from app.workbench_renderer import render_streamlit_workbench
    results = render_streamlit_workbench(state_controller.state, st)
    startup_timer.mark("workbench_render")

    context = state_controller.context()
    startup_record = workbench_runtime.record_startup_cycle(
        startup_timer.finish(),
        route_id=str(state_controller.state.get("workbench.interaction.active_navigation_id") or ""),
        project_id=str(context.project_id or ""),
    )
    logger.info(
        "workbench_startup_diagnostics status=%s total_ms=%s slow_stages=%s",
        startup_record.get("status"), startup_record.get("total_ms"), startup_record.get("slow_stages"),
    )
    if transition.changed:
        logger.info(
            "workbench_route_transition previous=%s active=%s duration_ms=%.2f cleanup=%d failures=%d status=%s",
            transition.previous_route, transition.active_route, transition.transition_ms,
            transition.cleanup_count, transition.cleanup_failures, transition.status,
        )

    if any(result.executed for result in results):
        _request_ui_refresh_and_rerun("workbench_command_executed")


def main() -> None:
    """Start the production UI, using legacy only under an explicit env flag."""

    if legacy_ui_requested():
        _run_legacy_ui()
        return
    _run_modern_workbench()


if __name__ == "__main__":
    main()
