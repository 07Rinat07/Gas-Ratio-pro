"""Bounded background import jobs and project-scoped import history."""
from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta, timezone
import csv
import io
import json
import os
from pathlib import Path
from threading import RLock
from typing import Callable, Iterable
import inspect
from uuid import uuid4

from .import_wizard import BatchImportResult

_TERMINAL = {"completed", "failed", "cancelled", "interrupted"}
_ACTIVE = {"queued", "running", "cancel_requested"}


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

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "ImportJobSnapshot":
        return cls(
            job_id=str(payload.get("job_id", "")),
            project_id=str(payload.get("project_id", "")),
            source_paths=tuple(str(v) for v in payload.get("source_paths", []) or []),
            source_names=tuple(str(v) for v in payload.get("source_names", []) or []),
            actor=str(payload.get("actor", "")),
            status=str(payload.get("status", "queued")),
            progress_percent=int(payload.get("progress_percent", 0) or 0),
            created_at=str(payload.get("created_at", "")),
            started_at=str(payload.get("started_at", "")),
            finished_at=str(payload.get("finished_at", "")),
            success_count=int(payload.get("success_count", 0) or 0),
            failed_count=int(payload.get("failed_count", 0) or 0),
            error_code=str(payload.get("error_code", "")),
            message=str(payload.get("message", "")),
            result=payload.get("result") if isinstance(payload.get("result"), dict) else None,
        )


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

    def list(
        self,
        project_id: str,
        *,
        limit: int = 100,
        statuses: set[str] | None = None,
        query: str = "",
    ) -> tuple[dict[str, object], ...]:
        path = self._path(project_id)
        if not path.exists():
            return ()
        items: list[dict[str, object]] = []
        query_normalized = query.strip().casefold()
        with self._lock, path.open("r", encoding="utf-8") as handle:
            for raw in handle:
                try:
                    payload = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if not isinstance(payload, dict):
                    continue
                if statuses and str(payload.get("status", "")) not in statuses:
                    continue
                if query_normalized:
                    searchable = " ".join(
                        [
                            str(payload.get("job_id", "")),
                            str(payload.get("actor", "")),
                            " ".join(str(v) for v in payload.get("source_names", []) or []),
                        ]
                    ).casefold()
                    if query_normalized not in searchable:
                        continue
                items.append(payload)
        return tuple(reversed(items[-max(1, int(limit)) :]))

    def export(self, project_id: str, *, format_id: str = "json", statuses: set[str] | None = None, query: str = "") -> bytes:
        items = list(reversed(self.list(project_id, limit=100_000, statuses=statuses, query=query)))
        normalized = format_id.strip().lower()
        if normalized == "json":
            return json.dumps(items, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
        if normalized != "csv":
            raise ValueError("history export format must be json or csv")
        stream = io.StringIO(newline="")
        fields = ["job_id", "status", "actor", "created_at", "started_at", "finished_at", "success_count", "failed_count", "source_names", "error_code", "message"]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for item in items:
            row = {key: item.get(key, "") for key in fields}
            row["source_names"] = ";".join(str(v) for v in item.get("source_names", []) or [])
            writer.writerow(row)
        return stream.getvalue().encode("utf-8-sig")

    def prune(self, project_id: str, *, retention_days: int = 90, keep_latest: int = 100) -> dict[str, int]:
        """Rewrite history while retaining recent entries and a minimum tail."""
        path = self._path(project_id)
        if not path.exists():
            return {"removed_entries": 0, "retained_entries": 0}
        cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, int(retention_days)))
        rows: list[dict[str, object]] = []
        with self._lock, path.open("r", encoding="utf-8") as handle:
            for raw in handle:
                try:
                    payload = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if isinstance(payload, dict):
                    rows.append(payload)
        keep_tail = max(0, int(keep_latest))
        retained: list[dict[str, object]] = []
        for index, payload in enumerate(rows):
            if index >= max(0, len(rows) - keep_tail):
                retained.append(payload)
                continue
            stamp = str(payload.get("finished_at") or payload.get("created_at") or "")
            try:
                when = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
            except ValueError:
                retained.append(payload)
                continue
            if when >= cutoff:
                retained.append(payload)
        temp = path.with_suffix(path.suffix + ".tmp")
        with self._lock, temp.open("w", encoding="utf-8") as handle:
            for payload in retained:
                handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
        os.replace(temp, path)
        return {"removed_entries": len(rows) - len(retained), "retained_entries": len(retained)}


