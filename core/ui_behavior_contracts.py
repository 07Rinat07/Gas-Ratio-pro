"""Renderer-neutral UI behavior contracts used by production code and tests.

These contracts describe observable behavior rather than implementation text.
They intentionally avoid Streamlit imports so acceptance tests can verify the
same promises across web, desktop, and future shells.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True, slots=True)
class DocumentationCenterBehavior:
    title: str = "Gas Ratio Pro Documentation Center"
    required_quick_links: tuple[str, ...] = ("Быстрый старт", "Диагностика")
    required_anchors: tuple[str, ...] = ("docs-shortcuts", "docs-faq")
    logo_overlay_enabled: bool = False

    def validate(self, quick_links: Iterable[str], anchors: Iterable[str]) -> bool:
        link_set = set(quick_links)
        anchor_set = set(anchors)
        return set(self.required_quick_links) <= link_set and set(self.required_anchors) <= anchor_set


@dataclass(frozen=True, slots=True)
class ProfessionalExportBehavior:
    panel_label: str = "🖨 Печать и экспорт"
    panel_help: str = "Открыть компактный центр печати и экспорта"
    expanded_default: bool = False
    primary_action_label: str = "🖨️  СФОРМИРОВАТЬ ОТЧЁТ"
    busy_action_label: str = "⏳  ОТЧЁТ ФОРМИРУЕТСЯ — ПОВТОРНО НЕ НАЖИМАТЬ"
    download_prefix: str = "⬇️ СКАЧАТЬ ГОТОВЫЙ"
    fragment_run_every: str = "2s"
    progress_mode: str = "inline"
    isolated_fragment: bool = True
    render_before_plots: bool = True
    heavy_plot_rendering_inside_panel: bool = False
    scopes: tuple[str, ...] = (
        "Вся скважина и все УВ-интервалы",
        "Текущий интервал графиков",
        "Выбрать отдельно",
    )
    selected_interval_scope: str = "Выбранный пласт"
    report_formats: tuple[str, ...] = ("pdf", "docx", "bundle")

    def scope_options(self, *, selected_interval_available: bool) -> tuple[str, ...]:
        options = list(self.scopes)
        if selected_interval_available:
            options.insert(0, self.selected_interval_scope)
        return tuple(options)




@dataclass(frozen=True, slots=True)
class PdfPreviewBehavior:
    expander_label: str = "Предпросмотр страниц PDF"
    create_action_label: str = "Создать предпросмотр"
    prefetch_label: str = "Предзагрузить следующую группу страниц"
    clear_cache_label: str = "Очистить кэш предпросмотра"
    previous_label: str = "← Предыдущие"
    next_label: str = "Следующие →"
    dpi_options: tuple[int, ...] = (72, 90, 110, 144, 180)
    layout_options: tuple[str, ...] = ("Одна колонка", "Две колонки")
    memory_budget_mib: tuple[int, ...] = (8, 16, 24, 48)
    prefetch_is_opt_in: bool = True
    heavy_payload_in_session_state: bool = False

@dataclass(frozen=True, slots=True)
class WorkbenchSearchBehavior:
    entity_kinds: tuple[str, ...] = (
        "projects",
        "wells",
        "las",
        "curves",
        "calculations",
        "reports",
        "documentation",
        "history",
        "favorites",
    )
    favorites_backend: str = "command_palette"
    empty_hint: str = "Закрепите команды и объекты через Ctrl+K"


@dataclass(frozen=True, slots=True)
class WorkbenchNavigationBehavior:
    required_routes: tuple[str, ...] = (
        "nav.dashboard",
        "nav.data",
        "nav.las_workspace",
        "nav.correlation",
        "nav.interpretation",
        "nav.reports",
        "nav.exports",
        "nav.documentation",
    )
    native_button_prefixes: tuple[str, ...] = ("workbench_menu_", "workbench_tree_")


@dataclass(frozen=True, slots=True)
class LauncherBehavior:
    guards_stale_port: bool = True
    force_restart_supported: bool = True
    prints_project_source: bool = True
    clears_legacy_ui_flag: bool = True


DOCUMENTATION_CENTER_BEHAVIOR = DocumentationCenterBehavior()
PROFESSIONAL_EXPORT_BEHAVIOR = ProfessionalExportBehavior()
PDF_PREVIEW_BEHAVIOR = PdfPreviewBehavior()
WORKBENCH_SEARCH_BEHAVIOR = WorkbenchSearchBehavior()
WORKBENCH_NAVIGATION_BEHAVIOR = WorkbenchNavigationBehavior()
LAUNCHER_BEHAVIOR = LauncherBehavior()


__all__ = [
    "DOCUMENTATION_CENTER_BEHAVIOR",
    "LAUNCHER_BEHAVIOR",
    "PROFESSIONAL_EXPORT_BEHAVIOR",
    "PDF_PREVIEW_BEHAVIOR",
    "WORKBENCH_NAVIGATION_BEHAVIOR",
    "WORKBENCH_SEARCH_BEHAVIOR",
    "DocumentationCenterBehavior",
    "LauncherBehavior",
    "ProfessionalExportBehavior",
    "PdfPreviewBehavior",
    "WorkbenchNavigationBehavior",
    "WorkbenchSearchBehavior",
]
