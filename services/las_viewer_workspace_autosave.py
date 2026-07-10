"""Atomic autosave and recovery for compact LAS Viewer workspace state.

The store persists only :class:`LasViewerState`. Raw LAS samples, render models,
and caches remain outside the autosave contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Mapping

from services.las_viewer_session import LasViewerSession, LasViewerState


@dataclass(frozen=True, slots=True)
class LasViewerAutosaveResult:
    written: bool
    recovered: bool
    path: str = ""
    checksum_sha256: str = ""
    used_backup: bool = False
    reason: str = ""
    state: LasViewerState | None = None


class LasViewerWorkspaceAutosaveStore:
    """Persist one recoverable LAS Viewer state with a single backup copy."""

    SCHEMA = "gas-ratio-pro/las-viewer-autosave"
    VERSION = "1.0"

    def __init__(self, directory: str | os.PathLike[str], *, filename: str = "las-viewer.autosave.json") -> None:
        self.directory = Path(directory).expanduser()
        name = str(filename or "").strip()
        if not name or Path(name).name != name:
            raise ValueError("autosave filename must be a simple file name")
        self.path = self.directory / name
        self.backup_path = self.directory / f"{name}.bak"

    def save(self, session: LasViewerSession) -> LasViewerAutosaveResult:
        state = session.state
        envelope = self._envelope(state)
        content = self._canonical_bytes(envelope)
        checksum = sha256(content).hexdigest()

        current_checksum = self._file_checksum(self.path)
        if current_checksum == checksum:
            return LasViewerAutosaveResult(
                written=False,
                recovered=False,
                path=str(self.path),
                checksum_sha256=checksum,
                reason="unchanged",
                state=state,
            )

        self.directory.mkdir(parents=True, exist_ok=True)
        temporary = self._write_temporary(content)
        try:
            if self.path.exists():
                os.replace(self.path, self.backup_path)
            os.replace(temporary, self.path)
        finally:
            Path(temporary).unlink(missing_ok=True)

        return LasViewerAutosaveResult(
            written=True,
            recovered=False,
            path=str(self.path),
            checksum_sha256=checksum,
            state=state,
        )

    def recover(
        self,
        *,
        project_id: str = "",
        las_id: str = "",
    ) -> LasViewerAutosaveResult:
        errors: list[str] = []
        for candidate, used_backup in ((self.path, False), (self.backup_path, True)):
            if not candidate.exists():
                continue
            try:
                state, checksum = self._load_state(candidate)
                self._validate_context(state, project_id=project_id, las_id=las_id)
                return LasViewerAutosaveResult(
                    written=False,
                    recovered=True,
                    path=str(candidate),
                    checksum_sha256=checksum,
                    used_backup=used_backup,
                    state=state,
                )
            except ValueError as exc:
                errors.append(f"{candidate.name}:{exc}")

        reason = "missing_autosave" if not errors else "invalid_autosave:" + ";".join(errors)
        return LasViewerAutosaveResult(False, False, reason=reason)

    def recover_session(self, *, project_id: str = "", las_id: str = "") -> LasViewerSession | None:
        result = self.recover(project_id=project_id, las_id=las_id)
        if not result.recovered or result.state is None:
            return None
        return LasViewerSession.from_state(result.state)

    def clear(self) -> int:
        removed = 0
        for candidate in (self.path, self.backup_path):
            if candidate.exists():
                candidate.unlink()
                removed += 1
        return removed

    def _envelope(self, state: LasViewerState) -> dict[str, Any]:
        payload = state.to_dict()
        return {
            "schema": self.SCHEMA,
            "version": self.VERSION,
            "content_type": "las-viewer-state",
            "state": payload,
            "state_checksum_sha256": sha256(self._canonical_bytes(payload)).hexdigest(),
        }

    def _load_state(self, source: Path) -> tuple[LasViewerState, str]:
        try:
            content = source.read_bytes()
            raw = json.loads(content.decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("not_valid_utf8_json") from exc
        if not isinstance(raw, Mapping):
            raise ValueError("root_not_object")
        if raw.get("schema") != self.SCHEMA or str(raw.get("version") or "") != self.VERSION:
            raise ValueError("unsupported_schema")
        state_payload = raw.get("state")
        if not isinstance(state_payload, Mapping):
            raise ValueError("missing_state")
        expected = str(raw.get("state_checksum_sha256") or "")
        actual = sha256(self._canonical_bytes(state_payload)).hexdigest()
        if not expected or expected != actual:
            raise ValueError("checksum_mismatch")
        try:
            state = LasViewerState.from_dict(state_payload)
        except (TypeError, ValueError, KeyError) as exc:
            raise ValueError("invalid_state") from exc
        return state, sha256(content).hexdigest()

    @staticmethod
    def _validate_context(state: LasViewerState, *, project_id: str, las_id: str) -> None:
        expected_project = str(project_id or "").strip()
        expected_las = str(las_id or "").strip()
        if expected_project and state.project_id and state.project_id != expected_project:
            raise ValueError("project_mismatch")
        if expected_las and state.las_id != expected_las:
            raise ValueError("las_mismatch")

    def _write_temporary(self, content: bytes) -> str:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=f".{self.path.name}.",
            suffix=".tmp",
            dir=self.directory,
            delete=False,
        ) as temporary:
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
            return temporary.name

    @staticmethod
    def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
        return (
            json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
            + "\n"
        ).encode("utf-8")

    @staticmethod
    def _file_checksum(path: Path) -> str:
        try:
            return sha256(path.read_bytes()).hexdigest()
        except OSError:
            return ""
