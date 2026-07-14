from __future__ import annotations

"""Deterministic, configurable candidate generation for multi-well correlation ties."""

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence
from uuid import uuid4

from projects.interpretation_correlation import (
    CorrelationEndpoint,
    CorrelationWorkspace,
    PublishedInterpretationInput,
    _atomic_write,
    _utc_now,
)
from projects.repository import DEFAULT_PROJECTS_ROOT, safe_project_id

SUGGESTION_SCHEMA = "gas-ratio-pro/interpretation-correlation-suggestions/v2"
LEGACY_SUGGESTION_SCHEMA = "gas-ratio-pro/interpretation-correlation-suggestions/v1"
PROFILE_SCHEMA = "gas-ratio-pro/interpretation-correlation-suggestion-profiles/v1"
ACCEPTANCE_JOURNAL_SCHEMA = "gas-ratio-pro/interpretation-correlation-suggestion-acceptance/v1"


@dataclass(frozen=True)
class CorrelationSuggestionSettings:
    max_depth_delta: float = 50.0
    minimum_confidence: float = 0.55
    base_weight: float = 0.25
    type_weight: float = 0.40
    label_weight: float = 0.25
    depth_weight: float = 0.10

    def validate(self) -> "CorrelationSuggestionSettings":
        if float(self.max_depth_delta) <= 0:
            raise ValueError("Максимальная разница глубин должна быть больше нуля.")
        if not 0.0 <= float(self.minimum_confidence) <= 1.0:
            raise ValueError("Минимальная уверенность должна быть от 0 до 1.")
        weights = (self.base_weight, self.type_weight, self.label_weight, self.depth_weight)
        if any(float(value) < 0 for value in weights):
            raise ValueError("Веса критериев не могут быть отрицательными.")
        if sum(float(value) for value in weights) <= 0:
            raise ValueError("Сумма весов критериев должна быть больше нуля.")
        return self

    @property
    def normalized_weights(self) -> tuple[float, float, float, float]:
        total = self.base_weight + self.type_weight + self.label_weight + self.depth_weight
        return tuple(float(value) / float(total) for value in (
            self.base_weight, self.type_weight, self.label_weight, self.depth_weight
        ))


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
    settings: CorrelationSuggestionSettings
    suggestions: tuple[CorrelationSuggestion, ...]


@dataclass(frozen=True)
class CorrelationSuggestionScenario:
    name: str
    settings: CorrelationSuggestionSettings
    suggestion_count: int
    high_confidence_count: int
    average_confidence: float
    average_depth_delta: float


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
    settings: CorrelationSuggestionSettings | None = None,
    max_depth_delta: float | None = None,
    minimum_confidence: float | None = None,
) -> CorrelationSuggestionPreview:
    """Build non-mutating, reproducible tie candidates from published intervals."""
    active = settings or CorrelationSuggestionSettings()
    if max_depth_delta is not None or minimum_confidence is not None:
        active = CorrelationSuggestionSettings(
            max_depth_delta=active.max_depth_delta if max_depth_delta is None else float(max_depth_delta),
            minimum_confidence=active.minimum_confidence if minimum_confidence is None else float(minimum_confidence),
            base_weight=active.base_weight,
            type_weight=active.type_weight,
            label_weight=active.label_weight,
            depth_weight=active.depth_weight,
        )
    active.validate()
    base_w, type_w, label_w, depth_w = active.normalized_weights

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
                    if depth_delta > active.max_depth_delta:
                        continue
                    type_match = _norm(left_interval.interval_type) == _norm(right_interval.interval_type) and _norm(left_interval.interval_type) not in {"", "undefined"}
                    label_match = _norm(left_interval.label) == _norm(right_interval.label) and bool(_norm(left_interval.label))
                    depth_score = max(0.0, 1.0 - depth_delta / active.max_depth_delta)
                    score = base_w + (type_w if type_match else 0.0) + (label_w if label_match else 0.0) + depth_w * depth_score
                    score = round(min(1.0, score), 4)
                    if score < active.minimum_confidence:
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
        settings=active,
        suggestions=tuple(candidates),
    )


def compare_suggestion_scenarios(
    workspace: CorrelationWorkspace,
    sources: Iterable[PublishedInterpretationInput],
    scenarios: Iterable[tuple[str, CorrelationSuggestionSettings]],
) -> tuple[CorrelationSuggestionScenario, ...]:
    source_rows = tuple(sources)
    rows: list[CorrelationSuggestionScenario] = []
    for name, settings in scenarios:
        preview = build_correlation_suggestions(workspace, source_rows, settings=settings)
        confidences = [item.confidence for item in preview.suggestions]
        deltas = [item.depth_delta for item in preview.suggestions]
        rows.append(CorrelationSuggestionScenario(
            name=str(name).strip() or "Сценарий",
            settings=settings,
            suggestion_count=len(preview.suggestions),
            high_confidence_count=sum(value >= 0.75 for value in confidences),
            average_confidence=round(sum(confidences) / len(confidences), 4) if confidences else 0.0,
            average_depth_delta=round(sum(deltas) / len(deltas), 4) if deltas else 0.0,
        ))
    return tuple(rows)


