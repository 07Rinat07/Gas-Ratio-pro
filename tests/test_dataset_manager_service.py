from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pandas as pd

from services.dataset_manager_service import DatasetManagerService
from projects.datasets import save_project_mud_log_dataset, list_project_mud_log_datasets


def _xlsx_bytes() -> bytes:
    buffer = BytesIO()
    pd.DataFrame({"DEPTH": [1000.0, 1001.0], "C1": [1.0, 2.0]}).to_excel(buffer, index=False)
    return buffer.getvalue()


def test_dataset_manager_service_clears_mud_log_section(tmp_path: Path) -> None:
    project_id = "demo"
    save_project_mud_log_dataset(
        data=_xlsx_bytes(),
        root=tmp_path,
        project_id=project_id,
        file_name="Geo_total_KB1.xlsx",
        name="Geo total",
    )
    assert len(list_project_mud_log_datasets(tmp_path, project_id)) == 1

    result = DatasetManagerService(tmp_path).clear_section(project_id, "Mud Log")

    assert result.deleted_count == 1
    assert result.diagnostic == "Удалено записей: 1."
    assert list_project_mud_log_datasets(tmp_path, project_id) == ()


def test_dataset_manager_audit_and_orphan_cleanup(tmp_path: Path) -> None:
    project_id = "demo"
    service = DatasetManagerService(tmp_path)
    orphan = service.section_dir(project_id, "mud_log") / "interrupted-import"
    orphan.mkdir(parents=True, exist_ok=True)
    (orphan / "source.csv").write_text("DEPTH,C1\n1000,1\n", encoding="utf-8")

    audit = service.audit_section(project_id, "mud_log")

    assert audit.active_records == 0
    assert audit.archived_records == 0
    assert audit.orphan_directories == ("interrupted-import",)
    assert audit.needs_cleanup is True

    result = service.clear_orphan_directories(project_id, "mud_log")

    assert result.deleted == 1
    assert not orphan.exists()


def test_dataset_manager_purges_only_archived_records(tmp_path: Path) -> None:
    from dataclasses import replace
    from projects import datasets as project_datasets

    project_id = "demo"
    first = save_project_mud_log_dataset(
        data=_xlsx_bytes(),
        root=tmp_path,
        project_id=project_id,
        file_name="active.xlsx",
        name="Active",
    )
    second = save_project_mud_log_dataset(
        data=_xlsx_bytes(),
        root=tmp_path,
        project_id=project_id,
        file_name="archived.xlsx",
        name="Archived",
    )
    records = project_datasets.list_project_mud_log_records(tmp_path, project_id, include_archived=True)
    archived_records = tuple(
        replace(item, archived_at="2026-07-12T00:00:00Z") if item.id == second.id else item
        for item in records
    )
    project_datasets._write_mud_log_manifest(tmp_path, project_id, archived_records)

    service = DatasetManagerService(tmp_path)
    audit = service.audit_section(project_id, "mud_log")
    assert audit.active_records == 1
    assert audit.archived_records == 1

    result = service.purge_archived(project_id, "mud_log")

    assert result.deleted == 1
    remaining = project_datasets.list_project_mud_log_records(tmp_path, project_id, include_archived=True)
    assert [item.id for item in remaining] == [first.id]