class ImportJobManager:
    """Small executor with durable compact snapshots and project-scoped history."""

    def __init__(
        self,
        projects_root: Path | str,
        runner: Callable[..., BatchImportResult],
        *,
        max_workers: int = 1,
        max_jobs: int = 64,
    ) -> None:
        self._root = Path(projects_root)
        self._runner = runner
        self._executor = ThreadPoolExecutor(max_workers=max(1, int(max_workers)), thread_name_prefix="gas-import")
        self._history = ImportHistoryRepository(self._root)
        self._max_jobs = max(4, int(max_jobs))
        self._jobs: dict[str, ImportJobSnapshot] = {}
        self._futures: dict[str, Future[BatchImportResult]] = {}
        self._lock = RLock()
        self._recover_interrupted_jobs()

    def _jobs_path(self, project_id: str) -> Path:
        if not project_id or any(part in project_id for part in ("/", "\\", "..")):
            raise ValueError("invalid project_id")
        return self._root / project_id / "imports" / "jobs.json"

    def _persist_project_locked(self, project_id: str) -> None:
        path = self._jobs_path(project_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = [item.to_dict() for item in self._jobs.values() if item.project_id == project_id]
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(temp, path)

    def _recover_interrupted_jobs(self) -> None:
        if not self._root.exists():
            return
        for path in self._root.glob("*/imports/jobs.json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(payload, list):
                continue
            project_id = path.parent.parent.name
            changed = False
            for raw in payload:
                if not isinstance(raw, dict):
                    continue
                snapshot = ImportJobSnapshot.from_dict(raw)
                if not snapshot.job_id or snapshot.project_id != project_id:
                    continue
                if snapshot.status in _ACTIVE:
                    snapshot = replace(
                        snapshot,
                        status="interrupted",
                        progress_percent=100,
                        finished_at=_utc_now(),
                        error_code="ImportJobInterrupted",
                        message="Application restarted before the import job completed.",
                    )
                    self._history.append(snapshot)
                    changed = True
                self._jobs[snapshot.job_id] = snapshot
            if changed:
                with self._lock:
                    self._persist_project_locked(project_id)

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
            self._persist_project_locked(project_id)
            future = self._executor.submit(self._execute, job_id)
            self._futures[job_id] = future
        return snapshot

    def _execute(self, job_id: str) -> BatchImportResult:
        with self._lock:
            current = self._jobs[job_id]
            if current.status == "cancelled":
                return BatchImportResult(())
            self._jobs[job_id] = replace(current, status="running", progress_percent=10, started_at=_utc_now())
            current = self._jobs[job_id]
            self._persist_project_locked(current.project_id)
        try:
            def should_cancel() -> bool:
                with self._lock:
                    return self._jobs[job_id].status == "cancel_requested"

            def progress(completed: int, total: int) -> None:
                percent = 10 if total <= 0 else min(95, 10 + int((completed / total) * 85))
                with self._lock:
                    latest = self._jobs[job_id]
                    self._jobs[job_id] = replace(latest, progress_percent=percent)
                    self._persist_project_locked(latest.project_id)

            parameters = inspect.signature(self._runner).parameters
            kwargs = {"project_id": current.project_id, "sources": current.source_paths, "actor": current.actor}
            if "should_cancel" in parameters:
                kwargs["should_cancel"] = should_cancel
            if "progress_callback" in parameters:
                kwargs["progress_callback"] = progress
            result = self._runner(**kwargs)
            cancel_requested = should_cancel()
            terminal = replace(
                current,
                status="cancelled" if cancel_requested else "completed",
                progress_percent=100,
                finished_at=_utc_now(),
                success_count=0 if cancel_requested else result.success_count,
                failed_count=0 if cancel_requested else result.failed_count,
                result=None if cancel_requested else result.to_dict(),
                error_code="ImportJobCancelled" if cancel_requested else "",
                message="Cancellation requested while the job was running." if cancel_requested else "",
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
            self._persist_project_locked(terminal.project_id)
        self._history.append(terminal)
        return result if terminal.status == "completed" else BatchImportResult(())

    def cancel(self, job_id: str) -> ImportJobSnapshot:
        with self._lock:
            current = self._jobs.get(job_id)
            if current is None:
                raise KeyError(job_id)
            if current.status in _TERMINAL:
                return current
            future = self._futures.get(job_id)
            if current.status == "queued" and future is not None and future.cancel():
                updated = replace(current, status="cancelled", progress_percent=100, finished_at=_utc_now(), error_code="ImportJobCancelled")
                self._jobs[job_id] = updated
                self._persist_project_locked(updated.project_id)
                self._history.append(updated)
                return updated
            updated = replace(current, status="cancel_requested", message="Cancellation requested.")
            self._jobs[job_id] = updated
            self._persist_project_locked(updated.project_id)
            return updated

    def get(self, job_id: str) -> ImportJobSnapshot:
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(job_id)
            return self._jobs[job_id]

    def list(self, *, project_id: str = "", statuses: set[str] | None = None) -> tuple[ImportJobSnapshot, ...]:
        with self._lock:
            values = list(self._jobs.values())
        if project_id:
            values = [item for item in values if item.project_id == project_id]
        if statuses:
            values = [item for item in values if item.status in statuses]
        return tuple(reversed(values))

    def history(self, project_id: str, *, limit: int = 100, statuses: set[str] | None = None, query: str = "") -> tuple[dict[str, object], ...]:
        return self._history.list(project_id, limit=limit, statuses=statuses, query=query)

    def export_history(self, project_id: str, *, format_id: str = "json", statuses: set[str] | None = None, query: str = "") -> bytes:
        return self._history.export(project_id, format_id=format_id, statuses=statuses, query=query)

    def retry_failed(self, job_id: str, *, actor: str = "") -> ImportJobSnapshot:
        snapshot = self.get(job_id)
        result = snapshot.result or {}
        failed_names = {
            str(item.get("source_name", ""))
            for item in (result.get("items", []) if isinstance(result, dict) else [])
            if isinstance(item, dict) and item.get("status") == "failed"
        }
        if snapshot.status == "interrupted":
            paths = [path for path in snapshot.source_paths if Path(path).exists()]
        else:
            paths = [path for path in snapshot.source_paths if Path(path).name in failed_names and Path(path).exists()]
        if not paths:
            raise ValueError("job has no available failed or interrupted items to retry")
        return self.submit(project_id=snapshot.project_id, sources=paths, actor=actor or snapshot.actor)

    def resume_interrupted(self, job_id: str, *, actor: str = "") -> ImportJobSnapshot:
        snapshot = self.get(job_id)
        if snapshot.status != "interrupted":
            raise ValueError("only interrupted jobs can be resumed")
        paths = [path for path in snapshot.source_paths if Path(path).exists()]
        if not paths:
            raise ValueError("interrupted job has no available source files")
        return self.submit(project_id=snapshot.project_id, sources=paths, actor=actor or snapshot.actor)

    def apply_retention_policy(
        self, project_id: str, *, retention_days: int = 90, keep_latest: int = 100, staging_max_age_days: int = 7
    ) -> dict[str, int]:
        history = self._history.prune(project_id, retention_days=retention_days, keep_latest=keep_latest)
        staging = self._root / project_id / "imports" / "staging"
        removed_files = 0
        removed_bytes = 0
        cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, int(staging_max_age_days)))
        protected = {
            Path(path).resolve()
            for item in self.list(project_id=project_id)
            if item.status in _ACTIVE
            for path in item.source_paths
        }
        if staging.exists():
            root = staging.resolve()
            for candidate in staging.iterdir():
                if not candidate.is_file():
                    continue
                resolved = candidate.resolve()
                if resolved.parent != root or resolved in protected:
                    continue
                modified = datetime.fromtimestamp(candidate.stat().st_mtime, tz=timezone.utc)
                if modified >= cutoff:
                    continue
                size = candidate.stat().st_size
                candidate.unlink()
                removed_files += 1
                removed_bytes += size
        return {**history, "removed_staging_files": removed_files, "removed_staging_bytes": removed_bytes}

    def cleanup_staging(self, project_id: str, *, include_terminal: bool = True) -> dict[str, int]:
        staging = self._root / project_id / "imports" / "staging"
        if not staging.exists():
            return {"removed_files": 0, "removed_bytes": 0}
        with self._lock:
            protected = {
                Path(path).resolve()
                for item in self._jobs.values()
                if item.project_id == project_id and (item.status in _ACTIVE or not include_terminal)
                for path in item.source_paths
            }
        removed_files = 0
        removed_bytes = 0
        root = staging.resolve()
        for candidate in staging.iterdir():
            try:
                resolved = candidate.resolve()
            except OSError:
                continue
            if resolved.parent != root or resolved in protected or not candidate.is_file():
                continue
            try:
                size = candidate.stat().st_size
                candidate.unlink()
            except OSError:
                continue
            removed_files += 1
            removed_bytes += size
        return {"removed_files": removed_files, "removed_bytes": removed_bytes}

    def _trim_locked(self) -> None:
        if len(self._jobs) <= self._max_jobs:
            return
        affected: set[str] = set()
        for job_id, item in list(self._jobs.items()):
            if item.status in _TERMINAL:
                affected.add(item.project_id)
                self._jobs.pop(job_id, None)
                self._futures.pop(job_id, None)
                if len(self._jobs) <= self._max_jobs:
                    break
        for project_id in affected:
            self._persist_project_locked(project_id)
