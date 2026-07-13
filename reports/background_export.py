from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, replace
from enum import Enum
from threading import Event, RLock
from time import time
from typing import Any, Callable, MutableMapping
from uuid import uuid4


class ExportJobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"
    ORPHANED = "orphaned"


@dataclass(frozen=True, slots=True)
class ExportJobSnapshot:
    id: str
    project_id: str
    request_signature: str
    status: ExportJobStatus
    progress: int
    message: str
    created_at: float
    updated_at: float
    result_key: str = ""
    error: str = ""

    @property
    def terminal(self) -> bool:
        return self.status in {
            ExportJobStatus.CANCELLED,
            ExportJobStatus.COMPLETED,
            ExportJobStatus.FAILED,
            ExportJobStatus.ORPHANED,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "request_signature": self.request_signature,
            "status": self.status.value,
            "progress": self.progress,
            "message": self.message,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "result_key": self.result_key,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, payload: MutableMapping[str, Any]) -> "ExportJobSnapshot":
        now = time()
        return cls(
            id=str(payload.get("id") or uuid4().hex),
            project_id=str(payload.get("project_id") or "default"),
            request_signature=str(payload.get("request_signature") or ""),
            status=ExportJobStatus(str(payload.get("status") or ExportJobStatus.PENDING.value)),
            progress=max(0, min(100, int(payload.get("progress", 0)))),
            message=str(payload.get("message") or ""),
            created_at=float(payload.get("created_at", now)),
            updated_at=float(payload.get("updated_at", now)),
            result_key=str(payload.get("result_key") or ""),
            error=str(payload.get("error") or ""),
        )


class ExportCancelled(RuntimeError):
    """Raised cooperatively when an export job cancellation was requested."""


ProgressCallback = Callable[[int, str], None]
ExportWork = Callable[[ProgressCallback, Callable[[], None]], Any]


