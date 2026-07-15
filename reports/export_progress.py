from __future__ import annotations

"""Stable four-stage progress contract for professional background exports."""

from dataclasses import dataclass
from typing import Callable


ProgressReporter = Callable[[int, str], None]


@dataclass(frozen=True, slots=True)
class ExportProgressStage:
    number: int
    total: int
    label: str
    minimum: int
    maximum: int

    @property
    def prefix(self) -> str:
        return f"Шаг {self.number} из {self.total} — {self.label}"


EXPORT_PROGRESS_STAGES: tuple[ExportProgressStage, ...] = (
    ExportProgressStage(1, 4, "Проверка параметров", 0, 9),
    ExportProgressStage(2, 4, "Подготовка данных", 10, 39),
    ExportProgressStage(3, 4, "Формирование документа", 40, 89),
    ExportProgressStage(4, 4, "Финализация файла", 90, 100),
)


def export_progress_stage(progress: int) -> ExportProgressStage:
    """Return the public stage corresponding to a normalized progress value."""
    normalized = max(0, min(100, int(progress)))
    for stage in EXPORT_PROGRESS_STAGES:
        if stage.minimum <= normalized <= stage.maximum:
            return stage
    return EXPORT_PROGRESS_STAGES[-1]


def format_export_progress_message(progress: int, detail: str = "") -> str:
    """Add a stable four-stage prefix without discarding the detailed renderer status."""
    stage = export_progress_stage(progress)
    normalized_detail = str(detail).strip()
    return f"{stage.prefix}: {normalized_detail}" if normalized_detail else stage.prefix


def staged_progress_reporter(report: ProgressReporter) -> ProgressReporter:
    """Decorate a worker reporter with the stable user-facing stage contract."""
    if not callable(report):
        raise TypeError("report must be callable")

    def _report(progress: int, message: str) -> None:
        normalized = max(0, min(100, int(progress)))
        report(normalized, format_export_progress_message(normalized, message))

    return _report
