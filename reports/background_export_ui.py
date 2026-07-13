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


@dataclass(frozen=True, slots=True)
class BackgroundExportHistoryItem:
    job_id: str
    title: str
    detail: str
    level: str
    progress: int
    retryable: bool
    retry_reason: str
    terminal: bool
    dismissible: bool
    updated_at: float


def retry_diagnostic_reason(
    snapshot: ExportJobSnapshot,
    *,
    artifact_available: bool | None = None,
) -> str:
    """Return a compact, persistence-safe reason for retrying a terminal job."""
    if snapshot.status is ExportJobStatus.FAILED:
        return snapshot.error or "Предыдущий экспорт завершился ошибкой."
    if snapshot.status is ExportJobStatus.CANCELLED:
        return "Предыдущий экспорт был отменён пользователем."
    if snapshot.status is ExportJobStatus.ORPHANED:
        return "Предыдущий экспорт был прерван перезапуском приложения."
    if snapshot.status is ExportJobStatus.COMPLETED and artifact_available is False:
        return "Файл завершённого экспорта утрачен после перезапуска приложения."
    return "Повторный запуск фонового экспорта."


def build_recent_background_job_history(
    snapshots: tuple[ExportJobSnapshot, ...],
    *,
    artifact_availability: Mapping[str, bool] | None = None,
    limit: int = 5,
) -> tuple[BackgroundExportHistoryItem, ...]:
    """Build a bounded newest-first history suitable for compact UI rendering."""
    availability = artifact_availability or {}
    bounded = snapshots[: max(0, int(limit))]
    items: list[BackgroundExportHistoryItem] = []
    for snapshot in bounded:
        available = availability.get(snapshot.id)
        view = build_background_export_status_view(snapshot, artifact_available=available)
        items.append(
            BackgroundExportHistoryItem(
                job_id=snapshot.id,
                title=view.title,
                detail=view.detail,
                level=view.level,
                progress=view.progress,
                retryable=view.retryable,
                retry_reason=snapshot.retry_reason,
                terminal=snapshot.terminal,
                dismissible=(
                    snapshot.terminal
                    and not (snapshot.status is ExportJobStatus.COMPLETED and available is True)
                ),
                updated_at=snapshot.updated_at,
            )
        )
    return tuple(items)
