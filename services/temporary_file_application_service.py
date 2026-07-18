"""Application boundary for lifecycle-managed temporary file cleanup.

UI and ordinary application services must not call ``Path.unlink`` directly.
This service validates that the target belongs to an approved temporary root
and delegates deletion to :class:`core.storage_lifecycle.DeleteEngine`.
"""

from __future__ import annotations

from pathlib import Path
from tempfile import gettempdir
from typing import Iterable

from core.storage_lifecycle import DeleteEngine, DeleteResult


class TemporaryFileApplicationService:
    """Delete temporary files through the shared storage lifecycle boundary."""

    def __init__(
        self,
        *,
        allowed_roots: Iterable[Path | str] | None = None,
        delete_engine: DeleteEngine | None = None,
    ) -> None:
        roots = tuple(allowed_roots or (Path(gettempdir()),))
        self._allowed_roots = tuple(Path(root).resolve() for root in roots)
        if not self._allowed_roots:
            raise ValueError("At least one temporary root is required.")
        self._delete_engine = delete_engine or DeleteEngine(attempts=2, delay_seconds=0.0)

    def delete(self, path: Path | str, *, missing_ok: bool = True) -> DeleteResult:
        """Delete one file only when it is inside an approved temporary root."""
        target = Path(path).resolve()
        if not any(target == root or root in target.parents for root in self._allowed_roots):
            raise ValueError(f"Temporary path is outside approved roots: {target}")
        return self._delete_engine.delete_path(target, missing_ok=missing_ok)

    def health_snapshot(self) -> dict[str, object]:
        return {
            "status": "ready",
            "allowed_roots": [str(root) for root in self._allowed_roots],
        }
