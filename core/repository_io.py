"""Hardened JSON repository I/O with bounded runtime telemetry.

The module centralizes UTF-8 JSON reads and durable atomic writes. Runtime
metrics contain only primitive metadata and never retain payloads, file
handles, locks, or repository objects.
"""
from __future__ import annotations

import json
import os
import tempfile
import uuid
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
        self._transaction_count = 0
        self._transaction_failures = 0
        self._last_transaction: dict[str, Any] = {}
        self._transactions: deque[dict[str, Any]] = deque(maxlen=self.max_events)


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

    def _publish_mutation(self, event: Mapping[str, Any]) -> None:
        payload = dict(event)
        self._mutation_count += 1
        self._last_mutation = dict(payload)
        for callback in tuple(self._mutation_subscribers.values()):
            try:
                callback(dict(payload))
            except Exception:
                self._mutation_failures += 1

    def notify_mutation(
        self, *, repository: str, operation: str, path: Path | str
    ) -> None:
        target = Path(path)
        self._publish_mutation({
            "repository": str(repository),
            "operation": str(operation),
            "path_name": target.name,
            "path_names": [target.name],
            "suffix": target.suffix.lower(),
            "project_id": self.project_id_from_path(target),
            "transaction_id": "",
            "change_count": 1,
            "timestamp": time(),
        })

    def notify_transaction(
        self,
        *,
        repository: str,
        transaction_id: str,
        paths: tuple[Path, ...],
        operations: tuple[str, ...],
        status: str,
        duration_ms: float,
        error_type: str = "",
    ) -> None:
        project_ids = {self.project_id_from_path(path) for path in paths}
        project_ids.discard("")
        event = {
            "repository": str(repository),
            "operation": "transaction",
            "path_name": paths[0].name if paths else "",
            "path_names": [path.name for path in paths],
            "suffix": "",
            "project_id": next(iter(project_ids)) if len(project_ids) == 1 else "",
            "transaction_id": str(transaction_id),
            "change_count": len(paths),
            "operations": list(operations),
            "status": str(status),
            "duration_ms": round(max(0.0, float(duration_ms)), 2),
            "error_type": str(error_type),
            "timestamp": time(),
        }
        self._transaction_count += 1
        if status != "committed":
            self._transaction_failures += 1
        self._last_transaction = dict(event)
        self._transactions.append(dict(event))
        if status == "committed":
            self._publish_mutation(event)

    def mutation_snapshot(self) -> dict[str, Any]:
        return {
            "mutation_count": self._mutation_count,
            "mutation_failures": self._mutation_failures,
            "subscriber_count": len(self._mutation_subscribers),
            "last_mutation": dict(self._last_mutation),
            "transaction_count": self._transaction_count,
            "transaction_failures": self._transaction_failures,
            "last_transaction": dict(self._last_transaction),
            "recent_transactions": [dict(item) for item in self._transactions],
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


@dataclass(frozen=True, slots=True)
class RepositoryTransactionResult:
    transaction_id: str
    status: str
    change_count: int
    duration_ms: float
    paths: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "transaction_id": self.transaction_id,
            "status": self.status,
            "change_count": self.change_count,
            "duration_ms": round(self.duration_ms, 2),
            "paths": list(self.paths),
        }


