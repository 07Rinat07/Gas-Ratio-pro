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
