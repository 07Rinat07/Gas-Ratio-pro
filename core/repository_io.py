"""Hardened JSON repository I/O with bounded runtime telemetry.

The module centralizes UTF-8 JSON reads and durable atomic writes. Runtime
metrics contain only primitive metadata and never retain payloads, file
handles, locks, or repository objects.
"""
from __future__ import annotations

import json
import hashlib
import os
import tempfile
import uuid
import shutil
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
        self._recovery_count = 0
        self._recovery_failures = 0
        self._last_recovery: dict[str, Any] = {}
        self._integrity_checks = 0
        self._integrity_failures = 0
        self._quarantined_transactions = 0
        self._cleaned_transactions = 0


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

    def notify_recovery(
        self,
        *,
        repository: str,
        root: Path | str,
        recovered: int,
        failures: int,
        integrity_checks: int = 0,
        integrity_failures: int = 0,
        quarantined: int = 0,
        cleaned: int = 0,
    ) -> None:
        self._recovery_count += max(0, int(recovered))
        self._recovery_failures += max(0, int(failures))
        self._integrity_checks += max(0, int(integrity_checks))
        self._integrity_failures += max(0, int(integrity_failures))
        self._quarantined_transactions += max(0, int(quarantined))
        self._cleaned_transactions += max(0, int(cleaned))
        self._last_recovery = {
            "repository": str(repository),
            "root_name": Path(root).name,
            "recovered": max(0, int(recovered)),
            "failures": max(0, int(failures)),
            "integrity_checks": max(0, int(integrity_checks)),
            "integrity_failures": max(0, int(integrity_failures)),
            "quarantined": max(0, int(quarantined)),
            "cleaned": max(0, int(cleaned)),
            "timestamp": time(),
        }

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
            "recovery_count": self._recovery_count,
            "recovery_failures": self._recovery_failures,
            "last_recovery": dict(self._last_recovery),
            "integrity_checks": self._integrity_checks,
            "integrity_failures": self._integrity_failures,
            "quarantined_transactions": self._quarantined_transactions,
            "cleaned_transactions": self._cleaned_transactions,
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


