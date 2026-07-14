"""Scheduled read-only repository health checks and recovery readiness reports."""
from __future__ import annotations

from dataclasses import dataclass
from time import time
from typing import Any

from core.repository_health import RepositoryHealthService, RepositoryHealthSnapshot


@dataclass(frozen=True, slots=True)
class RepositoryRecoveryReadiness:
    score: int
    status: str
    blocking_issues: int
    warning_issues: int
    repairable_issues: int
    scan_truncated: bool
    last_scan_at: float
    next_scan_at: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "status": self.status,
            "blocking_issues": self.blocking_issues,
            "warning_issues": self.warning_issues,
            "repairable_issues": self.repairable_issues,
            "scan_truncated": self.scan_truncated,
            "last_scan_at": self.last_scan_at,
            "next_scan_at": self.next_scan_at,
        }


class RepositoryHealthScheduler:
    """Runs bounded health scans only when due; never applies repairs automatically."""

    def __init__(
        self,
        service: RepositoryHealthService,
        *,
        interval_seconds: float = 300.0,
    ) -> None:
        self.service = service
        self.interval_seconds = max(30.0, float(interval_seconds))
        self._last_scan_at = 0.0
        self._last_snapshot: RepositoryHealthSnapshot | None = None
        self._scan_count = 0
        self._skipped_count = 0
        self._failure_count = 0
        self._last_error = ""

    def due(self, *, now: float | None = None) -> bool:
        current = time() if now is None else float(now)
        return self._last_snapshot is None or current >= self._last_scan_at + self.interval_seconds

    def tick(self, *, force: bool = False, now: float | None = None) -> RepositoryHealthSnapshot:
        current = time() if now is None else float(now)
        if not force and not self.due(now=current) and self._last_snapshot is not None:
            self._skipped_count += 1
            return self._last_snapshot
        try:
            snapshot = self.service.scan(force=True)
        except Exception as exc:
            self._failure_count += 1
            self._last_error = f"{type(exc).__name__}: {exc}"
            if self._last_snapshot is not None:
                return self._last_snapshot
            raise
        self._last_snapshot = snapshot
        self._last_scan_at = current
        self._scan_count += 1
        self._last_error = ""
        return snapshot

    def readiness(self, snapshot: RepositoryHealthSnapshot | None = None) -> RepositoryRecoveryReadiness:
        current = snapshot or self._last_snapshot or self.tick()
        errors = sum(1 for item in current.issues if item.severity == "error")
        warnings = sum(1 for item in current.issues if item.severity == "warning")
        repairable = sum(1 for item in current.issues if item.repairable)
        score = 100 - min(70, errors * 25) - min(25, warnings * 5)
        if current.truncated:
            score -= 10
        score = max(0, min(100, score))
        status = "ready" if score >= 90 else "attention" if score >= 60 else "blocked"
        return RepositoryRecoveryReadiness(
            score=score,
            status=status,
            blocking_issues=errors,
            warning_issues=warnings,
            repairable_issues=repairable,
            scan_truncated=current.truncated,
            last_scan_at=self._last_scan_at,
            next_scan_at=self._last_scan_at + self.interval_seconds,
        )

    def snapshot(self, *, now: float | None = None) -> dict[str, Any]:
        health = self.tick(now=now)
        return {
            "enabled": True,
            "interval_seconds": self.interval_seconds,
            "due": self.due(now=now),
            "scan_count": self._scan_count,
            "skipped_count": self._skipped_count,
            "failure_count": self._failure_count,
            "last_error": self._last_error,
            "health": health.to_dict(),
            "readiness": self.readiness(health).to_dict(),
        }

    def close(self) -> None:
        self._last_snapshot = None
        self.service.close()
