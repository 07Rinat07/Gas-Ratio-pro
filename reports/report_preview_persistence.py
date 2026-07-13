from __future__ import annotations

"""Project-scoped persistence for compact report-preview count snapshots.

Only validated JSON metadata is stored. Engineering dataframes, document models,
rendered files, and credentials are never persisted by this repository.
"""

import json
from pathlib import Path
import re
from typing import Any, Mapping

from reports.report_designer import resolve_report_document_counts_snapshot

_SAFE_ID = re.compile(r"[^A-Za-z0-9._-]+")
_FILE_NAME = "report_preview_counts.json"


class ReportPreviewCountsRepository:
    """Persist one compact report-count snapshot per project atomically."""

    def __init__(self, root_dir: Path | str) -> None:
        self.root_dir = Path(root_dir)

    def path_for(self, project_id: str) -> Path:
        safe_id = _SAFE_ID.sub("_", str(project_id or "").strip()).strip("._")
        if not safe_id:
            raise ValueError("project_id is required")
        return self.root_dir / safe_id / _FILE_NAME

    def save(self, project_id: str, payload: Mapping[str, Any]) -> Path:
        """Validate and atomically persist a current schema snapshot."""
        clean_project_id = str(project_id or "").strip()
        if not clean_project_id:
            raise ValueError("project_id is required")
        if not isinstance(payload, Mapping):
            raise ValueError("report preview snapshot must be a mapping")

        signature = str(payload.get("signature") or "").strip()
        resolution = resolve_report_document_counts_snapshot(
            payload,
            expected_signature=signature,
        )
        if resolution.state != "current" or resolution.counts is None:
            raise ValueError(f"invalid report preview snapshot: {resolution.state}")

        target = self.path_for(clean_project_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(target)
        return target

    def load(self, project_id: str) -> dict[str, Any] | None:
        """Load raw JSON metadata; context validation remains the caller's job."""
        target = self.path_for(project_id)
        if not target.exists():
            return None
        payload = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("invalid report preview snapshot payload")
        return payload

    def delete(self, project_id: str) -> bool:
        target = self.path_for(project_id)
        if not target.exists():
            return False
        target.unlink()
        return True
