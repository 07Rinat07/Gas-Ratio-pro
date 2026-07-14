"""Hardened JSON repository I/O with bounded runtime telemetry.

The module centralizes UTF-8 JSON reads and durable atomic writes. Runtime
metrics contain only primitive metadata and never retain payloads, file
handles, locks, or repository objects.
"""
from __future__ import annotations

import json
import os
import tempfile
from collections import deque
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter, time
from typing import Any, Callable, Mapping


@dataclass(frozen=True, slots=True)
class RepositoryIOEvent:
    repository: str
    operation: str
    status: str
    duration_ms: float
    bytes_count: int
    path_name: str
    timestamp: float
    error_type: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class RepositoryIOSnapshot:
    reads: int
    writes: int
    deletes: int
    failures: int
    bytes_read: int
    bytes_written: int
    total_duration_ms: float
    average_duration_ms: float
    events: tuple[RepositoryIOEvent, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "reads": self.reads,
            "writes": self.writes,
            "deletes": self.deletes,
            "failures": self.failures,
            "bytes_read": self.bytes_read,
            "bytes_written": self.bytes_written,
            "total_duration_ms": round(self.total_duration_ms, 2),
            "average_duration_ms": round(self.average_duration_ms, 2),
            "events": [event.to_dict() for event in self.events],
        }


class RepositoryIOMetrics:
    """Bounded process-local telemetry and repository mutation notifications."""

    def __init__(self, *, max_events: int = 100) -> None:
        if int(max_events) < 1:
            raise ValueError("max_events must be positive")
        self.max_events = int(max_events)
        self._events: deque[RepositoryIOEvent] = deque(maxlen=self.max_events)
        self._mutation_subscribers: dict[str, Callable[[dict[str, Any]], None]] = {}
        self._mutation_count = 0
        self._mutation_failures = 0
        self._last_mutation: dict[str, Any] = {}


    def subscribe_mutations(
        self, name: str, callback: Callable[[dict[str, Any]], None]
    ) -> None:
        clean = str(name).strip()
        if not clean:
            raise ValueError("mutation subscriber name must not be empty")
        self._mutation_subscribers[clean] = callback

    def unsubscribe_mutations(self, name: str) -> bool:
        return self._mutation_subscribers.pop(str(name), None) is not None

    @staticmethod
    def project_id_from_path(path: Path | str) -> str:
        parts = Path(path).parts
        try:
            index = parts.index("projects")
        except ValueError:
            return ""
        return str(parts[index + 1]) if index + 1 < len(parts) else ""

    def notify_mutation(
        self, *, repository: str, operation: str, path: Path | str
    ) -> None:
        target = Path(path)
        event = {
            "repository": str(repository),
            "operation": str(operation),
            "path_name": target.name,
            "suffix": target.suffix.lower(),
            "project_id": self.project_id_from_path(target),
            "timestamp": time(),
        }
        self._mutation_count += 1
        self._last_mutation = dict(event)
        for callback in tuple(self._mutation_subscribers.values()):
            try:
                callback(dict(event))
            except Exception:
                self._mutation_failures += 1

    def mutation_snapshot(self) -> dict[str, Any]:
        return {
            "mutation_count": self._mutation_count,
            "mutation_failures": self._mutation_failures,
            "subscriber_count": len(self._mutation_subscribers),
            "last_mutation": dict(self._last_mutation),
        }

    def record(
        self,
        *,
        repository: str,
        operation: str,
        status: str,
        duration_ms: float,
        bytes_count: int = 0,
        path: Path | str = "",
        error_type: str = "",
    ) -> RepositoryIOEvent:
        event = RepositoryIOEvent(
            repository=str(repository or "repository"),
            operation=str(operation),
            status=str(status),
            duration_ms=max(0.0, float(duration_ms)),
            bytes_count=max(0, int(bytes_count)),
            path_name=Path(path).name if path else "",
            timestamp=time(),
            error_type=str(error_type),
        )
        self._events.append(event)
        return event

    def snapshot(self, *, event_limit: int = 25) -> RepositoryIOSnapshot:
        events = tuple(self._events)
        reads = sum(1 for item in events if item.operation == "read")
        writes = sum(1 for item in events if item.operation == "write")
        deletes = sum(1 for item in events if item.operation == "delete")
        failures = sum(1 for item in events if item.status == "failed")
        duration = sum(item.duration_ms for item in events)
        count = len(events)
        limit = max(1, int(event_limit))
        return RepositoryIOSnapshot(
            reads=reads,
            writes=writes,
            deletes=deletes,
            failures=failures,
            bytes_read=sum(item.bytes_count for item in events if item.operation == "read"),
            bytes_written=sum(item.bytes_count for item in events if item.operation == "write"),
            total_duration_ms=duration,
            average_duration_ms=(duration / count) if count else 0.0,
            events=events[-limit:],
        )

    def clear(self) -> None:
        self._events.clear()


class AtomicJsonStore:
    """UTF-8 JSON store with durable replacement and optional schema checks."""

    def __init__(
        self,
        *,
        repository: str,
        metrics: RepositoryIOMetrics | None = None,
    ) -> None:
        clean = str(repository).strip()
        if not clean:
            raise ValueError("repository name must not be empty")
        self.repository = clean
        self.metrics = metrics

    def _record(
        self,
        operation: str,
        status: str,
        started: float,
        path: Path,
        *,
        bytes_count: int = 0,
        error: BaseException | None = None,
    ) -> None:
        if self.metrics is None:
            return
        self.metrics.record(
            repository=self.repository,
            operation=operation,
            status=status,
            duration_ms=(perf_counter() - started) * 1000.0,
            bytes_count=bytes_count,
            path=path,
            error_type=type(error).__name__ if error is not None else "",
        )

    def read(
        self,
        path: Path | str,
        *,
        expected_schema: str = "",
    ) -> dict[str, Any]:
        target = Path(path)
        started = perf_counter()
        try:
            raw = target.read_bytes()
            payload = json.loads(raw.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("JSON repository root must be an object")
            if expected_schema and payload.get("schema") != expected_schema:
                raise ValueError(f"Unsupported repository schema: {payload.get('schema')!r}")
        except Exception as exc:
            self._record("read", "failed", started, target, error=exc)
            raise
        self._record("read", "success", started, target, bytes_count=len(raw))
        return payload

    def write(self, path: Path | str, payload: Mapping[str, Any]) -> int:
        target = Path(path)
        started = perf_counter()
        temporary: Path | None = None
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            encoded = (
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
            ).encode("utf-8")
            descriptor, name = tempfile.mkstemp(
                prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
            )
            temporary = Path(name)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
            # Persist the directory entry on platforms that support directory fsync.
            try:
                directory_fd = os.open(target.parent, os.O_RDONLY)
            except (OSError, AttributeError):
                directory_fd = -1
            if directory_fd >= 0:
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
        except Exception as exc:
            self._record("write", "failed", started, target, error=exc)
            raise
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        self._record("write", "success", started, target, bytes_count=len(encoded))
        if self.metrics is not None:
            self.metrics.notify_mutation(repository=self.repository, operation="write", path=target)
        return len(encoded)

    def delete(self, path: Path | str, *, missing_ok: bool = True) -> bool:
        target = Path(path)
        started = perf_counter()
        existed = target.exists()
        try:
            target.unlink(missing_ok=missing_ok)
        except Exception as exc:
            self._record("delete", "failed", started, target, error=exc)
            raise
        self._record("delete", "success", started, target)
        if existed and self.metrics is not None:
            self.metrics.notify_mutation(repository=self.repository, operation="delete", path=target)
        return existed
