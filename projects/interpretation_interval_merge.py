from __future__ import annotations

"""Three-way merge for manual interpretation interval workspaces."""

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Literal, MutableMapping

from projects.interpretation_interval_manager import InterpretationIntervalManager
from projects.interpretation_intervals import InterpretationInterval, load_interpretation_intervals
from projects.repository import DEFAULT_PROJECTS_ROOT

MergeDecision = Literal["automatic", "source", "target", "skip"]
ConflictPolicy = Literal["source", "target", "skip"]
_COMPARE_FIELDS = ("label", "top", "base", "interval_type", "color", "comment", "source")


@dataclass(frozen=True)
class InterpretationMergeConflict:
    interval_id: str
    base: InterpretationInterval | None
    source: InterpretationInterval | None
    target: InterpretationInterval | None
    changed_fields: tuple[str, ...]


@dataclass(frozen=True)
class InterpretationMergePreview:
    base_interpretation_id: str
    source_interpretation_id: str
    target_interpretation_id: str
    automatic_count: int
    conflict_count: int
    unchanged_count: int
    delete_count: int
    conflicts: tuple[InterpretationMergeConflict, ...]
    confirmation_token: str


@dataclass(frozen=True)
class InterpretationMergeResult:
    automatic_count: int
    resolved_conflict_count: int
    skipped_conflict_count: int
    deleted_count: int
    target_interval_count: int


def _signature(interval: InterpretationInterval | None) -> dict[str, Any] | None:
    if interval is None:
        return None
    return {field: getattr(interval, field) for field in _COMPARE_FIELDS}


def _snapshot(intervals: Iterable[InterpretationInterval]) -> list[dict[str, Any]]:
    return [asdict(item) for item in sorted(intervals, key=lambda row: (row.id, row.top, row.base))]


def _changed_fields(
    left: InterpretationInterval | None,
    right: InterpretationInterval | None,
) -> tuple[str, ...]:
    if left is None or right is None:
        return ("existence",)
    return tuple(field for field in _COMPARE_FIELDS if getattr(left, field) != getattr(right, field))


