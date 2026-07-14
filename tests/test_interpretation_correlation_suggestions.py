from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from projects.interpretation_correlation import (
    CorrelationTie,
    CorrelationWorkspace,
    CorrelationWorkspaceRepository,
    PublishedInterpretationInput,
)
from projects.interpretation_correlation_commands import CorrelationWorkspaceCommandService
from projects.interpretation_correlation_suggestions import (
    build_correlation_suggestions,
    suggestion_preview_from_dict,
    validate_suggestion_preview,
)
from projects.interpretation_intervals import build_interpretation_interval


def _interval(interval_id: str, label: str, top: float, interval_type: str = "reservoir"):
    return build_interpretation_interval(
        interval_id=interval_id, label=label, top=top, base=top + 10,
        interval_type=interval_type,
    )


def _source(well: str, *intervals):
    return PublishedInterpretationInput(
        well, "main", f"rev-{well}", f"Published {well}", "2026-07-14",
        tuple(intervals), f"token-{well}",
    )


def _workspace() -> CorrelationWorkspace:
    return CorrelationWorkspace(
        "11111111-1111-4111-8111-111111111111", "Auto", "", (), (), "now", "now"
    )


def test_suggestions_prioritize_matching_type_label_and_depth() -> None:
    left = _interval("11111111-1111-4111-8111-111111111112", "Sand A", 100)
    strong = _interval("22222222-2222-4222-8222-222222222222", "Sand A", 104)
    weak = _interval("22222222-2222-4222-8222-222222222223", "Other", 105, "seal")
    preview = build_correlation_suggestions(_workspace(), (_source("A", left), _source("B", strong, weak)))
    assert len(preview.suggestions) == 1
    candidate = preview.suggestions[0]
    assert candidate.right.interval_id == strong.id
    assert candidate.type_match is True
    assert candidate.label_match is True
    assert candidate.confidence >= 0.9


def test_existing_tie_is_not_suggested_again() -> None:
    left = _interval("11111111-1111-4111-8111-111111111112", "Sand", 100)
    right = _interval("22222222-2222-4222-8222-222222222222", "Sand", 102)
    initial = build_correlation_suggestions(_workspace(), (_source("A", left), _source("B", right)))
    suggestion = initial.suggestions[0]
    tie = CorrelationTie("33333333-3333-4333-8333-333333333333", suggestion.left, suggestion.right, "Existing", "")
    workspace = replace(_workspace(), ties=(tie,), wells=("A", "B"))
    assert build_correlation_suggestions(workspace, (_source("A", left), _source("B", right))).suggestions == ()


def test_preview_roundtrip_and_stale_validation() -> None:
    from dataclasses import asdict
    left = _interval("11111111-1111-4111-8111-111111111112", "Sand", 100)
    right = _interval("22222222-2222-4222-8222-222222222222", "Sand", 102)
    sources = (_source("A", left), _source("B", right))
    workspace = _workspace()
    preview = suggestion_preview_from_dict(asdict(build_correlation_suggestions(workspace, sources)))
    validate_suggestion_preview(preview, workspace, sources)
    with pytest.raises(ValueError, match="источники изменились"):
        validate_suggestion_preview(preview, workspace, (sources[0], replace(sources[1], state_token="changed")))


def test_batch_add_is_single_undoable_command(tmp_path: Path, monkeypatch) -> None:
    left = _interval("11111111-1111-4111-8111-111111111112", "Sand", 100)
    right = _interval("22222222-2222-4222-8222-222222222222", "Sand", 102)
    sources = (_source("A", left), _source("B", right))
    repo = CorrelationWorkspaceRepository(root=tmp_path, project_id="p")
    workspace = repo.create(name="Auto")
    preview = build_correlation_suggestions(workspace, sources)
    monkeypatch.setattr("projects.interpretation_correlation.discover_published_interpretations", lambda **_: sources)
    candidate = preview.suggestions[0]
    commands = CorrelationWorkspaceCommandService({}, root=tmp_path, project_id="p", workspace_id=workspace.id)
    updated = commands.add_ties((CorrelationTie("", candidate.left, candidate.right, "Suggested", ""),))
    assert len(updated.ties) == 1
    assert commands.history_status()["undo_count"] == 1
    assert commands.undo() is True
    assert repo.get(workspace.id).ties == ()
