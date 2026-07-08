from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from wells.repository import (
    DEFAULT_WELLS_ROOT,
    WellRecord,
    delete_well_record,
    delete_well_version,
    list_wells,
    read_well_file_bytes,
    save_well_version,
)


class WellManagerService:
    """Application service for saved well records and versions."""

    def __init__(self, root: Path | str = DEFAULT_WELLS_ROOT) -> None:
        self.root = Path(root)

    def list_wells(self) -> tuple[WellRecord, ...]:
        return list_wells(self.root)

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
    ) -> WellRecord:
        return save_well_version(
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

    def delete_version(self, well_id: str, version_id: str) -> WellRecord | None:
        updated = delete_well_version(self.root, well_id, version_id)
        if not updated.versions:
            delete_well_record(self.root, well_id)
            return None
        return updated

    def delete_well(self, well_id: str) -> bool:
        return delete_well_record(self.root, well_id)

    def clear_all_wells(self) -> int:
        records = self.list_wells()
        deleted = 0
        for record in records:
            if delete_well_record(self.root, record.id):
                deleted += 1
        return deleted
