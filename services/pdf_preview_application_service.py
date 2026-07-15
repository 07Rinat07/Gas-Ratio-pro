"""Project-scoped application boundary for heavy PDF preview runtime state."""

from __future__ import annotations

from pathlib import Path
from core.cache_metrics import CacheMetricsRegistry
from projects.repository import DEFAULT_PROJECTS_ROOT, safe_project_id
from reports.pdf_preview import (
    PdfPreviewCacheLookup,
    PdfPreviewCacheStats,
    PdfPreviewCacheStoreResult,
    PdfPreviewResult,
    PdfPreviewRuntimeCache,
    PdfPreviewRuntimeCacheSnapshot,
)


class PdfPreviewApplicationService:
    """Own one project's bounded PDF preview cache and its telemetry."""

    def __init__(
        self,
        *,
        project_id: str,
        root: Path | str = DEFAULT_PROJECTS_ROOT,
        metrics_registry: CacheMetricsRegistry | None = None,
        max_entries: int = 3,
        max_bytes: int = 24 * 1024 * 1024,
    ) -> None:
        self.project_id = safe_project_id(project_id)
        self.root = Path(root).resolve()
        metrics = (
            metrics_registry.counter("pdf_preview_runtime", max_entries=max_entries)
            if metrics_registry is not None
            else None
        )
        self._cache = PdfPreviewRuntimeCache(
            max_entries=max_entries,
            max_bytes=max_bytes,
            metrics=metrics,
        )

    def migrate_legacy_entries(self, payload: object) -> int:
        """Import valid legacy Session State entries and ignore malformed data."""
        if not isinstance(payload, dict):
            return 0
        entries = payload.get("entries")
        if not isinstance(entries, (list, tuple)):
            entries = (payload,)
        migrated = 0
        for entry in reversed(tuple(entries)):
            if not isinstance(entry, dict):
                continue
            signature = entry.get("signature")
            result = entry.get("result")
            if isinstance(signature, str) and isinstance(result, PdfPreviewResult):
                self._cache.store(signature, result)
                migrated += 1
        return migrated

    def configure(self, *, max_entries: int | None = None, max_bytes: int | None = None) -> None:
        self._cache.configure(max_entries=max_entries, max_bytes=max_bytes)

    def inspect(self, signature: str) -> PdfPreviewCacheLookup:
        return self._cache.inspect(signature)

    def store(self, signature: str, result: PdfPreviewResult) -> PdfPreviewCacheStoreResult:
        return self._cache.store(signature, result)

    def clear(self) -> int:
        return self._cache.clear()

    def known_total_pages(self) -> int:
        return self._cache.known_total_pages()

    def stats(self, *, warning_threshold_bytes: int | None = None, critical_threshold_bytes: int | None = None) -> PdfPreviewCacheStats:
        return self._cache.stats(
            warning_threshold_bytes=warning_threshold_bytes,
            critical_threshold_bytes=critical_threshold_bytes,
        )

    def snapshot(self) -> PdfPreviewRuntimeCacheSnapshot:
        return self._cache.snapshot()

    def health_snapshot(self) -> dict[str, object]:
        snapshot = self.snapshot()
        return {
            "service": type(self).__name__,
            "project_id": self.project_id,
            "root": str(self.root),
            "status": "ok",
            "cache": snapshot.to_dict(),
        }

    def close(self) -> None:
        self._cache.close()
