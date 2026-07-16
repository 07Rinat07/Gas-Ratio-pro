"""Bounded background import jobs and project-scoped import history."""
from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import json
from pathlib import Path
from threading import RLock
from typing import Callable, Iterable
from uuid import uuid4

from .import_wizard import BatchImportResult

_TERMINAL = {"completed", "failed", "cancelled"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True, slots=True)
class ImportJobSnapshot:
    job_id: str
    project_id: str
    source_paths: tuple[str, ...]
    source_names: tuple[str, ...]
    actor: str = ""
    status: str = "queued"
    progress_percent: int = 0
    created_at: str = ""
    started_at: str = ""
    finished_at: str = ""
    success_count: int = 0
    failed_count: int = 0
    error_code: str = ""
    message: str = ""
    result: dict[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["source_paths"] = list(self.source_paths)
        payload["source_names"] = list(self.source_names)
        return payload


class ImportHistoryRepository:
    """Append-only project-scoped JSONL history for terminal import jobs."""

    def __init__(self, projects_root: Path | str) -> None:
        self._root = Path(projects_root)
        self._lock = RLock()

    def _path(self, project_id: str) -> Path:
        if not project_id or any(part in project_id for part in ("/", "\\", "..")):
            raise ValueError("invalid project_id")
        return self._root / project_id / "imports" / "history.jsonl"

    def append(self, snapshot: ImportJobSnapshot) -> None:
        path = self._path(snapshot.project_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(snapshot.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        with self._lock, path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def list(self, project_id: str, *, limit: int = 100) -> tuple[dict[str, object], ...]:
        path = self._path(project_id)
        if not path.exists():
            return ()
        items: list[dict[str, object]] = []
        with self._lock, path.open("r", encoding="utf-8") as handle:
            for raw in handle:
                try:
                    payload = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if isinstance(payload, dict):
                    items.append(payload)
        return tuple(reversed(items[-max(1, int(limit)) :]))


class ImportJobManager:
    """Small session-local executor with JSON-safe snapshots and durable history."""

    def __init__(
        self,
        projects_root: Path | str,
        runner: Callable[..., BatchImportResult],
        *,
        max_workers: int = 1,
        max_jobs: int = 64,
    ) -> None:
        self._runner = runner
        self._executor = ThreadPoolExecutor(max_workers=max(1, int(max_workers)), thread_name_prefix="gas-import")
        self._history = ImportHistoryRepository(projects_root)
        self._max_jobs = max(4, int(max_jobs))
        self._jobs: dict[str, ImportJobSnapshot] = {}
        self._futures: dict[str, Future[BatchImportResult]] = {}
        self._lock = RLock()

    def submit(self, *, project_id: str, sources: Iterable[Path | str], actor: str = "") -> ImportJobSnapshot:
        paths = tuple(str(Path(item).resolve()) for item in sources)
        if not paths:
            raise ValueError("at least one source is required")
        job_id = f"import-{uuid4().hex[:12]}"
        snapshot = ImportJobSnapshot(
            job_id=job_id,
            project_id=project_id,
            source_paths=paths,
            source_names=tuple(Path(item).name for item in paths),
            actor=actor,
            created_at=_utc_now(),
        )
        with self._lock:
            self._jobs[job_id] = snapshot
            self._trim_locked()
            future = self._executor.submit(self._execute, job_id)
            self._futures[job_id] = future
        return snapshot

    def _execute(self, job_id: str) -> BatchImportResult:
        with self._lock:
            current = self._jobs[job_id]
            self._jobs[job_id] = replace(current, status="running", progress_percent=10, started_at=_utc_now())
            current = self._jobs[job_id]
        try:
            result = self._runner(project_id=current.project_id, sources=current.source_paths, actor=current.actor)
            terminal = replace(
                current,
                status="completed",
                progress_percent=100,
                finished_at=_utc_now(),
                success_count=result.success_count,
                failed_count=result.failed_count,
                result=result.to_dict(),
            )
        except Exception as exc:  # job boundary must never leak executor failures
            terminal = replace(
                current,
                status="failed",
                progress_percent=100,
                finished_at=_utc_now(),
                error_code=type(exc).__name__,
                message=str(exc),
            )
        with self._lock:
            self._jobs[job_id] = terminal
        self._history.append(terminal)
        return result if terminal.status == "completed" else BatchImportResult(())

    def get(self, job_id: str) -> ImportJobSnapshot:
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(job_id)
            return self._jobs[job_id]

    def list(self, *, project_id: str = "") -> tuple[ImportJobSnapshot, ...]:
        with self._lock:
            values = list(self._jobs.values())
        if project_id:
            values = [item for item in values if item.project_id == project_id]
        return tuple(reversed(values))

    def history(self, project_id: str, *, limit: int = 100) -> tuple[dict[str, object], ...]:
        return self._history.list(project_id, limit=limit)

    def retry_failed(self, job_id: str, *, actor: str = "") -> ImportJobSnapshot:
        snapshot = self.get(job_id)
        result = snapshot.result or {}
        failed_names = {
            str(item.get("source_name", ""))
            for item in (result.get("items", []) if isinstance(result, dict) else [])
            if isinstance(item, dict) and item.get("status") == "failed"
        }
        paths = [path for path in snapshot.source_paths if Path(path).name in failed_names]
        if not paths:
            raise ValueError("job has no failed items to retry")
        return self.submit(project_id=snapshot.project_id, sources=paths, actor=actor or snapshot.actor)

    def _trim_locked(self) -> None:
        if len(self._jobs) <= self._max_jobs:
            return
        for job_id, item in list(self._jobs.items()):
            if item.status in _TERMINAL:
                self._jobs.pop(job_id, None)
                self._futures.pop(job_id, None)
                if len(self._jobs) <= self._max_jobs:
                    break
