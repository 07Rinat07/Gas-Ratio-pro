from __future__ import annotations

"""Deterministic quality analysis for multi-well interpretation correlation."""

import csv
import io
import json
from dataclasses import asdict, dataclass
from typing import Iterable, Mapping, Sequence

from projects.interpretation_correlation import (
    CorrelationTie,
    CorrelationWorkspace,
    PublishedInterpretationInput,
)

CORRELATION_QUALITY_SCHEMA = "gas-ratio-pro/interpretation-correlation-quality/v1"
QUALITY_SEVERITIES = {"info", "warning", "error"}


@dataclass(frozen=True)
class CorrelationQualityIssue:
    code: str
    severity: str
    message: str
    tie_ids: tuple[str, ...] = ()
    well_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class CorrelationQualitySummary:
    score: int
    status: str
    total_ties: int
    visible_ties: int
    connected_wells: int
    total_wells: int
    duplicate_groups: int
    crossing_pairs: int
    unavailable_endpoints: int
    isolated_wells: int
    issues: tuple[CorrelationQualityIssue, ...]

    @property
    def issue_count(self) -> int:
        return len(self.issues)

    @property
    def error_count(self) -> int:
        return sum(item.severity == "error" for item in self.issues)

    @property
    def warning_count(self) -> int:
        return sum(item.severity == "warning" for item in self.issues)


def _source_key(item: PublishedInterpretationInput) -> tuple[str, str, str]:
    return item.well_id, item.interpretation_id, item.revision_id


def _endpoint_key(tie: CorrelationTie) -> tuple[tuple[str, str], tuple[str, str]]:
    first = (tie.left.well_id, tie.left.interval_id)
    second = (tie.right.well_id, tie.right.interval_id)
    return tuple(sorted((first, second)))  # type: ignore[return-value]


def _ordered_depths(tie: CorrelationTie, well_a: str, well_b: str) -> tuple[float, float]:
    if tie.left.well_id == well_a and tie.right.well_id == well_b:
        return float(tie.left.depth), float(tie.right.depth)
    return float(tie.right.depth), float(tie.left.depth)


def _crossing_pairs(ties: Sequence[CorrelationTie]) -> tuple[tuple[str, str], ...]:
    by_pair: dict[tuple[str, str], list[CorrelationTie]] = {}
    for tie in ties:
        if not tie.visible:
            continue
        pair = tuple(sorted((tie.left.well_id, tie.right.well_id)))
        by_pair.setdefault(pair, []).append(tie)

    crossings: list[tuple[str, str]] = []
    for (well_a, well_b), pair_ties in by_pair.items():
        ordered = sorted(pair_ties, key=lambda item: (_ordered_depths(item, well_a, well_b)[0], item.id))
        for index, first in enumerate(ordered):
            first_a, first_b = _ordered_depths(first, well_a, well_b)
            for second in ordered[index + 1 :]:
                second_a, second_b = _ordered_depths(second, well_a, well_b)
                if first_a == second_a or first_b == second_b:
                    continue
                if (first_a < second_a and first_b > second_b) or (first_a > second_a and first_b < second_b):
                    crossings.append(tuple(sorted((first.id, second.id))))
    return tuple(sorted(set(crossings)))


