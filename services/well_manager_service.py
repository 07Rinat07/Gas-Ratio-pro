from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from wells.repository import (
    DEFAULT_WELLS_ROOT,
    WellRecord,
    delete_well_record,
    delete_well_version,
    list_wells,
    load_well_record,
    read_well_file_bytes,
    save_well_version,
)


@dataclass(frozen=True)
class WellSaveResult:
    """Result of saving a well version through the service layer."""

    record: WellRecord


@dataclass(frozen=True)
class WellDeleteResult:
    """Result of deleting a complete well from persistent storage."""

    well_id: str
    deleted: bool


@dataclass(frozen=True)
class WellVersionDeleteResult:
    """Result of deleting one version from a saved well."""

    well_id: str
    version_id: str
    deleted: bool
    well_deleted: bool
    remaining_versions: int
    record: WellRecord | None = None


class WellManagerService:
    """High-level well manager used by UI/controllers.

    Streamlit UI should not call the well repository directly for save/delete
    workflows. This service centralizes persistent well operations and returns
    explicit results that the UI can use for cleanup and user feedback.
    """

    def __init__(self, root: Path | str = DEFAULT_WELLS_ROOT) -> None:
        self.root = Path(root)

    def list_wells(self) -> tuple[WellRecord, ...]:
        return list_wells(self.root)

    def count_wells(self) -> int:
        return len(self.list_wells())

    def load_well(self, well_id: str) -> WellRecord:
        return load_well_record(self.root, well_id)

    def read_file_bytes(self, well_id: str, version_id: str, file_key: str) -> bytes:
        return read_well_file_bytes(self.root, well_id, version_id, file_key)

    def save_version(
        self,
        df: pd.DataFrame,
        *,
        well_name: str = "",
        well_id: str | None = None,
        area: str = "",
        status: str = "draft",
        comment: str = "",
        version_label: str = "prepared",
        kind: str = "prepared_las",
        depth_column: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> WellSaveResult:
        record = save_well_version(
            df,
            root=self.root,
            well_name=well_name,
            well_id=well_id,
            area=area,
            status=status,
            comment=comment,
            version_label=version_label,
            kind=kind,
            depth_column=depth_column,
            metadata=metadata,
        )
        return WellSaveResult(record=record)

    def delete_well(self, well_id: str) -> WellDeleteResult:
        deleted = delete_well_record(self.root, well_id)
        return WellDeleteResult(well_id=well_id, deleted=deleted)

    def delete(self, well_id: str) -> WellDeleteResult:
        """Compatibility alias for delete_well()."""

        return self.delete_well(well_id)

    def delete_version(self, well_id: str, version_id: str) -> WellVersionDeleteResult:
        updated_record = delete_well_version(self.root, well_id, version_id)
        remaining_versions = len(updated_record.versions)
        well_deleted = False
        record: WellRecord | None = updated_record

        if remaining_versions == 0:
            # A saved well without versions is not useful in the application UI.
            # Remove its directory so it cannot reappear after a rerun/restart.
            well_deleted = delete_well_record(self.root, well_id)
            record = None

        return WellVersionDeleteResult(
            well_id=well_id,
            version_id=version_id,
            deleted=True,
            well_deleted=well_deleted,
            remaining_versions=remaining_versions,
            record=record,
        )
