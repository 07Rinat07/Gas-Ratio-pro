from pathlib import Path

from las_correlation.settings import LasCorrelationSettings
from services.interpretation_workspace_application_service import (
    InterpretationWorkspaceApplicationService,
)
from services.las_workspace_application_service import LasWorkspaceApplicationService


def test_las_workspace_roundtrips_project_correlation_settings(tmp_path: Path):
    service = LasWorkspaceApplicationService(root=tmp_path, project_id="project-a")
    settings = LasCorrelationSettings()

    assert service.load_correlation_settings() is None
    service.save_correlation_settings(settings)

    assert service.load_correlation_settings() == settings


def test_las_workspace_rejects_invalid_correlation_settings(tmp_path: Path):
    service = LasWorkspaceApplicationService(root=tmp_path, project_id="project-a")

    try:
        service.save_correlation_settings(object())
    except TypeError as exc:
        assert "LasCorrelationSettings" in str(exc)
    else:
        raise AssertionError("invalid settings must be rejected")


def test_interpretation_workspace_owns_interval_listing_and_display_settings(tmp_path: Path):
    state = {}
    service = InterpretationWorkspaceApplicationService(root=tmp_path, project_id="project-a")

    assert service.list_intervals(
        state=state, well_id="well-1", interpretation_id="default"
    ) == ()

    defaults = service.load_display_settings(
        well_id="well-1", interpretation_id="default"
    )
    assert defaults.visible is True

    saved = service.save_display_settings(
        well_id="well-1",
        interpretation_id="default",
        visible=False,
        opacity=0.33,
    )
    loaded = service.load_display_settings(
        well_id="well-1", interpretation_id="default"
    )
    assert loaded == saved
    assert loaded.visible is False
    assert loaded.opacity == 0.33


def test_streamlit_ui_does_not_import_project_settings_persistence():
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")

    assert "InterpretationIntervalManager" not in source
    assert "interval_display_settings." not in source
    assert "load_project_correlation_settings(" not in source
    assert "save_project_correlation_settings(" not in source
