"""Repository for multiple recoverable LAS Viewer workspace autosaves."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import os
from pathlib import Path
import re
from typing import Iterable

from services.las_viewer_session import LasViewerSession, LasViewerState
from services.las_viewer_workspace_autosave import (
    LasViewerAutosaveResult,
    LasViewerWorkspaceAutosaveStore,
)


@dataclass(frozen=True, slots=True)
class LasViewerAutosaveRepositoryEntry:
    filename: str
    modified_ns: int
    project_id: str = ""
    las_id: str = ""
    valid: bool = False
    reason: str = ""


@dataclass(frozen=True, slots=True)
class LasViewerAutosaveRepositoryRecovery:
    recovered: bool
    state: LasViewerState | None = None
    path: str = ""
    used_backup: bool = False
    inspected: int = 0
    skipped_invalid: int = 0
    reason: str = ""


@dataclass(frozen=True, slots=True)
class LasViewerAutosaveRepositoryRemoval:
    removed: bool
    filename: str = ""
    removed_files: int = 0
    reason: str = ""



class LasViewerWorkspaceAutosaveRepository:
    """Manage independent autosaves for multiple LAS Viewer sessions."""

    PREFIX = "las-viewer-"
    SUFFIX = ".autosave.json"

    def __init__(self, directory: str | os.PathLike[str], *, max_entries: int = 20) -> None:
        if int(max_entries) < 1:
            raise ValueError("max_entries must be >= 1")
        self.directory = Path(directory).expanduser()
        self.max_entries = int(max_entries)

    def save(self, session: LasViewerSession) -> LasViewerAutosaveResult:
        store = self._store_for_state(session.state)
        result = store.save(session)
        self.prune()
        return result

    def recover_latest(self, *, project_id: str = "", las_id: str = "") -> LasViewerAutosaveRepositoryRecovery:
        inspected = 0
        skipped = 0
        for filename, _modified in self._candidate_files():
            inspected += 1
            result = LasViewerWorkspaceAutosaveStore(self.directory, filename=filename).recover(
                project_id=project_id,
                las_id=las_id,
            )
            if result.recovered and result.state is not None:
                return LasViewerAutosaveRepositoryRecovery(
                    recovered=True,
                    state=result.state,
                    path=result.path,
                    used_backup=result.used_backup,
                    inspected=inspected,
                    skipped_invalid=skipped,
                )
            skipped += 1
        return LasViewerAutosaveRepositoryRecovery(
            recovered=False,
            inspected=inspected,
            skipped_invalid=skipped,
            reason="missing_compatible_autosave" if inspected else "missing_autosave",
        )


    def recover_entry(self, filename: str) -> LasViewerAutosaveRepositoryRecovery:
        """Recover one repository entry by its safe repository filename."""
        name = Path(str(filename or "")).name
        if name != str(filename or "") or not name.startswith(self.PREFIX) or not name.endswith(self.SUFFIX):
            return LasViewerAutosaveRepositoryRecovery(recovered=False, reason="invalid_repository_filename")
        candidates = {candidate for candidate, _modified in self._candidate_files()}
        if name not in candidates:
            return LasViewerAutosaveRepositoryRecovery(recovered=False, reason="missing_autosave")
        result = LasViewerWorkspaceAutosaveStore(self.directory, filename=name).recover()
        if not result.recovered or result.state is None:
            return LasViewerAutosaveRepositoryRecovery(
                recovered=False,
                path=result.path,
                used_backup=result.used_backup,
                inspected=1,
                skipped_invalid=1,
                reason=result.reason or "invalid_autosave",
            )
        return LasViewerAutosaveRepositoryRecovery(
            recovered=True,
            state=result.state,
            path=result.path,
            used_backup=result.used_backup,
            inspected=1,
        )


    def remove_entry(self, filename: str) -> LasViewerAutosaveRepositoryRemoval:
        """Remove one autosave entry and its backup using a safe repository name."""
        name = Path(str(filename or "")).name
        if name != str(filename or "") or not name.startswith(self.PREFIX) or not name.endswith(self.SUFFIX):
            return LasViewerAutosaveRepositoryRemoval(
                removed=False,
                filename=name,
                reason="invalid_repository_filename",
            )
        candidates = {candidate for candidate, _modified in self._candidate_files()}
        if name not in candidates:
            return LasViewerAutosaveRepositoryRemoval(
                removed=False,
                filename=name,
                reason="missing_autosave",
            )
        removed_files = LasViewerWorkspaceAutosaveStore(self.directory, filename=name).clear()
        return LasViewerAutosaveRepositoryRemoval(
            removed=removed_files > 0,
            filename=name,
            removed_files=removed_files,
            reason="removed" if removed_files else "missing_autosave",
        )

    def recover_latest_session(self, *, project_id: str = "", las_id: str = "") -> LasViewerSession | None:
        result = self.recover_latest(project_id=project_id, las_id=las_id)
        return LasViewerSession.from_state(result.state) if result.recovered and result.state is not None else None

    def entries(self) -> tuple[LasViewerAutosaveRepositoryEntry, ...]:
        items: list[LasViewerAutosaveRepositoryEntry] = []
        for filename, modified in self._candidate_files():
            result = LasViewerWorkspaceAutosaveStore(self.directory, filename=filename).recover()
            state = result.state
            items.append(
                LasViewerAutosaveRepositoryEntry(
                    filename=filename,
                    modified_ns=modified,
                    project_id=state.project_id if state else "",
                    las_id=state.las_id if state else "",
                    valid=bool(result.recovered and state is not None),
                    reason=result.reason,
                )
            )
        return tuple(items)

    def prune(self, *, keep: int | None = None) -> int:
        limit = self.max_entries if keep is None else int(keep)
        if limit < 1:
            raise ValueError("keep must be >= 1")
        candidates = self._candidate_files()
        removed = 0
        for filename, _modified in candidates[limit:]:
            removed += LasViewerWorkspaceAutosaveStore(self.directory, filename=filename).clear()
        return removed

    def clear(self) -> int:
        removed = 0
        for filename, _modified in self._candidate_files():
            removed += LasViewerWorkspaceAutosaveStore(self.directory, filename=filename).clear()
        return removed

    def _store_for_state(self, state: LasViewerState) -> LasViewerWorkspaceAutosaveStore:
        identity = f"{state.project_id}\0{state.las_id}".encode("utf-8")
        digest = sha256(identity).hexdigest()[:16]
        label = self._slug(state.las_id or state.project_id or "session")[:36]
        filename = f"{self.PREFIX}{label}-{digest}{self.SUFFIX}"
        return LasViewerWorkspaceAutosaveStore(self.directory, filename=filename)

    def _candidate_files(self) -> list[tuple[str, int]]:
        if not self.directory.exists():
            return []
        names: dict[str, int] = {}
        pattern = f"{self.PREFIX}*{self.SUFFIX}"
        for path in self.directory.glob(pattern):
            if not path.is_file():
                continue
            names[path.name] = max(names.get(path.name, 0), path.stat().st_mtime_ns)
        backup_pattern = f"{self.PREFIX}*{self.SUFFIX}.bak"
        for path in self.directory.glob(backup_pattern):
            if not path.is_file():
                continue
            filename = path.name[:-4]
            names[filename] = max(names.get(filename, 0), path.stat().st_mtime_ns)
        return sorted(names.items(), key=lambda item: (-item[1], item[0]))

    @staticmethod
    def _slug(value: str) -> str:
        text = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value or "").strip()).strip("-._")
        return text or "session"
