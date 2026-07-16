from io import BytesIO

import pytest

from services.las_manager_service import LasManagerService
from services.las_viewer_open_workflow import LasViewerOpenWorkflow


def test_open_real_las_builds_compact_viewer_session(tmp_path):
    result = LasViewerOpenWorkflow(tmp_path).open("project-1", "examples/sample_gas_data.las")

    assert result.depth_curve.upper() in {"DEPT", "DEPTH", "MD"}
    assert result.row_count > 0
    assert result.curve_count > 0
    assert result.viewer_state["las_id"] == result.las_id
    assert result.payload["data_quality"]["raw_dataframe_included"] is False
    serialized = result.to_dict()
    assert serialized["raw_dataframe_included"] is False
    assert "dataframe" not in serialized
    assert len(LasManagerService(tmp_path).list_files("project-1")) == 1


def test_invalid_las_is_rejected_without_storage_mutation(tmp_path):
    source = BytesIO(b"~Version\nVERS. 2.0\n~Curve\nDEPT.M\n")
    source.name = "broken.las"

    with pytest.raises(ValueError, match="ASCII"):
        LasViewerOpenWorkflow(tmp_path).open("project-1", source)

    assert LasManagerService(tmp_path).list_files("project-1") == ()


def test_missing_depth_channel_is_rejected_and_rolled_back(tmp_path):
    source = BytesIO(
        b"~Version\nVERS. 2.0\n~Well\nNULL. -999.25\n~Curve\nGR.API\nRT.OHMM\n~ASCII\n10 20\n11 21\n"
    )
    source.name = "no-depth.las"

    with pytest.raises(ValueError, match="depth channel"):
        LasViewerOpenWorkflow(tmp_path).open("project-1", source)

    assert LasManagerService(tmp_path).list_files("project-1") == ()


def test_non_las_extension_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="only .las"):
        LasViewerOpenWorkflow(tmp_path).open("project-1", BytesIO(b"x"), file_name="data.txt")


def test_open_result_exposes_localized_dataset_messages(tmp_path):
    from services.localization_application_service import LocalizationApplicationService
    i18n = LocalizationApplicationService(catalogs_dir="resources/i18n", language="en")
    result = LasViewerOpenWorkflow(tmp_path).open(
        "project-1", "examples/sample_gas_data.las", translate=i18n.translate
    )
    assert result.dataset_messages
    assert "registered" in result.dataset_messages[0].lower() or "imported" in result.dataset_messages[0].lower()
    assert result.to_dict()["dataset_messages"] == list(result.dataset_messages)
