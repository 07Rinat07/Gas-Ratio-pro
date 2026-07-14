from __future__ import annotations

import json
from dataclasses import replace

from projects.interpretation_correlation import (
    CorrelationEndpoint,
    CorrelationTie,
    CorrelationWorkspace,
    PublishedInterpretationInput,
)
from projects.interpretation_correlation_quality import (
    analyze_correlation_quality,
    build_correlation_quality_issue_rows,
    export_correlation_quality_csv,
    export_correlation_quality_json,
)
from projects.interpretation_intervals import InterpretationInterval, build_interpretation_interval


def _interval(interval_id: str, top: float, base: float) -> InterpretationInterval:
    return build_interpretation_interval(interval_id=interval_id, top=top, base=base, label=interval_id)


def _source(well: str, interval: InterpretationInterval) -> PublishedInterpretationInput:
    return PublishedInterpretationInput(well, "main", f"rev-{well}", "Published", "2026-07-14", (interval,), "token")


def _endpoint(well: str, interval: InterpretationInterval, depth: float) -> CorrelationEndpoint:
    return CorrelationEndpoint(well, "main", f"rev-{well}", interval.id, depth, interval.label)


def _tie(tie_id: str, left: CorrelationEndpoint, right: CorrelationEndpoint, *, visible: bool = True) -> CorrelationTie:
    return CorrelationTie(tie_id, left, right, tie_id, "", visible=visible)


def _workspace(*ties: CorrelationTie, wells=("A", "B")) -> CorrelationWorkspace:
    return CorrelationWorkspace("11111111-1111-4111-8111-111111111111", "QC", "", tuple(wells), tuple(ties), "now", "now")


def test_quality_good_workspace_has_full_score() -> None:
    a1, b1 = _interval("11111111-1111-4111-8111-111111111112", 100, 110), _interval("22222222-2222-4222-8222-222222222222", 120, 130)
    summary = analyze_correlation_quality(_workspace(_tie("33333333-3333-4333-8333-333333333333", _endpoint("A", a1, 105), _endpoint("B", b1, 125))), (_source("A", a1), _source("B", b1)))
    assert summary.score == 100
    assert summary.status == "good"
    assert summary.issues == ()


def test_quality_detects_duplicate_crossing_and_isolated_well() -> None:
    a1 = _interval("11111111-1111-4111-8111-111111111112", 100, 110)
    a2 = _interval("11111111-1111-4111-8111-111111111113", 120, 130)
    b1 = _interval("22222222-2222-4222-8222-222222222222", 200, 210)
    b2 = _interval("22222222-2222-4222-8222-222222222223", 180, 190)
    t1 = _tie("33333333-3333-4333-8333-333333333331", _endpoint("A", a1, 105), _endpoint("B", b1, 205))
    duplicate = _tie("33333333-3333-4333-8333-333333333332", _endpoint("A", a1, 106), _endpoint("B", b1, 206))
    crossing = _tie("33333333-3333-4333-8333-333333333333", _endpoint("A", a2, 125), _endpoint("B", b2, 185))
    sources = (_source("A", a1), replace(_source("A", a2), revision_id="rev-A2"), _source("B", b1), replace(_source("B", b2), revision_id="rev-B2"))
    # endpoints must refer to matching source revisions
    crossing = replace(crossing, left=replace(crossing.left, revision_id="rev-A2"), right=replace(crossing.right, revision_id="rev-B2"))
    summary = analyze_correlation_quality(_workspace(t1, duplicate, crossing, wells=("A", "B", "C")), sources)
    codes = {item.code for item in summary.issues}
    assert {"duplicate_ties", "crossing_ties", "isolated_well"}.issubset(codes)
    assert summary.duplicate_groups == 1
    assert summary.crossing_pairs >= 1
    assert summary.isolated_wells == 1
    assert summary.score < 100


def test_quality_detects_unavailable_endpoint_and_ignores_hidden_connectivity() -> None:
    a1, b1 = _interval("11111111-1111-4111-8111-111111111112", 100, 110), _interval("22222222-2222-4222-8222-222222222222", 120, 130)
    missing = replace(_endpoint("B", b1, 125), revision_id="missing")
    summary = analyze_correlation_quality(_workspace(_tie("33333333-3333-4333-8333-333333333333", _endpoint("A", a1, 105), missing, visible=False)), (_source("A", a1), _source("B", b1)))
    assert summary.unavailable_endpoints == 1
    assert summary.connected_wells == 0
    assert summary.error_count == 1


def test_quality_exports_are_deterministic_and_include_workspace_context() -> None:
    a1, b1 = _interval("11111111-1111-4111-8111-111111111112", 100, 110), _interval("22222222-2222-4222-8222-222222222222", 120, 130)
    workspace = _workspace(_tie("33333333-3333-4333-8333-333333333333", _endpoint("A", a1, 105), _endpoint("B", b1, 125)))
    summary = analyze_correlation_quality(workspace, (_source("A", a1), _source("B", b1)))
    payload = json.loads(export_correlation_quality_json(workspace, summary))
    assert payload["workspace_id"] == workspace.id
    assert payload["summary"]["score"] == 100
    csv_text = export_correlation_quality_csv(workspace, summary).decode("utf-8-sig")
    assert "workspace_id" in csv_text and "no_issues" in csv_text
    assert build_correlation_quality_issue_rows(summary) == []