def _token(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class InterpretationIntervalMergeService:
    """Preview and apply a stale-safe three-way merge into the target workspace."""

    def __init__(
        self,
        state: MutableMapping[str, Any],
        *,
        root: Path | str = DEFAULT_PROJECTS_ROOT,
        project_id: str,
        well_id: str,
        base_interpretation_id: str,
        source_interpretation_id: str,
        target_interpretation_id: str,
    ) -> None:
        ids = {base_interpretation_id, source_interpretation_id, target_interpretation_id}
        if len(ids) != 3:
            raise ValueError("Базовая, исходная и целевая интерпретации должны различаться.")
        self.state = state
        self.root = Path(root)
        self.project_id = str(project_id)
        self.well_id = str(well_id)
        self.base_interpretation_id = str(base_interpretation_id)
        self.source_interpretation_id = str(source_interpretation_id)
        self.target_interpretation_id = str(target_interpretation_id)

    def _load(self) -> tuple[tuple[InterpretationInterval, ...], tuple[InterpretationInterval, ...], tuple[InterpretationInterval, ...]]:
        base = load_interpretation_intervals(
            self.root, self.project_id, self.well_id, self.base_interpretation_id
        ).intervals
        source = load_interpretation_intervals(
            self.root, self.project_id, self.well_id, self.source_interpretation_id
        ).intervals
        target = load_interpretation_intervals(
            self.root, self.project_id, self.well_id, self.target_interpretation_id
        ).intervals
        return base, source, target

    def preview(self) -> InterpretationMergePreview:
        base, source, target = self._load()
        base_by_id = {item.id: item for item in base}
        source_by_id = {item.id: item for item in source}
        target_by_id = {item.id: item for item in target}
        automatic = unchanged = deleted = 0
        conflicts: list[InterpretationMergeConflict] = []

        for interval_id in sorted(set(base_by_id) | set(source_by_id) | set(target_by_id)):
            b = base_by_id.get(interval_id)
            s = source_by_id.get(interval_id)
            t = target_by_id.get(interval_id)
            bs = _signature(b)
            ss = _signature(s)
            ts = _signature(t)
            source_changed = ss != bs
            target_changed = ts != bs

            if not source_changed:
                unchanged += 1
                continue
            if not target_changed or ss == ts:
                automatic += 1
                if s is None:
                    deleted += 1
                continue
            conflicts.append(
                InterpretationMergeConflict(
                    interval_id=interval_id,
                    base=b,
                    source=s,
                    target=t,
                    changed_fields=tuple(sorted(set(_changed_fields(b, s)) | set(_changed_fields(b, t)))),
                )
            )

        payload = {
            "base_interpretation_id": self.base_interpretation_id,
            "source_interpretation_id": self.source_interpretation_id,
            "target_interpretation_id": self.target_interpretation_id,
            "base": _snapshot(base),
            "source": _snapshot(source),
            "target": _snapshot(target),
        }
        return InterpretationMergePreview(
            base_interpretation_id=self.base_interpretation_id,
            source_interpretation_id=self.source_interpretation_id,
            target_interpretation_id=self.target_interpretation_id,
            automatic_count=automatic,
            conflict_count=len(conflicts),
            unchanged_count=unchanged,
            delete_count=deleted,
            conflicts=tuple(conflicts),
            confirmation_token=_token(payload),
        )

    def apply(
        self,
        preview: InterpretationMergePreview,
        *,
        expected_confirmation_token: str,
        conflict_policy: ConflictPolicy = "target",
        conflict_resolutions: dict[str, ConflictPolicy] | None = None,
        reject_overlaps: bool = False,
    ) -> InterpretationMergeResult:
        if conflict_policy not in {"source", "target", "skip"}:
            raise ValueError("Неизвестная политика разрешения конфликтов.")
        current = self.preview()
        if not expected_confirmation_token or current.confirmation_token != expected_confirmation_token:
            raise ValueError("Данные изменились после preview; повторите предварительный просмотр.")

        base, source, target = self._load()
        base_by_id = {item.id: item for item in base}
        source_by_id = {item.id: item for item in source}
        target_by_id = {item.id: item for item in target}
        merged = dict(target_by_id)
        automatic = resolved = skipped = deleted = 0
        resolutions = conflict_resolutions or {}

        for interval_id in sorted(set(base_by_id) | set(source_by_id) | set(target_by_id)):
            b = base_by_id.get(interval_id)
            s = source_by_id.get(interval_id)
            t = target_by_id.get(interval_id)
            bs, ss, ts = _signature(b), _signature(s), _signature(t)
            source_changed = ss != bs
            target_changed = ts != bs
            if not source_changed:
                continue
            if not target_changed or ss == ts:
                automatic += 1
                if s is None:
                    merged.pop(interval_id, None)
                    deleted += 1
                else:
                    merged[interval_id] = s
                continue

            decision = resolutions.get(interval_id, conflict_policy)
            if decision == "source":
                if s is None:
                    merged.pop(interval_id, None)
                    deleted += 1
                else:
                    merged[interval_id] = s
                resolved += 1
            elif decision in {"target", "skip"}:
                skipped += 1
            else:
                raise ValueError(f"Неизвестное решение конфликта для {interval_id}: {decision}")

        final_intervals = tuple(merged.values())
        if reject_overlaps:
            ordered = sorted(final_intervals, key=lambda item: (item.top, item.base, item.id))
            for index, current_interval in enumerate(ordered):
                for other in ordered[index + 1:]:
                    if other.top >= current_interval.base:
                        break
                    if max(current_interval.top, other.top) < min(current_interval.base, other.base):
                        raise ValueError(
                            f"Объединение создаёт пересечение интервалов «{current_interval.label}» и «{other.label}»."
                        )

        manager = InterpretationIntervalManager(
            self.state,
            root=self.root,
            project_id=self.project_id,
            well_id=self.well_id,
            interpretation_id=self.target_interpretation_id,
        )
        saved = manager.replace_all(final_intervals, action="merge_interpretations")
        return InterpretationMergeResult(
            automatic_count=automatic,
            resolved_conflict_count=resolved,
            skipped_conflict_count=skipped,
            deleted_count=deleted,
            target_interval_count=len(saved),
        )
