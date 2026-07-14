from __future__ import annotations

"""Deterministic candidate generation for multi-well correlation ties."""

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Iterable, Sequence

from projects.interpretation_correlation import (
    CorrelationEndpoint,
    CorrelationTie,
    CorrelationWorkspace,
    PublishedInterpretationInput,
)

SUGGESTION_SCHEMA = "gas-ratio-pro/interpretation-correlation-suggestions/v1"


@dataclass(frozen=True)
class CorrelationSuggestion:
    id: str
    left: CorrelationEndpoint
    right: CorrelationEndpoint
    confidence: float
    reason: str
    depth_delta: float
    type_match: bool
    label_match: bool


@dataclass(frozen=True)
class CorrelationSuggestionPreview:
    schema: str
    workspace_id: str
    workspace_state_token: str
    source_state_token: str
    suggestions: tuple[CorrelationSuggestion, ...]


def _norm(value: str) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def _source_token(sources: Sequence[PublishedInterpretationInput]) -> str:
    payload = [
        {
            "well_id": item.well_id,
            "interpretation_id": item.interpretation_id,
            "revision_id": item.revision_id,
            "state_token": item.state_token,
            "intervals": [asdict(interval) for interval in item.intervals],
        }
        for item in sorted(sources, key=lambda row: (row.well_id, row.interpretation_id, row.revision_id))
    ]
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def build_correlation_suggestions(
    workspace: CorrelationWorkspace,
    sources: Iterable[PublishedInterpretationInput],
    *,
    max_depth_delta: float = 50.0,
    minimum_confidence: float = 0.55,
) -> CorrelationSuggestionPreview:
    """Build non-mutating, reproducible tie candidates from published intervals."""
    max_delta = float(max_depth_delta)
    if max_delta <= 0:
        raise ValueError("Максимальная разница глубин должна быть больше нуля.")
    min_conf = float(minimum_confidence)
    if not 0.0 <= min_conf <= 1.0:
        raise ValueError("Минимальная уверенность должна быть от 0 до 1.")

    source_rows = tuple(sources)
    existing = {
        frozenset(((tie.left.well_id, tie.left.interval_id), (tie.right.well_id, tie.right.interval_id)))
        for tie in workspace.ties
    }
    candidates: list[CorrelationSuggestion] = []
    for left_index, left_source in enumerate(source_rows):
        for right_source in source_rows[left_index + 1 :]:
            if left_source.well_id == right_source.well_id:
                continue
            for left_interval in left_source.intervals:
                best: CorrelationSuggestion | None = None
                for right_interval in right_source.intervals:
                    key = frozenset(((left_source.well_id, left_interval.id), (right_source.well_id, right_interval.id)))
                    if key in existing:
                        continue
                    depth_delta = abs(float(left_interval.middle_depth) - float(right_interval.middle_depth))
                    if depth_delta > max_delta:
                        continue
                    type_match = _norm(left_interval.interval_type) == _norm(right_interval.interval_type) and _norm(left_interval.interval_type) not in {"", "undefined"}
                    label_match = _norm(left_interval.label) == _norm(right_interval.label) and bool(_norm(left_interval.label))
                    score = 0.25 + (0.40 if type_match else 0.0) + (0.25 if label_match else 0.0) + 0.10 * (1.0 - depth_delta / max_delta)
                    score = round(min(1.0, score), 4)
                    if score < min_conf:
                        continue
                    reason_parts = []
                    if type_match:
                        reason_parts.append("совпадает тип")
                    if label_match:
                        reason_parts.append("совпадает подпись")
                    reason_parts.append(f"Δ глубины {depth_delta:.2f} м")
                    left_endpoint = CorrelationEndpoint(left_source.well_id, left_source.interpretation_id, left_source.revision_id, left_interval.id, float(left_interval.middle_depth), left_interval.label)
                    right_endpoint = CorrelationEndpoint(right_source.well_id, right_source.interpretation_id, right_source.revision_id, right_interval.id, float(right_interval.middle_depth), right_interval.label)
                    identity = "|".join((left_source.well_id, left_interval.id, right_source.well_id, right_interval.id))
                    candidate = CorrelationSuggestion(
                        id=hashlib.sha256(identity.encode()).hexdigest()[:20],
                        left=left_endpoint,
                        right=right_endpoint,
                        confidence=score,
                        reason=", ".join(reason_parts),
                        depth_delta=round(depth_delta, 6),
                        type_match=type_match,
                        label_match=label_match,
                    )
                    if best is None or (candidate.confidence, -candidate.depth_delta, candidate.id) > (best.confidence, -best.depth_delta, best.id):
                        best = candidate
                if best is not None:
                    candidates.append(best)
    candidates.sort(key=lambda item: (-item.confidence, item.depth_delta, item.left.well_id, item.left.depth))
    return CorrelationSuggestionPreview(
        schema=SUGGESTION_SCHEMA,
        workspace_id=workspace.id,
        workspace_state_token=workspace.state_token,
        source_state_token=_source_token(source_rows),
        suggestions=tuple(candidates),
    )


def validate_suggestion_preview(
    preview: CorrelationSuggestionPreview,
    workspace: CorrelationWorkspace,
    sources: Iterable[PublishedInterpretationInput],
) -> None:
    if preview.workspace_id != workspace.id or preview.workspace_state_token != workspace.state_token:
        raise ValueError("Корреляционный проект изменился после построения предложений.")
    if preview.source_state_token != _source_token(tuple(sources)):
        raise ValueError("Опубликованные источники изменились после построения предложений.")


def suggestion_preview_from_dict(payload: dict) -> CorrelationSuggestionPreview:
    if payload.get("schema") != SUGGESTION_SCHEMA:
        raise ValueError("Неподдерживаемая схема предложений корреляции.")
    suggestions = []
    for row in payload.get("suggestions", []):
        suggestions.append(CorrelationSuggestion(
            id=str(row["id"]),
            left=CorrelationEndpoint(**row["left"]),
            right=CorrelationEndpoint(**row["right"]),
            confidence=float(row["confidence"]),
            reason=str(row["reason"]),
            depth_delta=float(row["depth_delta"]),
            type_match=bool(row["type_match"]),
            label_match=bool(row["label_match"]),
        ))
    return CorrelationSuggestionPreview(
        schema=SUGGESTION_SCHEMA,
        workspace_id=str(payload["workspace_id"]),
        workspace_state_token=str(payload["workspace_state_token"]),
        source_state_token=str(payload["source_state_token"]),
        suggestions=tuple(suggestions),
    )