class AtomicJsonTransaction:
    """Stage several JSON writes/deletes and publish one coherent mutation.

    Files are prepared before the first destination is replaced. If any commit
    step fails, previously replaced files are restored from byte-for-byte
    backups. The transaction contains no locks or payloads after completion.
    """

    def __init__(self, store: "AtomicJsonStore") -> None:
        self.store = store
        self.transaction_id = uuid.uuid4().hex
        self._changes: list[tuple[str, Path, bytes | None]] = []
        self._closed = False

    def write(self, path: Path | str, payload: Mapping[str, Any]) -> None:
        self._ensure_open()
        encoded = (
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8")
        self._changes.append(("write", Path(path), encoded))

    def delete(self, path: Path | str, *, missing_ok: bool = True) -> None:
        self._ensure_open()
        target = Path(path)
        if not missing_ok and not target.exists():
            raise FileNotFoundError(target)
        self._changes.append(("delete", target, None))

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("repository transaction is already closed")

    @staticmethod
    def _sync_directory(path: Path) -> None:
        try:
            descriptor = os.open(path, os.O_RDONLY)
        except (OSError, AttributeError):
            return
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def commit(self) -> RepositoryTransactionResult:
        self._ensure_open()
        self._closed = True
        started = perf_counter()
        staged: dict[Path, Path] = {}
        backups: dict[Path, bytes | None] = {}
        applied: list[Path] = []
        paths = tuple(change[1] for change in self._changes)
        operations = tuple(change[0] for change in self._changes)
        try:
            if len(set(paths)) != len(paths):
                raise ValueError("transaction contains duplicate destination paths")
            for operation, target, encoded in self._changes:
                target.parent.mkdir(parents=True, exist_ok=True)
                backups[target] = target.read_bytes() if target.exists() else None
                if operation == "write":
                    descriptor, name = tempfile.mkstemp(
                        prefix=f".{target.name}.{self.transaction_id}.",
                        suffix=".tmp",
                        dir=target.parent,
                    )
                    temporary = Path(name)
                    with os.fdopen(descriptor, "wb") as stream:
                        stream.write(encoded or b"")
                        stream.flush()
                        os.fsync(stream.fileno())
                    staged[target] = temporary
            for operation, target, _encoded in self._changes:
                if operation == "write":
                    os.replace(staged[target], target)
                else:
                    target.unlink(missing_ok=True)
                applied.append(target)
                self._sync_directory(target.parent)
        except Exception as exc:
            for target in reversed(applied):
                original = backups.get(target)
                try:
                    if original is None:
                        target.unlink(missing_ok=True)
                    else:
                        descriptor, name = tempfile.mkstemp(
                            prefix=f".{target.name}.rollback.", suffix=".tmp", dir=target.parent
                        )
                        temporary = Path(name)
                        with os.fdopen(descriptor, "wb") as stream:
                            stream.write(original)
                            stream.flush()
                            os.fsync(stream.fileno())
                        os.replace(temporary, target)
                        self._sync_directory(target.parent)
                except Exception:
                    # Preserve the original transaction failure. Rollback health
                    # is visible through the failed transaction diagnostic.
                    pass
            duration_ms = (perf_counter() - started) * 1000.0
            if self.store.metrics is not None:
                self.store.metrics.notify_transaction(
                    repository=self.store.repository,
                    transaction_id=self.transaction_id,
                    paths=paths,
                    operations=operations,
                    status="rolled_back",
                    duration_ms=duration_ms,
                    error_type=type(exc).__name__,
                )
            raise
        finally:
            for temporary in staged.values():
                temporary.unlink(missing_ok=True)
        duration_ms = (perf_counter() - started) * 1000.0
        if self.store.metrics is not None:
            self.store.metrics.notify_transaction(
                repository=self.store.repository,
                transaction_id=self.transaction_id,
                paths=paths,
                operations=operations,
                status="committed",
                duration_ms=duration_ms,
            )
        return RepositoryTransactionResult(
            transaction_id=self.transaction_id,
            status="committed",
            change_count=len(paths),
            duration_ms=duration_ms,
            paths=tuple(path.name for path in paths),
        )

    def rollback(self) -> None:
        self._ensure_open()
        self._closed = True
        self._changes.clear()

    def __enter__(self) -> "AtomicJsonTransaction":
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> bool:
        if exc_type is not None:
            self.rollback()
            return False
        self.commit()
        return False


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

    def transaction(self) -> AtomicJsonTransaction:
        """Create a staged multi-file transaction for this repository."""

        return AtomicJsonTransaction(self)

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