class BackgroundExportManager:
    """Process-local executor with recoverable metadata-only job snapshots.

    Binary artifacts are intentionally not persisted in the snapshot store. The
    worker returns a result object that remains process-local; callers should
    copy completed bytes into the existing bounded export cache.
    """

    STATE_KEY = "background_export_jobs_v1"
    MAX_SNAPSHOTS = 20

    def __init__(
        self,
        state: MutableMapping[str, Any],
        *,
        max_workers: int = 1,
    ) -> None:
        self._state = state
        self._executor = ThreadPoolExecutor(max_workers=max(1, int(max_workers)), thread_name_prefix="gas-export")
        self._lock = RLock()
        self._futures: dict[str, Future[Any]] = {}
        self._cancel_events: dict[str, Event] = {}
        self._results: dict[str, Any] = {}
        self._recover_snapshots()

    def _store(self) -> dict[str, dict[str, Any]]:
        raw = self._state.get(self.STATE_KEY)
        if not isinstance(raw, dict):
            raw = {}
            self._state[self.STATE_KEY] = raw
        return raw

    def _recover_snapshots(self) -> None:
        """Mark interrupted non-terminal jobs as orphaned after app restart."""
        store = self._store()
        for job_id, payload in list(store.items()):
            try:
                snapshot = ExportJobSnapshot.from_dict(payload)
            except (TypeError, ValueError):
                store.pop(job_id, None)
                continue
            if snapshot.status in {
                ExportJobStatus.PENDING,
                ExportJobStatus.RUNNING,
                ExportJobStatus.CANCELLING,
            }:
                snapshot = replace(
                    snapshot,
                    status=ExportJobStatus.ORPHANED,
                    message="Предыдущая фоновая операция была прервана перезапуском приложения.",
                    updated_at=time(),
                )
                store[job_id] = snapshot.to_dict()
        self._trim_store()

    def _trim_store(self) -> None:
        store = self._store()
        ordered = sorted(
            store.items(),
            key=lambda item: float(item[1].get("updated_at", 0.0)) if isinstance(item[1], dict) else 0.0,
            reverse=True,
        )
        keep = {job_id for job_id, _ in ordered[: self.MAX_SNAPSHOTS]}
        for job_id in tuple(store):
            if job_id not in keep:
                store.pop(job_id, None)
                self._results.pop(job_id, None)

    def _write(self, snapshot: ExportJobSnapshot) -> None:
        self._store()[snapshot.id] = snapshot.to_dict()
        self._trim_store()

    def _read(self, job_id: str) -> ExportJobSnapshot:
        payload = self._store().get(job_id)
        if not isinstance(payload, dict):
            raise KeyError(f"Unknown export job: {job_id}")
        return ExportJobSnapshot.from_dict(payload)

    def submit(
        self,
        *,
        project_id: str,
        request_signature: str,
        work: ExportWork,
    ) -> ExportJobSnapshot:
        if not request_signature.strip():
            raise ValueError("request_signature must not be empty")
        with self._lock:
            for snapshot in self.list(project_id=project_id):
                if (
                    snapshot.request_signature == request_signature
                    and snapshot.status in {ExportJobStatus.PENDING, ExportJobStatus.RUNNING, ExportJobStatus.CANCELLING}
                ):
                    raise RuntimeError("Этот экспорт уже выполняется в фоновом режиме.")

            now = time()
            snapshot = ExportJobSnapshot(
                id=uuid4().hex,
                project_id=str(project_id),
                request_signature=request_signature,
                status=ExportJobStatus.PENDING,
                progress=0,
                message="Экспорт поставлен в очередь.",
                created_at=now,
                updated_at=now,
            )
            cancel_event = Event()
            self._cancel_events[snapshot.id] = cancel_event
            self._write(snapshot)
            future = self._executor.submit(self._run, snapshot.id, work, cancel_event)
            self._futures[snapshot.id] = future
            return snapshot

    def _run(self, job_id: str, work: ExportWork, cancel_event: Event) -> None:
        def check_cancelled() -> None:
            if cancel_event.is_set():
                raise ExportCancelled("Экспорт отменён пользователем.")

        def report(progress: int, message: str) -> None:
            with self._lock:
                current = self._read(job_id)
                if current.terminal:
                    return
                normalized = max(current.progress, min(99, max(0, int(progress))))
                status = ExportJobStatus.CANCELLING if cancel_event.is_set() else ExportJobStatus.RUNNING
                self._write(replace(current, status=status, progress=normalized, message=str(message), updated_at=time()))
            check_cancelled()

        with self._lock:
            current = self._read(job_id)
            self._write(replace(current, status=ExportJobStatus.RUNNING, progress=1, message="Экспорт запущен.", updated_at=time()))

        try:
            check_cancelled()
            result = work(report, check_cancelled)
            check_cancelled()
        except ExportCancelled as exc:
            with self._lock:
                current = self._read(job_id)
                self._write(replace(current, status=ExportJobStatus.CANCELLED, message=str(exc), updated_at=time()))
        except Exception as exc:  # worker boundary: persist safe diagnostic metadata
            with self._lock:
                current = self._read(job_id)
                self._write(
                    replace(
                        current,
                        status=ExportJobStatus.FAILED,
                        message="Экспорт завершился ошибкой.",
                        error=f"{type(exc).__name__}: {exc}",
                        updated_at=time(),
                    )
                )
        else:
            with self._lock:
                self._results[job_id] = result
                current = self._read(job_id)
                self._write(
                    replace(
                        current,
                        status=ExportJobStatus.COMPLETED,
                        progress=100,
                        message="Экспорт завершён.",
                        result_key=job_id,
                        updated_at=time(),
                    )
                )
        finally:
            with self._lock:
                self._cancel_events.pop(job_id, None)

    def cancel(self, job_id: str) -> ExportJobSnapshot:
        with self._lock:
            snapshot = self._read(job_id)
            if snapshot.terminal:
                return snapshot
            event = self._cancel_events.get(job_id)
            if event is not None:
                event.set()
            future = self._futures.get(job_id)
            if future is not None and future.cancel():
                snapshot = replace(
                    snapshot,
                    status=ExportJobStatus.CANCELLED,
                    message="Экспорт отменён до запуска.",
                    updated_at=time(),
                )
            else:
                snapshot = replace(
                    snapshot,
                    status=ExportJobStatus.CANCELLING,
                    message="Запрошена отмена экспорта.",
                    updated_at=time(),
                )
            self._write(snapshot)
            return snapshot

    def snapshot(self, job_id: str) -> ExportJobSnapshot:
        with self._lock:
            return self._read(job_id)

    def list(self, *, project_id: str | None = None) -> tuple[ExportJobSnapshot, ...]:
        with self._lock:
            snapshots: list[ExportJobSnapshot] = []
            for payload in self._store().values():
                if not isinstance(payload, dict):
                    continue
                try:
                    snapshot = ExportJobSnapshot.from_dict(payload)
                except (TypeError, ValueError):
                    continue
                if project_id is None or snapshot.project_id == str(project_id):
                    snapshots.append(snapshot)
            snapshots.sort(key=lambda item: item.updated_at, reverse=True)
            return tuple(snapshots)

    def pop_result(self, job_id: str) -> Any:
        with self._lock:
            snapshot = self._read(job_id)
            if snapshot.status is not ExportJobStatus.COMPLETED:
                raise RuntimeError("Результат экспорта ещё не готов.")
            if job_id not in self._results:
                raise RuntimeError("Результат фонового экспорта недоступен после перезапуска приложения.")
            return self._results.pop(job_id)


    def result_available(self, job_id: str) -> bool:
        """Return whether a completed process-local result can be handed off."""
        with self._lock:
            return job_id in self._results

    def dismiss(self, job_id: str) -> None:
        """Remove a terminal job snapshot and any unclaimed process-local result."""
        with self._lock:
            snapshot = self._read(job_id)
            if not snapshot.terminal:
                raise RuntimeError("Выполняющуюся задачу нельзя удалить из очереди.")
            self._store().pop(job_id, None)
            self._results.pop(job_id, None)
            self._futures.pop(job_id, None)
            self._cancel_events.pop(job_id, None)

    def shutdown(self, *, wait: bool = False) -> None:
        self._executor.shutdown(wait=wait, cancel_futures=True)