@dataclass(frozen=True, slots=True)
class RepositoryTransactionInspection:
    transaction_id: str
    location: str
    status: str
    schema: str
    repository: str
    created_at: float
    entry_count: int
    recoverable: bool
    integrity_valid: bool
    issues: tuple[str, ...]
    path: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "transaction_id": self.transaction_id,
            "location": self.location,
            "status": self.status,
            "schema": self.schema,
            "repository": self.repository,
            "created_at": self.created_at,
            "entry_count": self.entry_count,
            "recoverable": self.recoverable,
            "integrity_valid": self.integrity_valid,
            "issues": list(self.issues),
            "path": self.path,
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

    @staticmethod
    def _sha256_bytes(payload: bytes) -> str:
        return hashlib.sha256(payload).hexdigest()

    @classmethod
    def _sha256_file(cls, path: Path) -> str:
        return cls._sha256_bytes(path.read_bytes())

    @staticmethod
    def _write_manifest(path: Path, payload: Mapping[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        encoded = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
        descriptor, name = tempfile.mkstemp(prefix=".manifest.", suffix=".tmp", dir=path.parent)
        temporary = Path(name)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
            AtomicJsonTransaction._sync_directory(path.parent)
        finally:
            temporary.unlink(missing_ok=True)

    @staticmethod
    def _common_root(paths: tuple[Path, ...]) -> Path:
        if not paths:
            raise ValueError("repository transaction has no changes")
        resolved = [str(path.resolve()) for path in paths]
        common = Path(os.path.commonpath(resolved))
        if common in tuple(path.resolve() for path in paths):
            common = common.parent
        return common

    def commit(self) -> RepositoryTransactionResult:
        self._ensure_open()
        self._closed = True
        started = perf_counter()
        paths = tuple(change[1] for change in self._changes)
        operations = tuple(change[0] for change in self._changes)
        if len(set(paths)) != len(paths):
            raise ValueError("transaction contains duplicate destination paths")
        root = self._common_root(paths)
        self.store.recover_transactions(root)
        transaction_dir = root / ".repository_transactions" / self.transaction_id
        manifest_path = transaction_dir / "manifest.json"
        entries: list[dict[str, Any]] = []
        try:
            transaction_dir.mkdir(parents=True, exist_ok=False)
            for index, (operation, target, encoded) in enumerate(self._changes):
                target = target.resolve()
                target.parent.mkdir(parents=True, exist_ok=True)
                backup_name = f"backup-{index:04d}.bin"
                staged_name = f"staged-{index:04d}.json"
                existed = target.exists()
                if existed:
                    backup_path = transaction_dir / backup_name
                    original_bytes = target.read_bytes()
                    backup_path.write_bytes(original_bytes)
                    with backup_path.open("rb") as stream:
                        os.fsync(stream.fileno())
                    before_sha256 = self._sha256_bytes(original_bytes)
                else:
                    before_sha256 = ""
                if operation == "write":
                    staged_path = transaction_dir / staged_name
                    staged_path.write_bytes(encoded or b"")
                    with staged_path.open("rb") as stream:
                        os.fsync(stream.fileno())
                    after_sha256 = self._sha256_bytes(encoded or b"")
                else:
                    after_sha256 = ""
                entries.append({
                    "operation": operation,
                    "target": str(target),
                    "existed": existed,
                    "backup": backup_name if existed else "",
                    "staged": staged_name if operation == "write" else "",
                    "before_sha256": before_sha256,
                    "after_sha256": after_sha256,
                })
            manifest = {
                "schema": "gas-ratio-pro/repository-transaction/v2",
                "transaction_id": self.transaction_id,
                "repository": self.store.repository,
                "root": str(root.resolve()),
                "status": "prepared",
                "entries": entries,
                "created_at": time(),
            }
            self._write_manifest(manifest_path, manifest)
            manifest["status"] = "applying"
            self._write_manifest(manifest_path, manifest)
            for entry in entries:
                target = Path(entry["target"])
                if entry["operation"] == "write":
                    os.replace(transaction_dir / entry["staged"], target)
                    if self._sha256_file(target) != str(entry.get("after_sha256", "")):
                        raise IOError(f"repository transaction integrity check failed: {target.name}")
                else:
                    target.unlink(missing_ok=True)
                    if target.exists():
                        raise IOError(f"repository transaction delete verification failed: {target.name}")
                self._sync_directory(target.parent)
            manifest["status"] = "committed"
            manifest["committed_at"] = time()
            manifest["integrity_verified"] = True
            self._write_manifest(manifest_path, manifest)
        except Exception as exc:
            self.store._recover_transaction_dir(transaction_dir, expected_root=root)
            duration_ms = (perf_counter() - started) * 1000.0
            if self.store.metrics is not None:
                self.store.metrics.notify_transaction(
                    repository=self.store.repository, transaction_id=self.transaction_id,
                    paths=paths, operations=operations, status="rolled_back",
                    duration_ms=duration_ms, error_type=type(exc).__name__,
                )
            raise
        else:
            shutil.rmtree(transaction_dir, ignore_errors=True)
            parent = transaction_dir.parent
            try:
                parent.rmdir()
            except OSError:
                pass
        duration_ms = (perf_counter() - started) * 1000.0
        if self.store.metrics is not None:
            self.store.metrics.notify_transaction(
                repository=self.store.repository, transaction_id=self.transaction_id,
                paths=paths, operations=operations, status="committed", duration_ms=duration_ms,
            )
        return RepositoryTransactionResult(
            transaction_id=self.transaction_id, status="committed",
            change_count=len(paths), duration_ms=duration_ms,
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

    @staticmethod
    def _sha256_file(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    @staticmethod
    def _quarantine_transaction_dir(transaction_dir: Path, *, root: Path) -> Path:
        quarantine_root = root / ".repository_transactions_quarantine"
        quarantine_root.mkdir(parents=True, exist_ok=True)
        destination = quarantine_root / transaction_dir.name
        if destination.exists():
            destination = quarantine_root / f"{transaction_dir.name}-{uuid.uuid4().hex[:8]}"
        os.replace(transaction_dir, destination)
        AtomicJsonTransaction._sync_directory(quarantine_root)
        return destination

    def _recover_transaction_dir(
        self, transaction_dir: Path, *, expected_root: Path
    ) -> tuple[bool, int, int, bool, bool]:
        """Recover one journal directory.

        Returns ``(recovered, checks, failures, quarantined, cleaned)``.
        Corrupt or unsafe journals are quarantined instead of being deleted.
        """
        manifest_path = transaction_dir / "manifest.json"
        if not manifest_path.exists():
            self._quarantine_transaction_dir(transaction_dir, root=expected_root)
            return False, 0, 1, True, False
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            self._quarantine_transaction_dir(transaction_dir, root=expected_root)
            return False, 0, 1, True, False
        if not isinstance(payload, dict) or payload.get("schema") not in {
            "gas-ratio-pro/repository-transaction/v1",
            "gas-ratio-pro/repository-transaction/v2",
        }:
            self._quarantine_transaction_dir(transaction_dir, root=expected_root)
            return False, 0, 1, True, False
        root = Path(str(payload.get("root", ""))).resolve()
        if root != expected_root.resolve():
            self._quarantine_transaction_dir(transaction_dir, root=expected_root)
            return False, 0, 1, True, False
        status = str(payload.get("status", ""))
        checks = 0
        integrity_failures = 0
        if status != "committed":
            try:
                entries = list(payload.get("entries", []))
            except Exception:
                self._quarantine_transaction_dir(transaction_dir, root=expected_root)
                return False, 0, 1, True, False
            for entry in reversed(entries):
                if not isinstance(entry, dict):
                    self._quarantine_transaction_dir(transaction_dir, root=expected_root)
                    return False, checks, integrity_failures + 1, True, False
                target = Path(str(entry.get("target", ""))).resolve()
                try:
                    target.relative_to(root)
                except ValueError:
                    self._quarantine_transaction_dir(transaction_dir, root=expected_root)
                    return False, checks, integrity_failures + 1, True, False
                if bool(entry.get("existed")):
                    backup = transaction_dir / str(entry.get("backup", ""))
                    if not backup.exists():
                        self._quarantine_transaction_dir(transaction_dir, root=expected_root)
                        return False, checks, integrity_failures + 1, True, False
                    expected_hash = str(entry.get("before_sha256", ""))
                    if expected_hash:
                        checks += 1
                        if self._sha256_file(backup) != expected_hash:
                            self._quarantine_transaction_dir(transaction_dir, root=expected_root)
                            return False, checks, integrity_failures + 1, True, False
                    descriptor, name = tempfile.mkstemp(prefix=f".{target.name}.recover.", suffix=".tmp", dir=target.parent)
                    temporary = Path(name)
                    with os.fdopen(descriptor, "wb") as stream:
                        stream.write(backup.read_bytes())
                        stream.flush()
                        os.fsync(stream.fileno())
                    os.replace(temporary, target)
                    if expected_hash:
                        checks += 1
                        if self._sha256_file(target) != expected_hash:
                            integrity_failures += 1
                            raise IOError(f"recovered file integrity mismatch: {target.name}")
                else:
                    target.unlink(missing_ok=True)
                    checks += 1
                    if target.exists():
                        integrity_failures += 1
                        raise IOError(f"recovered delete verification failed: {target.name}")
                AtomicJsonTransaction._sync_directory(target.parent)
        else:
            for entry in list(payload.get("entries", [])):
                if not isinstance(entry, dict):
                    continue
                target = Path(str(entry.get("target", ""))).resolve()
                try:
                    target.relative_to(root)
                except ValueError:
                    self._quarantine_transaction_dir(transaction_dir, root=expected_root)
                    return False, checks, integrity_failures + 1, True, False
                expected_hash = str(entry.get("after_sha256", ""))
                if entry.get("operation") == "write" and expected_hash:
                    checks += 1
                    if not target.exists() or self._sha256_file(target) != expected_hash:
                        self._quarantine_transaction_dir(transaction_dir, root=expected_root)
                        return False, checks, integrity_failures + 1, True, False
                elif entry.get("operation") == "delete":
                    checks += 1
                    if target.exists():
                        self._quarantine_transaction_dir(transaction_dir, root=expected_root)
                        return False, checks, integrity_failures + 1, True, False
        shutil.rmtree(transaction_dir, ignore_errors=True)
        return status != "committed", checks, integrity_failures, False, True

    def recover_transactions(self, root: Path | str) -> dict[str, int]:
        recovery_root = Path(root).resolve()
        journal_root = recovery_root / ".repository_transactions"
        recovered = 0
        failures = 0
        integrity_checks = 0
        integrity_failures = 0
        quarantined = 0
        cleaned = 0
        if journal_root.exists():
            for transaction_dir in sorted(path for path in journal_root.iterdir() if path.is_dir()):
                try:
                    result = self._recover_transaction_dir(transaction_dir, expected_root=recovery_root)
                    was_recovered, checks, check_failures, was_quarantined, was_cleaned = result
                    integrity_checks += checks
                    integrity_failures += check_failures
                    quarantined += int(was_quarantined)
                    cleaned += int(was_cleaned)
                    if was_recovered:
                        recovered += 1
                except Exception:
                    failures += 1
            try:
                journal_root.rmdir()
            except OSError:
                pass
        if self.metrics is not None and (
            recovered or failures or integrity_checks or integrity_failures or quarantined or cleaned
        ):
            self.metrics.notify_recovery(
                repository=self.repository,
                root=recovery_root,
                recovered=recovered,
                failures=failures,
                integrity_checks=integrity_checks,
                integrity_failures=integrity_failures,
                quarantined=quarantined,
                cleaned=cleaned,
            )
        return {"recovered": recovered, "failures": failures}

    def inspect_transaction_directory(
        self,
        transaction_dir: Path | str,
        *,
        expected_root: Path | str,
        location: str = "active",
    ) -> RepositoryTransactionInspection:
        """Inspect a transaction journal without mutating repository data."""

        directory = Path(transaction_dir).resolve()
        root = Path(expected_root).resolve()
        issues: list[str] = []
        payload: dict[str, Any] = {}
        manifest_path = directory / "manifest.json"
        if not manifest_path.exists():
            issues.append("manifest_missing")
        else:
            try:
                loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    payload = loaded
                else:
                    issues.append("manifest_root_not_object")
            except Exception:
                issues.append("manifest_invalid_json")

        schema = str(payload.get("schema", ""))
        if payload and schema not in {
            "gas-ratio-pro/repository-transaction/v1",
            "gas-ratio-pro/repository-transaction/v2",
        }:
            issues.append("schema_unsupported")
        manifest_root = Path(str(payload.get("root", ""))).resolve() if payload.get("root") else None
        if payload and manifest_root != root:
            issues.append("root_mismatch")

        raw_entries = payload.get("entries", []) if payload else []
        if not isinstance(raw_entries, list):
            issues.append("entries_invalid")
            raw_entries = []
        status = str(payload.get("status", "unknown"))
        for index, entry in enumerate(raw_entries):
            prefix = f"entry_{index}"
            if not isinstance(entry, dict):
                issues.append(prefix + "_invalid")
                continue
            target_text = str(entry.get("target", ""))
            if not target_text:
                issues.append(prefix + "_target_missing")
                continue
            target = Path(target_text).resolve()
            try:
                target.relative_to(root)
            except ValueError:
                issues.append(prefix + "_target_outside_root")
                continue
            operation = str(entry.get("operation", ""))
            if operation not in {"write", "delete"}:
                issues.append(prefix + "_operation_invalid")
            if status != "committed" and bool(entry.get("existed")):
                backup_name = str(entry.get("backup", ""))
                backup = directory / backup_name
                if not backup_name or not backup.exists():
                    issues.append(prefix + "_backup_missing")
                else:
                    expected_hash = str(entry.get("before_sha256", ""))
                    if expected_hash and self._sha256_file(backup) != expected_hash:
                        issues.append(prefix + "_backup_hash_mismatch")
            if status == "committed":
                expected_hash = str(entry.get("after_sha256", ""))
                if operation == "write" and expected_hash:
                    if not target.exists() or self._sha256_file(target) != expected_hash:
                        issues.append(prefix + "_committed_hash_mismatch")
                elif operation == "delete" and target.exists():
                    issues.append(prefix + "_committed_delete_mismatch")

        integrity_valid = not issues
        recoverable = integrity_valid and status in {"prepared", "applying"}
        return RepositoryTransactionInspection(
            transaction_id=str(payload.get("transaction_id", directory.name)),
            location=str(location),
            status=status,
            schema=schema,
            repository=str(payload.get("repository", "")),
            created_at=float(payload.get("created_at", 0.0) or 0.0),
            entry_count=len(raw_entries),
            recoverable=recoverable,
            integrity_valid=integrity_valid,
            issues=tuple(issues),
            path=str(directory),
        )

    def list_transaction_journals(self, root: Path | str) -> list[dict[str, Any]]:
        """Return active and quarantined journals as JSON-compatible metadata."""

        recovery_root = Path(root).resolve()
        rows: list[RepositoryTransactionInspection] = []
        locations = (
            ("active", recovery_root / ".repository_transactions"),
            ("quarantine", recovery_root / ".repository_transactions_quarantine"),
        )
        for location, parent in locations:
            if not parent.exists():
                continue
            for directory in sorted(path for path in parent.iterdir() if path.is_dir()):
                rows.append(self.inspect_transaction_directory(
                    directory, expected_root=recovery_root, location=location
                ))
        return [item.to_dict() for item in rows]

    def recover_quarantined_transaction(
        self, root: Path | str, transaction_id: str
    ) -> dict[str, Any]:
        """Safely roll back one valid incomplete transaction from quarantine."""

        recovery_root = Path(root).resolve()
        clean_id = str(transaction_id).strip()
        if not clean_id or Path(clean_id).name != clean_id:
            raise ValueError("invalid transaction id")
        quarantine_root = recovery_root / ".repository_transactions_quarantine"
        candidates = [
            path for path in quarantine_root.glob(clean_id + "*")
            if path.is_dir() and (path.name == clean_id or path.name.startswith(clean_id + "-"))
        ]
        if len(candidates) != 1:
            raise FileNotFoundError(f"quarantined transaction not uniquely found: {clean_id}")
        source = candidates[0].resolve()
        inspection = self.inspect_transaction_directory(
            source, expected_root=recovery_root, location="quarantine"
        )
        if not inspection.recoverable:
            raise ValueError("quarantined transaction is not safe for automatic recovery")
        active_root = recovery_root / ".repository_transactions"
        active_root.mkdir(parents=True, exist_ok=True)
        destination = active_root / source.name
        if destination.exists():
            raise FileExistsError(destination)
        os.replace(source, destination)
        AtomicJsonTransaction._sync_directory(active_root)
        recovered, checks, failures, quarantined, cleaned = self._recover_transaction_dir(
            destination, expected_root=recovery_root
        )
        try:
            quarantine_root.rmdir()
        except OSError:
            pass
        if self.metrics is not None:
            self.metrics.notify_recovery(
                repository=self.repository, root=recovery_root,
                recovered=int(recovered), failures=0 if recovered else 1,
                integrity_checks=checks, integrity_failures=failures,
                quarantined=int(quarantined), cleaned=int(cleaned),
            )
        return {
            "transaction_id": inspection.transaction_id,
            "recovered": bool(recovered),
            "integrity_checks": checks,
            "integrity_failures": failures,
            "quarantined": bool(quarantined),
            "cleaned": bool(cleaned),
        }

    def cleanup_transaction_journals(
        self,
        root: Path | str,
        *,
        older_than_seconds: float = 30 * 24 * 60 * 60,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Remove only integrity-valid committed journals older than retention."""

        recovery_root = Path(root).resolve()
        cutoff = time() - max(0.0, float(older_than_seconds))
        candidates: list[str] = []
        removed: list[str] = []
        journal_root = recovery_root / ".repository_transactions"
        if journal_root.exists():
            for directory in sorted(path for path in journal_root.iterdir() if path.is_dir()):
                inspection = self.inspect_transaction_directory(
                    directory, expected_root=recovery_root, location="active"
                )
                created_at = inspection.created_at or directory.stat().st_mtime
                if inspection.status == "committed" and inspection.integrity_valid and created_at <= cutoff:
                    candidates.append(inspection.transaction_id)
                    if not dry_run:
                        shutil.rmtree(directory)
                        removed.append(inspection.transaction_id)
            if not dry_run:
                try:
                    journal_root.rmdir()
                except OSError:
                    pass
        return {
            "dry_run": bool(dry_run),
            "candidate_count": len(candidates),
            "removed_count": len(removed),
            "candidates": candidates,
            "removed": removed,
        }

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
