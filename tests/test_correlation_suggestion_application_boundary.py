from __future__ import annotations

from pathlib import Path

import pytest

from services.interpretation_correlation_application_service import (
    InterpretationCorrelationApplicationService,
)


def test_ui_does_not_request_correlation_persistence_objects() -> None:
    source = Path("ui/interpretation_correlation_panel.py").read_text(encoding="utf-8")
    assert "suggestion_profile_repository" not in source
    assert "suggestion_acceptance_journal" not in source
    assert "profile_repository." not in source
    assert "acceptance_journal." not in source


def test_profile_store_is_lazy_and_reused(tmp_path: Path) -> None:
    service = InterpretationCorrelationApplicationService(root=tmp_path, project_id="demo")
    assert service.health()["suggestion_profiles_initialized"] is False

    assert service.list_suggestion_profiles() == ()
    first = service._suggestion_profiles
    assert first is not None

    assert service.list_suggestion_profiles() == ()
    assert service._suggestion_profiles is first
    assert service.health()["suggestion_profiles_initialized"] is True


def test_acceptance_journal_rejects_empty_workspace_id(tmp_path: Path) -> None:
    service = InterpretationCorrelationApplicationService(root=tmp_path, project_id="demo")
    with pytest.raises(ValueError, match="Workspace id"):
        service.list_suggestion_acceptances(workspace_id="  ")