def analyze_correlation_quality(
    workspace: CorrelationWorkspace,
    sources: Iterable[PublishedInterpretationInput],
) -> CorrelationQualitySummary:
    """Analyze persisted ties without mutating workspace or published inputs."""

    source_map = {_source_key(item): item for item in sources}
    issues: list[CorrelationQualityIssue] = []
    unavailable_count = 0
    connected_wells: set[str] = set()

    for tie in workspace.ties:
        tie_unavailable = False
        for endpoint in (tie.left, tie.right):
            source = source_map.get((endpoint.well_id, endpoint.interpretation_id, endpoint.revision_id))
            if source is None or not any(interval.id == endpoint.interval_id for interval in source.intervals):
                unavailable_count += 1
                tie_unavailable = True
                issues.append(CorrelationQualityIssue(
                    code="unavailable_endpoint",
                    severity="error",
                    message=f"Связь «{tie.name}» использует недоступный опубликованный интервал скважины {endpoint.well_id}.",
                    tie_ids=(tie.id,),
                    well_ids=(endpoint.well_id,),
                ))
        if tie.visible and not tie_unavailable:
            connected_wells.update((tie.left.well_id, tie.right.well_id))

    duplicate_map: dict[tuple[tuple[str, str], tuple[str, str]], list[str]] = {}
    for tie in workspace.ties:
        duplicate_map.setdefault(_endpoint_key(tie), []).append(tie.id)
    duplicate_groups = 0
    for ids in duplicate_map.values():
        if len(ids) > 1:
            duplicate_groups += 1
            issues.append(CorrelationQualityIssue(
                code="duplicate_ties",
                severity="warning",
                message=f"Обнаружены дублирующиеся связи между одинаковыми интервалами: {len(ids)}.",
                tie_ids=tuple(sorted(ids)),
            ))

    crossings = _crossing_pairs(workspace.ties)
    for first_id, second_id in crossings:
        first = next(item for item in workspace.ties if item.id == first_id)
        wells = tuple(sorted((first.left.well_id, first.right.well_id)))
        issues.append(CorrelationQualityIssue(
            code="crossing_ties",
            severity="warning",
            message=f"Связи пересекаются между скважинами {wells[0]} и {wells[1]}.",
            tie_ids=(first_id, second_id),
            well_ids=wells,
        ))

    workspace_wells = set(workspace.wells)
    isolated = tuple(sorted(workspace_wells - connected_wells))
    for well_id in isolated:
        issues.append(CorrelationQualityIssue(
            code="isolated_well",
            severity="warning",
            message=f"Скважина {well_id} не имеет ни одной доступной видимой корреляционной связи.",
            well_ids=(well_id,),
        ))

    if not workspace.ties:
        issues.append(CorrelationQualityIssue(
            code="empty_workspace",
            severity="info",
            message="В корреляционном проекте ещё нет связей.",
            well_ids=tuple(sorted(workspace_wells)),
        ))

    score = 100
    score -= unavailable_count * 20
    score -= duplicate_groups * 8
    score -= len(crossings) * 6
    score -= len(isolated) * 10
    score = max(0, min(100, score))
    status = "good" if score >= 85 else "attention" if score >= 60 else "critical"

    return CorrelationQualitySummary(
        score=score,
        status=status,
        total_ties=len(workspace.ties),
        visible_ties=sum(item.visible for item in workspace.ties),
        connected_wells=len(connected_wells),
        total_wells=len(workspace_wells),
        duplicate_groups=duplicate_groups,
        crossing_pairs=len(crossings),
        unavailable_endpoints=unavailable_count,
        isolated_wells=len(isolated),
        issues=tuple(issues),
    )


def build_correlation_quality_issue_rows(summary: CorrelationQualitySummary) -> list[dict[str, object]]:
    return [
        {
            "severity": issue.severity,
            "code": issue.code,
            "message": issue.message,
            "tie_ids": ", ".join(issue.tie_ids),
            "well_ids": ", ".join(issue.well_ids),
        }
        for issue in summary.issues
    ]


def export_correlation_quality_json(workspace: CorrelationWorkspace, summary: CorrelationQualitySummary) -> bytes:
    payload = {
        "schema": CORRELATION_QUALITY_SCHEMA,
        "workspace_id": workspace.id,
        "workspace_name": workspace.name,
        "workspace_state_token": workspace.state_token,
        "summary": {key: value for key, value in asdict(summary).items() if key != "issues"},
        "issues": [asdict(item) for item in summary.issues],
    }
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def export_correlation_quality_csv(workspace: CorrelationWorkspace, summary: CorrelationQualitySummary) -> bytes:
    stream = io.StringIO(newline="")
    fieldnames = ["workspace_id", "workspace_name", "score", "status", "severity", "code", "message", "tie_ids", "well_ids"]
    writer = csv.DictWriter(stream, fieldnames=fieldnames)
    writer.writeheader()
    rows = build_correlation_quality_issue_rows(summary)
    if not rows:
        rows = [{"severity": "info", "code": "no_issues", "message": "Проблемы качества не обнаружены.", "tie_ids": "", "well_ids": ""}]
    for row in rows:
        writer.writerow({
            "workspace_id": workspace.id,
            "workspace_name": workspace.name,
            "score": summary.score,
            "status": summary.status,
            **row,
        })
    return ("\ufeff" + stream.getvalue()).encode("utf-8")
