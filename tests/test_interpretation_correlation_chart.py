from __future__ import annotations

from pathlib import Path

import pytest

from projects.interpretation_correlation import CorrelationEndpoint, CorrelationWorkspaceRepository, CorrelationWorkspaceService, discover_published_interpretations
from projects.interpretation_correlation_chart import CorrelationChartSettings, build_correlation_figure, build_correlation_payload, export_correlation_svg
from projects.interpretation_intervals import create_interpretation_interval
from projects.interpretation_publication import InterpretationPublicationRepository
from projects.interpretation_revisions import InterpretationRevisionRepository


def _publish(root: Path, well: str, top: float, color: str):
    interval = create_interpretation_interval(root=root, project_id="p", well_id=well, interpretation_id="main", label=f"H-{well}", top=top, base=top + 12, color=color)
    revision = InterpretationRevisionRepository(root=root, project_id="p", well_id=well, interpretation_id="main").create(name=f"Published {well}")
    InterpretationPublicationRepository(root=root, project_id="p", well_id=well, interpretation_id="main").transition(to_status="published", action="publish", revision_id=revision.id)
    return interval, revision


def _workspace(root: Path):
    left, left_revision = _publish(root, "w1", 100, "#FF0000")
    right, right_revision = _publish(root, "w2", 125, "#00AA00")
    repo = CorrelationWorkspaceRepository(root=root, project_id="p")
    workspace = repo.create(name="Cross section")
    service = CorrelationWorkspaceService(root=root, project_id="p", workspace_id=workspace.id)
    workspace = service.add_tie(
        left=CorrelationEndpoint("w1", "main", left_revision.id, left.id, 106, left.label),
        right=CorrelationEndpoint("w2", "main", right_revision.id, right.id, 131, right.label),
        name="Marker A", expected_state_token=workspace.state_token,
    )
    return workspace, discover_published_interpretations(root=root, project_id="p")


def test_builds_multi_well_figure_and_svg(tmp_path: Path):
    workspace, sources = _workspace(tmp_path)
    figure = build_correlation_figure(workspace, sources)
    assert len(figure.data) >= 5
    assert list(figure.layout.xaxis.ticktext) == ["w1", "w2"]
    assert figure.layout.yaxis.range[0] > figure.layout.yaxis.range[1]
    svg = export_correlation_svg(workspace, sources)
    assert svg.startswith(b"<svg")
    assert b"Marker A" in svg
    assert b"Cross section" in svg


def test_depth_window_clips_intervals_and_filters_ties(tmp_path: Path):
    workspace, sources = _workspace(tmp_path)
    payload, normalized = build_correlation_payload(workspace, sources, settings=CorrelationChartSettings(depth_min=102, depth_max=120))
    assert normalized.depth_min == 102
    assert normalized.depth_max == 120
    assert payload.visible_ties == workspace.ties
    figure = build_correlation_figure(workspace, sources, settings=normalized)
    assert figure.layout.yaxis.range == (120, 102)


def test_rejects_invalid_depth_window(tmp_path: Path):
    workspace, sources = _workspace(tmp_path)
    with pytest.raises(ValueError, match="диапазон"):
        build_correlation_payload(workspace, sources, settings=CorrelationChartSettings(depth_min=130, depth_max=120))