def validate_suggestion_preview(preview: CorrelationSuggestionPreview, workspace: CorrelationWorkspace, sources: Iterable[PublishedInterpretationInput]) -> None:
    if preview.workspace_id != workspace.id or preview.workspace_state_token != workspace.state_token:
        raise ValueError("Корреляционный проект изменился после построения предложений.")
    if preview.source_state_token != _source_token(tuple(sources)):
        raise ValueError("Опубликованные источники изменились после построения предложений.")


def suggestion_preview_from_dict(payload: dict) -> CorrelationSuggestionPreview:
    schema = payload.get("schema")
    if schema not in {SUGGESTION_SCHEMA, LEGACY_SUGGESTION_SCHEMA}:
        raise ValueError("Неподдерживаемая схема предложений корреляции.")
    suggestions = []
    for row in payload.get("suggestions", []):
        suggestions.append(CorrelationSuggestion(
            id=str(row["id"]), left=CorrelationEndpoint(**row["left"]), right=CorrelationEndpoint(**row["right"]),
            confidence=float(row["confidence"]), reason=str(row["reason"]), depth_delta=float(row["depth_delta"]),
            type_match=bool(row["type_match"]), label_match=bool(row["label_match"]),
        ))
    settings_payload = payload.get("settings") or {}
    settings = CorrelationSuggestionSettings(**settings_payload).validate()
    return CorrelationSuggestionPreview(
        schema=SUGGESTION_SCHEMA,
        workspace_id=str(payload["workspace_id"]), workspace_state_token=str(payload["workspace_state_token"]),
        source_state_token=str(payload["source_state_token"]), settings=settings, suggestions=tuple(suggestions),
    )


class CorrelationSuggestionProfileRepository:
    """Project-scoped atomic storage for reusable suggestion calibration profiles."""

    def __init__(self, *, root: Path | str = DEFAULT_PROJECTS_ROOT, project_id: str) -> None:
        self.path = Path(root) / safe_project_id(project_id) / "correlations" / "suggestion_profiles.json"

    def list(self) -> tuple[dict[str, Any], ...]:
        if not self.path.exists():
            return ()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return ()
        if payload.get("schema") != PROFILE_SCHEMA:
            return ()
        return tuple(dict(item) for item in payload.get("profiles", ()) if isinstance(item, dict))

    def save(self, *, name: str, settings: CorrelationSuggestionSettings) -> dict[str, Any]:
        clean_name = str(name or "").strip()
        if not clean_name:
            raise ValueError("Укажите название профиля.")
        settings.validate()
        rows = list(self.list())
        current = next((item for item in rows if str(item.get("name", "")).casefold() == clean_name.casefold()), None)
        profile = {
            "id": current.get("id") if current else str(uuid4()),
            "name": clean_name,
            "settings": asdict(settings),
            "updated_at": _utc_now(),
        }
        rows = [profile if current and item.get("id") == current.get("id") else item for item in rows]
        if current is None:
            rows.append(profile)
        _atomic_write(self.path, {"schema": PROFILE_SCHEMA, "profiles": rows})
        return profile

    def delete(self, profile_id: str) -> bool:
        rows = list(self.list())
        kept = [item for item in rows if item.get("id") != profile_id]
        if len(kept) == len(rows):
            return False
        _atomic_write(self.path, {"schema": PROFILE_SCHEMA, "profiles": kept})
        return True


class CorrelationSuggestionAcceptanceJournal:
    """Persistent compact audit of accepted automatic suggestions."""

    def __init__(self, *, root: Path | str = DEFAULT_PROJECTS_ROOT, project_id: str, workspace_id: str, limit: int = 200) -> None:
        self.path = Path(root) / safe_project_id(project_id) / "correlations" / str(workspace_id) / "suggestion_acceptance.json"
        self.limit = max(1, int(limit))

    def list(self) -> tuple[dict[str, Any], ...]:
        if not self.path.exists():
            return ()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return ()
        if payload.get("schema") != ACCEPTANCE_JOURNAL_SCHEMA:
            return ()
        return tuple(dict(item) for item in payload.get("operations", ()) if isinstance(item, dict))

    def append(self, *, preview: CorrelationSuggestionPreview, accepted_ids: Sequence[str], added_tie_ids: Sequence[str]) -> None:
        selected = [item for item in preview.suggestions if item.id in set(accepted_ids)]
        rows = list(self.list())
        rows.append({
            "id": str(uuid4()), "timestamp": _utc_now(), "workspace_id": preview.workspace_id,
            "settings": asdict(preview.settings), "accepted_count": len(selected),
            "average_confidence": round(sum(item.confidence for item in selected) / len(selected), 4) if selected else 0.0,
            "suggestion_ids": [item.id for item in selected], "added_tie_ids": list(added_tie_ids),
        })
        _atomic_write(self.path, {"schema": ACCEPTANCE_JOURNAL_SCHEMA, "operations": rows[-self.limit:]})
