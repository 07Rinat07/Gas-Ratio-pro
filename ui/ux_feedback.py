"""Unified tooltip and long-running operation feedback contracts.

The module is framework-neutral so UI tests can validate labels, help text and
progress sequencing without importing Streamlit.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class TooltipDefinition:
    key: str
    text: str


_TOOLTIPS: dict[str, TooltipDefinition] = {
    "report.profile": TooltipDefinition(
        "report.profile",
        "Отчёт для заказчика содержит краткие выводы; инженерный профиль включает расширенные расчётные материалы.",
    ),
    "report.format": TooltipDefinition(
        "report.format",
        "PDF — печать; DOCX — редактирование; PNG/SVG — планшет; XLSX — инженерные таблицы.",
    ),
    "report.template": TooltipDefinition(
        "report.template",
        "Engineering — полный технический отчёт; Corporate — компактная передача заказчику; Minimal — краткое заключение.",
    ),
    "report.sections": TooltipDefinition(
        "report.sections",
        "Выбранные разделы формируют единый состав PDF и DOCX и участвуют в проверке готовности экспорта.",
    ),
    "report.technical_appendix": TooltipDefinition(
        "report.technical_appendix",
        "Добавляет расширенные расчётные таблицы и технические сведения для внутренней инженерной проверки.",
    ),
    "report.page_chrome": TooltipDefinition(
        "report.page_chrome",
        "Добавляет код документа, классификацию, верхний и нижний колонтитулы и номера страниц.",
    ),
    "report.print_scope": TooltipDefinition(
        "report.print_scope",
        "Определяет диапазон глубины и набор интервальных страниц, включаемых в экспорт.",
    ),
    "report.prepare": TooltipDefinition(
        "report.prepare",
        "Проверяет параметры, строит модель отчёта и создаёт файл выбранного формата.",
    ),
}


def tooltip(key: str, *, fallback: str | None = None) -> str:
    """Return normalized help text for a UI control.

    Unknown keys require an explicit fallback so missing registry entries do not
    silently produce empty help bubbles.
    """

    item = _TOOLTIPS.get(str(key).strip())
    if item is not None:
        return item.text
    if fallback is not None and str(fallback).strip():
        return str(fallback).strip()
    raise KeyError(f"Unknown tooltip key: {key!r}")


def tooltip_keys() -> tuple[str, ...]:
    return tuple(sorted(_TOOLTIPS))


@dataclass(frozen=True)
class OperationStage:
    id: str
    percent: int
    message: str

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("Operation stage id cannot be empty")
        if not 0 <= int(self.percent) <= 100:
            raise ValueError("Operation stage percent must be between 0 and 100")
        if not self.message.strip():
            raise ValueError("Operation stage message cannot be empty")


@dataclass(frozen=True)
class OperationProgressPlan:
    id: str
    stages: tuple[OperationStage, ...]

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("Operation plan id cannot be empty")
        if not self.stages:
            raise ValueError("Operation plan must contain at least one stage")
        values = [stage.percent for stage in self.stages]
        if values != sorted(values) or len(values) != len(set(values)):
            raise ValueError("Operation stage percentages must be unique and increasing")
        if self.stages[-1].percent != 100:
            raise ValueError("Operation plan must finish at 100 percent")

    def stage(self, stage_id: str) -> OperationStage:
        normalized = str(stage_id).strip()
        for stage in self.stages:
            if stage.id == normalized:
                return stage
        raise KeyError(f"Unknown operation stage: {stage_id!r}")


REPORT_EXPORT_PROGRESS = OperationProgressPlan(
    id="report_export",
    stages=(
        OperationStage("validate", 5, "Проверка настроек экспорта…"),
        OperationStage("model", 30, "Формируется модель отчёта и атлас интервалов…"),
        OperationStage("render", 70, "Создаётся файл выбранного формата…"),
        OperationStage("finalize", 95, "Проверяется готовый файл…"),
        OperationStage("complete", 100, "Файл готов к скачиванию."),
    ),
)


def validate_tooltip_coverage(keys: Iterable[str]) -> tuple[str, ...]:
    """Return missing keys for preflight/audit tooling."""

    return tuple(sorted({str(key).strip() for key in keys if str(key).strip()} - set(_TOOLTIPS)))
