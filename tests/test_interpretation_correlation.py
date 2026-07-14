from __future__ import annotations

import json
from pathlib import Path

import pytest

from projects.interpretation_correlation import (
    CorrelationEndpoint, CorrelationWorkspaceRepository, CorrelationWorkspaceService,
    discover_published_interpretations, export_correlation_csv, export_correlation_json,
)
from projects.interpretation_intervals import create_interpretation_interval
from projects.interpretation_publication import InterpretationPublicationRepository
from projects.interpretation_revisions import InterpretationRevisionRepository


def _publish(root: Path, project: str, well: str, interpretation: str, top: float):
    interval = create_interpretation_interval(root=root, project_id=project, well_id=well, interpretation_id=interpretation, label=f"Horizon {well}", top=top, base=top + 10)
    revisions = InterpretationRevisionRepository(root=root, project_id=project, well_id=well, interpretation_id=interpretation)
    revision = revisions.create(name="Published")
    publication = InterpretationPublicationRepository(root=root, project_id=project, well_id=well, interpretation_id=interpretation)
    publication.transition(to_status="published", action="publish", revision_id=revision.id)
    return interval, revision


def test_discovery_and_correlation_crud(tmp_path: Path):
    left_interval, left_revision = _publish(tmp_path, "p", "w1", "i1", 100)
    right_interval, right_revision = _publish(tmp_path, "p", "w2", "i2", 120)
    inputs = discover_published_interpretations(root=tmp_path, project_id="p")
    assert [item.well_id for item in inputs] == ["w1", "w2"]

    repo = CorrelationWorkspaceRepository(root=tmp_path, project_id="p")
    workspace = repo.create(name="Field correlation")
    service = CorrelationWorkspaceService(root=tmp_path, project_id="p", workspace_id=workspace.id)
    updated = service.add_tie(
        left=CorrelationEndpoint("w1", "i1", left_revision.id, left_interval.id, 105, left_interval.label),
        right=CorrelationEndpoint("w2", "i2", right_revision.id, right_interval.id, 125, right_interval.label),
        expected_state_token=workspace.state_token,
    )
    assert len(updated.ties) == 1
    assert updated.wells == ("w1", "w2")
    assert b"Field correlation" in export_correlation_json(updated)
    assert b"left_well" in export_correlation_csv(updated)

    cleaned = service.delete_tie(updated.ties[0].id, expected_state_token=updated.state_token)
    assert cleaned.ties == ()


def test_rejects_same_well_and_stale_state(tmp_path: Path):
    interval, revision = _publish(tmp_path, "p", "w1", "i1", 100)
    repo = CorrelationWorkspaceRepository(root=tmp_path, project_id="p")
    workspace = repo.create(name="Correlation")
    service = CorrelationWorkspaceService(root=tmp_path, project_id="p", workspace_id=workspace.id)
    endpoint = CorrelationEndpoint("w1", "i1", revision.id, interval.id, 105, interval.label)
    with pytest.raises(ValueError, match="разные скважины"):
        service.add_tie(left=endpoint, right=endpoint)

    changed = repo.save(type(workspace)(workspace.id, "Changed", "", (), (), workspace.created_at, workspace.updated_at))
    with pytest.raises(ValueError, match="изменился"):
        repo.save(changed, expected_state_token=workspace.state_token)


def test_ignores_non_published_revision(tmp_path: Path):
    create_interpretation_interval(root=tmp_path, project_id="p", well_id="w", interpretation_id="i", label="A", top=1, base=2)
    InterpretationRevisionRepository(root=tmp_path, project_id="p", well_id="w", interpretation_id="i").create(name="Draft")
    assert discover_published_interpretations(root=tmp_path, project_id="p") == ()
