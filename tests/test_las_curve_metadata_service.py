from __future__ import annotations

from services.las_curve_metadata_service import LasCurveMetadataService
from services.las_manager_service import LasManagerService
from tests.test_las_manager_service import SIMPLE_LAS


def test_las_curve_metadata_service_returns_renderer_safe_summary(tmp_path):
    manager = LasManagerService(tmp_path)
    record = manager.save_file(
        project_id="demo",
        data=SIMPLE_LAS,
        file_name="demo.las",
        well_name="Demo Well",
        version_label="raw",
    ).record

    summary = LasCurveMetadataService(tmp_path).summarize("demo", record.id).to_dict()

    assert summary["project_id"] == "demo"
    assert summary["las_id"] == record.id
    assert summary["well_name"] == "Demo Well"
    assert summary["curve_count"] == 2
    assert summary["row_count"] == 2
    assert summary["depth_curve"] == "DEPT"
    assert summary["depth_range"] == {"start": 1000.0, "stop": 1000.5, "step": 0.5}
    assert summary["curves"][0]["mnemonic"] == "DEPT"
    assert summary["curves"][0]["unit"] == "M"
    assert "curves" in summary
