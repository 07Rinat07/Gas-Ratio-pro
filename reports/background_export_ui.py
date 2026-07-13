from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from reports.background_export import ExportJobSnapshot, ExportJobStatus


@dataclass(frozen=True, slots=True)
class BackgroundExportResult:
    """Process-local result handed from a worker to the Streamlit UI thread."""

    artifact: Any
    metrics: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class BackgroundExportStatusView:
    level: str
    title: str
    detail: str
    progress: int
    cancellable: bool
    downloadable: bool
    retryable: bool


def build_background_export_status_view(
    snapshot: ExportJobSnapshot,
    *,
    artifact_available: bool | None = None,
) -> BackgroundExportStatusView:
    status = snapshot.status
    progress = max(0, min(100, snapshot.progress))
    if status is ExportJobStatus.COMPLETED:
        available = True if artifact_available is None else bool(artifact_available)
        if not available:
            return BackgroundExportStatusView(
                level="warning",
                title="Готовый файл больше недоступен",
                detail=(
                    "Метаданные завершённого экспорта восстановлены, но бинарный файл "
                    "не хранится после перезапуска приложения. Запустите экспорт повторно."
                ),
                progress=100,
                cancellable=False,
                downloadable=False,
                retryable=True,
            )
        return BackgroundExportStatusView(
            level="success",
            title="Экспорт завершён",
            detail=snapshot.message,
            progress=100,
            cancellable=False,
            downloadable=True,
            retryable=False,
        )
    if status is ExportJobStatus.FAILED:
        return BackgroundExportStatusView(
            level="error",
            title="Ошибка фонового экспорта",
            detail=snapshot.error or snapshot.message,
            progress=progress,
            cancellable=False,
            downloadable=False,
            retryable=True,
        )
    if status is ExportJobStatus.CANCELLED:
        return BackgroundExportStatusView(
            level="warning",
            title="Экспорт отменён",
            detail=snapshot.message,
            progress=progress,
            cancellable=False,
            downloadable=False,
            retryable=True,
        )
    if status is ExportJobStatus.ORPHANED:
        return BackgroundExportStatusView(
            level="warning",
            title="Экспорт прерван",
            detail=snapshot.message,
            progress=progress,
            cancellable=False,
            downloadable=False,
            retryable=True,
        )
    return BackgroundExportStatusView(
        level="info",
        title="Фоновый экспорт выполняется",
        detail=snapshot.message,
        progress=min(99, progress),
        cancellable=True,
        downloadable=False,
        retryable=False,
    )


def latest_relevant_job(
    snapshots: tuple[ExportJobSnapshot, ...],
    *,
    request_signature: str | None = None,
) -> ExportJobSnapshot | None:
    """Prefer the active matching request, then the newest matching terminal job."""
    matching = tuple(
        item for item in snapshots
        if not request_signature or item.request_signature == request_signature
    )
    for snapshot in matching:
        if not snapshot.terminal:
            return snapshot
    return matching[0] if matching else None
