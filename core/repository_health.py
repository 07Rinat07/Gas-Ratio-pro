"""Repository health scanning and explicit repair planning.

The scanner is read-only by default.  It records only serializable metadata and
never retains repository payloads.  Repairs require an explicit action id and
revalidate the target before moving it into a project-local quarantine.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter, time
from typing import Any, Iterable


@dataclass(frozen=True, slots=True)
class RepositoryHealthIssue:
    issue_id: str
    severity: str
    kind: str
    relative_path: str
    message: str
    repairable: bool
    token: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class RepositoryRepairAction:
    action_id: str
    issue_id: str
    operation: str
    relative_path: str
    destination: str
    token: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class RepositoryHealthSnapshot:
    root_name: str
    scanned_at: float
    duration_ms: float
    files_scanned: int
    json_files: int
    total_bytes: int
    healthy: bool
    truncated: bool
    issues: tuple[RepositoryHealthIssue, ...]
    repair_plan: tuple[RepositoryRepairAction, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "root_name": self.root_name,
            "scanned_at": self.scanned_at,
            "duration_ms": round(self.duration_ms, 2),
            "files_scanned": self.files_scanned,
            "json_files": self.json_files,
            "total_bytes": self.total_bytes,
            "healthy": self.healthy,
            "truncated": self.truncated,
            "issue_count": len(self.issues),
            "repairable_count": sum(1 for item in self.issues if item.repairable),
            "severity_counts": {
                level: sum(1 for item in self.issues if item.severity == level)
                for level in ("error", "warning", "info")
            },
            "issues": [item.to_dict() for item in self.issues],
            "repair_plan": [item.to_dict() for item in self.repair_plan],
        }


class RepositoryHealthService:
    """Bounded, throttled repository scanner with explicit quarantine repairs."""

    EXCLUDED_DIRS = {
        ".git", ".venv", "__pycache__", ".pytest_cache",
        ".repository_health_quarantine",
    }

    def __init__(
        self,
        root: Path | str,
        *,
        max_files: int = 5000,
        max_json_bytes: int = 8 * 1024 * 1024,
        stale_temp_seconds: float = 24 * 60 * 60,
        scan_ttl_seconds: float = 30.0,
    ) -> None:
        self.root = Path(root).resolve()
        self.max_files = max(1, int(max_files))
        self.max_json_bytes = max(1024, int(max_json_bytes))
        self.stale_temp_seconds = max(0.0, float(stale_temp_seconds))
        self.scan_ttl_seconds = max(0.0, float(scan_ttl_seconds))
        self._latest: RepositoryHealthSnapshot | None = None

    @staticmethod
    def _file_token(path: Path) -> str:
        stat = path.stat()
        material = f"{path.resolve()}|{stat.st_size}|{stat.st_mtime_ns}".encode("utf-8")
        return hashlib.sha256(material).hexdigest()

    @staticmethod
    def _issue_id(kind: str, relative_path: str, token: str) -> str:
        return hashlib.sha256(f"{kind}|{relative_path}|{token}".encode("utf-8")).hexdigest()[:20]

    def _iter_files(self) -> Iterable[Path]:
        for current, dirs, files in os.walk(self.root):
            dirs[:] = [name for name in dirs if name not in self.EXCLUDED_DIRS]
            for name in files:
                yield Path(current) / name

    def scan(self, *, force: bool = False) -> RepositoryHealthSnapshot:
        now = time()
        if (
            not force and self._latest is not None
            and now - self._latest.scanned_at < self.scan_ttl_seconds
        ):
            return self._latest
        started = perf_counter()
        issues: list[RepositoryHealthIssue] = []
        files_scanned = json_files = total_bytes = 0
        truncated = False

        if not self.root.exists():
            token = hashlib.sha256(str(self.root).encode("utf-8")).hexdigest()
            issues.append(RepositoryHealthIssue(
                issue_id=self._issue_id("root_missing", ".", token),
                severity="error", kind="root_missing", relative_path=".",
                message="Repository root does not exist.", repairable=False, token=token,
            ))
        else:
            for path in self._iter_files():
                if files_scanned >= self.max_files:
                    truncated = True
                    break
                files_scanned += 1
                try:
                    stat = path.stat()
                except OSError as exc:
                    token = hashlib.sha256(str(path).encode("utf-8")).hexdigest()
                    rel = str(path.relative_to(self.root))
                    issues.append(RepositoryHealthIssue(
                        self._issue_id("stat_failed", rel, token), "warning", "stat_failed",
                        rel, f"Cannot inspect file metadata: {type(exc).__name__}", False, token,
                    ))
                    continue
                total_bytes += max(0, stat.st_size)
                rel = str(path.relative_to(self.root))
                suffix = path.suffix.lower()
                token = self._file_token(path)
                if suffix == ".json":
                    json_files += 1
                    if stat.st_size > self.max_json_bytes:
                        issues.append(RepositoryHealthIssue(
                            self._issue_id("json_oversized", rel, token), "warning", "json_oversized",
                            rel, f"JSON file exceeds scan limit ({stat.st_size} bytes).", False, token,
                        ))
                        continue
                    try:
                        with path.open("r", encoding="utf-8") as stream:
                            json.load(stream)
                    except (UnicodeError, json.JSONDecodeError, OSError) as exc:
                        issues.append(RepositoryHealthIssue(
                            self._issue_id("invalid_json", rel, token), "error", "invalid_json",
                            rel, f"Invalid JSON: {type(exc).__name__}", True, token,
                        ))
                elif suffix == ".tmp" or name_is_temp(path.name):
                    age = max(0.0, now - stat.st_mtime)
                    if age >= self.stale_temp_seconds:
                        issues.append(RepositoryHealthIssue(
                            self._issue_id("stale_temp", rel, token), "warning", "stale_temp",
                            rel, f"Stale temporary file ({int(age)} seconds old).", True, token,
                        ))

        if truncated:
            token = hashlib.sha256(f"truncated|{self.max_files}".encode("utf-8")).hexdigest()
            issues.append(RepositoryHealthIssue(
                self._issue_id("scan_truncated", ".", token), "warning", "scan_truncated", ".",
                f"Scan stopped after {self.max_files} files.", False, token,
            ))

        plan = tuple(self._build_action(item) for item in issues if item.repairable)
        snapshot = RepositoryHealthSnapshot(
            root_name=self.root.name,
            scanned_at=now,
            duration_ms=(perf_counter() - started) * 1000.0,
            files_scanned=files_scanned,
            json_files=json_files,
            total_bytes=total_bytes,
            healthy=not any(item.severity == "error" for item in issues),
            truncated=truncated,
            issues=tuple(issues),
            repair_plan=plan,
        )
        self._latest = snapshot
        return snapshot

    def _build_action(self, issue: RepositoryHealthIssue) -> RepositoryRepairAction:
        source = self.root / issue.relative_path
        destination = self.root / ".repository_health_quarantine" / issue.relative_path
        return RepositoryRepairAction(
            action_id=hashlib.sha256(f"repair|{issue.issue_id}|{issue.token}".encode()).hexdigest()[:24],
            issue_id=issue.issue_id,
            operation="quarantine",
            relative_path=issue.relative_path,
            destination=str(destination.relative_to(self.root)),
            token=issue.token,
        )

    def apply_repair(self, action_id: str) -> dict[str, Any]:
        snapshot = self.scan(force=True)
        matches = [item for item in snapshot.repair_plan if item.action_id == str(action_id)]
        if len(matches) != 1:
            raise ValueError("repair action is missing or stale")
        action = matches[0]
        source = (self.root / action.relative_path).resolve()
        source.relative_to(self.root)
        if not source.exists() or self._file_token(source) != action.token:
            raise ValueError("repair target changed after scan")
        destination = (self.root / action.destination).resolve()
        destination.relative_to(self.root)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            destination = destination.with_name(destination.name + f".{int(time())}")
        os.replace(source, destination)
        self._latest = None
        return {
            "action_id": action.action_id,
            "status": "quarantined",
            "source": action.relative_path,
            "destination": str(destination.relative_to(self.root)),
        }

    def close(self) -> None:
        self._latest = None


def name_is_temp(name: str) -> bool:
    clean = str(name).lower()
    return clean.startswith(".") and (clean.endswith(".tmp") or ".tmp." in clean)
