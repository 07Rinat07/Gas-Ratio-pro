from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from reports.background_export import ExportJobSnapshot, ExportJobStatus


@dataclass(frozen=True, slots=True)
class BackgroundExportResult:
    """Process-local result handed from a worker to the Streamlit UI thread."""

    artifact: Any
    metrics: Mapping[str, Any]
    report_document_counts: Any | None = None


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
    status: ExportJobStatus
    export_format: str
    duration_seconds: float
    artifact_size_bytes: int


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
                status=snapshot.status,
                export_format=snapshot.export_format,
                duration_seconds=max(
                    0.0,
                    snapshot.duration_seconds
                    or (snapshot.updated_at - snapshot.created_at),
                ),
                artifact_size_bytes=max(0, snapshot.artifact_size_bytes),
            )
        )
    return tuple(items)


def filter_recent_background_job_history(
    items: tuple[BackgroundExportHistoryItem, ...],
    *,
    statuses: tuple[ExportJobStatus | str, ...] = (),
    formats: tuple[str, ...] = (),
) -> tuple[BackgroundExportHistoryItem, ...]:
    """Filter already-bounded export history without mutating its order.

    Empty filters mean "all". String status values are accepted to keep the
    function convenient for Streamlit widget values and persisted UI state.
    """
    normalized_statuses = {
        value.value if isinstance(value, ExportJobStatus) else str(value).strip().lower()
        for value in statuses
        if str(value).strip()
    }
    normalized_formats = {str(value).strip().lower() for value in formats if str(value).strip()}
    return tuple(
        item for item in items
        if (not normalized_statuses or item.status.value in normalized_statuses)
        and (not normalized_formats or item.export_format.strip().lower() in normalized_formats)
    )



def sort_recent_background_job_history(
    items: tuple[BackgroundExportHistoryItem, ...],
    *,
    sort_by: str = "updated_desc",
) -> tuple[BackgroundExportHistoryItem, ...]:
    """Return a deterministically sorted copy of recent export history.

    Supported modes are ``updated_desc``/``updated_asc``,
    ``duration_desc``/``duration_asc`` and ``size_desc``/``size_asc``.
    Unknown values safely fall back to newest-first ordering. Stable
    secondary keys keep Streamlit reruns visually deterministic.
    """
    mode = str(sort_by or "updated_desc").strip().lower()
    supported = {
        "updated_desc",
        "updated_asc",
        "duration_desc",
        "duration_asc",
        "size_desc",
        "size_asc",
    }
    if mode not in supported:
        mode = "updated_desc"

    field, direction = mode.rsplit("_", 1)
    reverse = direction == "desc"

    def primary(item: BackgroundExportHistoryItem) -> float:
        if field == "duration":
            return float(item.duration_seconds)
        if field == "size":
            return float(item.artifact_size_bytes)
        return float(item.updated_at)

    # First establish deterministic newest-first tie ordering, then rely on
    # Python's stable sort for the selected primary metric.
    deterministic = sorted(items, key=lambda item: (item.updated_at, item.job_id), reverse=True)
    return tuple(sorted(deterministic, key=primary, reverse=reverse))


@dataclass(frozen=True, slots=True)
class BackgroundExportPerformanceSummary:
    total_jobs: int
    active_jobs: int
    completed_jobs: int
    failed_jobs: int
    cancelled_jobs: int
    orphaned_jobs: int
    success_rate_percent: float
    average_duration_seconds: float
    average_artifact_size_bytes: int


def build_background_export_performance_summary(
    items: tuple[BackgroundExportHistoryItem, ...],
) -> BackgroundExportPerformanceSummary:
    """Aggregate lightweight runtime metrics from visible export history.

    The function is renderer-neutral and deliberately uses only persisted
    snapshot metadata. Active jobs are excluded from success-rate, duration and
    artifact-size averages because their final values are not known yet.
    """
    total_jobs = len(items)
    completed = tuple(item for item in items if item.status is ExportJobStatus.COMPLETED)
    failed = tuple(item for item in items if item.status is ExportJobStatus.FAILED)
    cancelled = tuple(item for item in items if item.status is ExportJobStatus.CANCELLED)
    orphaned = tuple(item for item in items if item.status is ExportJobStatus.ORPHANED)
    terminal_count = len(completed) + len(failed) + len(cancelled) + len(orphaned)
    duration_samples = tuple(
        item.duration_seconds for item in items
        if item.terminal and item.duration_seconds >= 0.0
    )
    size_samples = tuple(
        item.artifact_size_bytes for item in completed
        if item.artifact_size_bytes > 0
    )
    return BackgroundExportPerformanceSummary(
        total_jobs=total_jobs,
        active_jobs=total_jobs - terminal_count,
        completed_jobs=len(completed),
        failed_jobs=len(failed),
        cancelled_jobs=len(cancelled),
        orphaned_jobs=len(orphaned),
        success_rate_percent=(100.0 * len(completed) / terminal_count) if terminal_count else 0.0,
        average_duration_seconds=(sum(duration_samples) / len(duration_samples)) if duration_samples else 0.0,
        average_artifact_size_bytes=(int(round(sum(size_samples) / len(size_samples))) if size_samples else 0),
    )


def format_export_duration(seconds: float) -> str:
    """Format a job duration for compact Russian-language history metadata."""
    total_seconds = max(0, int(round(float(seconds))))
    if total_seconds < 60:
        return f"{total_seconds} с"
    minutes, remainder = divmod(total_seconds, 60)
    if minutes < 60:
        return f"{minutes} мин {remainder:02d} с"
    hours, minutes = divmod(minutes, 60)
    return f"{hours} ч {minutes:02d} мин"


def format_artifact_size(size_bytes: int) -> str:
    """Format a non-negative artifact size using compact binary units."""
    size = max(0, int(size_bytes))
    units = ("Б", "КиБ", "МиБ", "ГиБ")
    value = float(size)
    unit = units[0]
    for candidate in units:
        unit = candidate
        if value < 1024.0 or candidate == units[-1]:
            break
        value /= 1024.0
    if unit == "Б":
        return f"{int(value)} {unit}"
    return f"{value:.1f} {unit}"
