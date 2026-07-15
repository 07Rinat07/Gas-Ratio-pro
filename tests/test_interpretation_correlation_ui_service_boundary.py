from pathlib import Path


def test_correlation_panel_does_not_construct_workspace_repository_directly() -> None:
    source = Path("ui/interpretation_correlation_panel.py").read_text(encoding="utf-8")

    assert "CorrelationWorkspaceRepository" not in source
    assert "discover_published_interpretations" not in source
    assert "application_service_container(state).correlation" in source
    assert "Repository(" not in source
