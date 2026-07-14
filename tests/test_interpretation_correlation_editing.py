from __future__ import annotations

from pathlib import Path

import pytest

from projects.interpretation_correlation import (
    CorrelationEndpoint,
    CorrelationWorkspaceRepository,
    CorrelationWorkspaceService,
    discover_published_interpretations,
)
from projects.interpretation_correlation_chart import build_correlation_figure, export_correlation_svg
from projects.interpretation_correlation_commands import (
    CorrelationHistoryConflict,
    CorrelationWorkspaceCommandService,
)
from projects.interpretation_intervals import create_interpretation_interval
from projects.interpretation_publication import InterpretationPublicationRepository
from projects.interpretation_revisions import InterpretationRevisionRepository


def _publish(root: Path, well: str, top: float):
    interval = create_interpretation_interval(
        root=root, project_id="p", well_id=well, interpretation_id="main",
        label=f"H-{well}", top=top, base=top + 20,
    )
    revision = InterpretationRevisionRepository(
        root=root, project_id="p", well_id=well, interpretation_id="main"
    ).create(name=f"Published {well}")
    InterpretationPublicationRepository(
        root=root, project_id="p", well_id=well, interpretation_id="main"
    ).transition(to_status="published", action="publish", revision_id=revision.id)
    return interval, revision


def _commands(root: Path):
    left, left_revision = _publish(root, "w1", 100)
    right, right_revision = _publish(root, "w2", 120)
    repo = CorrelationWorkspaceRepository(root=root, project_id="p")
    workspace = repo.create(name="Editable")
    state: dict = {}
    commands = CorrelationWorkspaceCommandService(
        state, root=root, project_id="p", workspace_id=workspace.id
    )
    workspace = commands.add_tie(
        left=CorrelationEndpoint("w1", "main", left_revision.id, left.id, 110, left.label),
        right=CorrelationEndpoint("w2", "main", right_revision.id, right.id, 130, right.label),
        name="Marker",
    )
    return repo, commands, state, workspace


def test_update_tie_style_depth_and_backward_compatible_defaults(tmp_path: Path):
    repo, commands, _, workspace = _commands(tmp_path)
    tie = workspace.ties[0]
    updated = commands.update_tie(
        tie.id, left_depth=112, right_depth=128, name="Updated", note="reviewed",
        color="#AA3300", width=4.5, dash="dashdot", visible=False,
    )
    changed = updated.ties[0]
    assert changed.left.depth == 112
    assert changed.right.depth == 128
    assert (changed.name, changed.note) == ("Updated", "reviewed")
    assert (changed.color, changed.width, changed.dash, changed.visible) == ("#AA3300", 4.5, "dashdot", False)

    payload = repo.directory.joinpath(workspace.id, "correlation.json").read_text(encoding="utf-8")
    assert '"dash": "dashdot"' in payload


def test_undo_redo_and_batch_delete_are_single_commands(tmp_path: Path):
    repo, commands, _, workspace = _commands(tmp_path)
    first = workspace.ties[0]
    workspace = commands.add_tie(left=first.left, right=first.right, name="Second")
    ids = tuple(item.id for item in workspace.ties)
    deleted = commands.delete_ties(ids)
    assert deleted.ties == ()
    assert commands.undo() is True
    assert len(repo.get(workspace.id).ties) == 2
    assert commands.redo() is True
    assert repo.get(workspace.id).ties == ()


def test_undo_rejects_external_changes(tmp_path: Path):
    repo, commands, _, workspace = _commands(tmp_path)
    tie = workspace.ties[0]
    commands.update_tie(tie.id, note="history")
    current = repo.get(workspace.id)
    external = type(current)(
        current.id, "External", current.description, current.wells, current.ties,
        current.created_at, current.updated_at,
    )
    repo.save(external)
    with pytest.raises(CorrelationHistoryConflict, match="вне истории"):
        commands.undo()


def test_hidden_tie_is_excluded_and_style_is_rendered(tmp_path: Path):
    repo, commands, _, workspace = _commands(tmp_path)
    tie = workspace.ties[0]
    workspace = commands.update_tie(tie.id, color="#112233", width=5.0, dash="dot")
    sources = discover_published_interpretations(root=tmp_path, project_id="p")
    figure = build_correlation_figure(workspace, sources)
    tie_trace = next(trace for trace in figure.data if trace.name == "Marker")
    assert tie_trace.line.color == "#112233"
    assert tie_trace.line.width == 5.0
    assert tie_trace.line.dash == "dot"
    assert b'#112233' in export_correlation_svg(workspace, sources)

    workspace = commands.update_tie(tie.id, visible=False)
    figure = build_correlation_figure(workspace, sources)
    assert all(trace.name != "Marker" for trace in figure.data)


def test_persistent_operation_journal_is_bounded_and_serializable(tmp_path: Path):
    _, commands, _, workspace = _commands(tmp_path)
    tie = workspace.ties[0]
    commands.update_tie(tie.id, note="one")
    commands.update_tie(tie.id, note="two")
    rows = commands.journal.list()
    assert [item["action"] for item in rows] == ["add_tie", "update_tie", "update_tie"]
    assert rows[-1]["tie_count_before"] == 1
    assert rows[-1]["tie_count_after"] == 1
    assert commands.journal.path.exists()
