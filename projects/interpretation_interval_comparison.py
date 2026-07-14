from __future__ import annotations

"""Comparison and safe transfer between manual interpretation workspaces."""

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Literal, MutableMapping

from projects.interpretation_interval_manager import InterpretationIntervalManager
from projects.interpretation_intervals import (
    InterpretationInterval,
    build_interpretation_interval,
    load_interpretation_intervals,
)
from projects.repository import DEFAULT_PROJECTS_ROOT

ComparisonStatus = Literal["added", "removed", "modified", "unchanged"]
ConflictPolicy = Literal["overwrite", "skip", "copy"]
_COMPARE_FIELDS = ("label", "top", "base", "interval_type", "color", "comment", "source")


@dataclass(frozen=True)
class InterpretationIntervalDifference:
    interval_id: str
    status: ComparisonStatus
    source: InterpretationInterval | None
    target: InterpretationInterval | None
    changed_fields: tuple[str, ...] = ()


@dataclass(frozen=True)
class InterpretationIntervalComparison:
    source_interpretation_id: str
    target_interpretation_id: str
    differences: tuple[InterpretationIntervalDifference, ...]

    @property
    def added_count(self) -> int:
        return sum(item.status == "added" for item in self.differences)

    @property
    def removed_count(self) -> int:
        return sum(item.status == "removed" for item in self.differences)

    @property
    def modified_count(self) -> int:
        return sum(item.status == "modified" for item in self.differences)

    @property
    def unchanged_count(self) -> int:
        return sum(item.status == "unchanged" for item in self.differences)


@dataclass(frozen=True)
class InterpretationIntervalTransferPreview:
    source_interpretation_id: str
    target_interpretation_id: str
    selected_ids: tuple[str, ...]
    conflict_policy: ConflictPolicy
    add_count: int
    overwrite_count: int
    skip_count: int
    copy_count: int
    confirmation_token: str


@dataclass(frozen=True)
class InterpretationIntervalTransferResult:
    added_count: int
    overwritten_count: int
    skipped_count: int
    copied_count: int
    target_interval_count: int


def _interval_signature(interval: InterpretationInterval) -> dict[str, Any]:
    return {field: getattr(interval, field) for field in _COMPARE_FIELDS}


def _snapshot(intervals: Iterable[InterpretationInterval]) -> list[dict[str, Any]]:
    return [asdict(item) for item in sorted(intervals, key=lambda row: (row.id, row.top, row.base))]


def _confirmation_token(
    source_interpretation_id: str,
    target_interpretation_id: str,
    source: Iterable[InterpretationInterval],
    target: Iterable[InterpretationInterval],
    selected_ids: tuple[str, ...],
    conflict_policy: ConflictPolicy,
) -> str:
    payload = {
        "source_interpretation_id": source_interpretation_id,
        "target_interpretation_id": target_interpretation_id,
        "source": _snapshot(source),
        "target": _snapshot(target),
        "selected_ids": list(selected_ids),
        "conflict_policy": conflict_policy,
    }
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def compare_interpretation_intervals(
    *,
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str,
    well_id: str,
    source_interpretation_id: str,
    target_interpretation_id: str,
) -> InterpretationIntervalComparison:
    source_set = load_interpretation_intervals(root, project_id, well_id, source_interpretation_id)
    target_set = load_interpretation_intervals(root, project_id, well_id, target_interpretation_id)
    source_by_id = {item.id: item for item in source_set.intervals}
    target_by_id = {item.id: item for item in target_set.intervals}
    differences: list[InterpretationIntervalDifference] = []
    for interval_id in sorted(set(source_by_id) | set(target_by_id)):
        source = source_by_id.get(interval_id)
        target = target_by_id.get(interval_id)
        if source is None:
            status: ComparisonStatus = "removed"
            changed_fields: tuple[str, ...] = ()
        elif target is None:
            status = "added"
            changed_fields = ()
        else:
            changed_fields = tuple(
                field for field in _COMPARE_FIELDS if getattr(source, field) != getattr(target, field)
            )
            status = "modified" if changed_fields else "unchanged"
        differences.append(
            InterpretationIntervalDifference(
                interval_id=interval_id,
                status=status,
                source=source,
                target=target,
                changed_fields=changed_fields,
            )
        )
    return InterpretationIntervalComparison(
        source_interpretation_id=source_interpretation_id,
        target_interpretation_id=target_interpretation_id,
        differences=tuple(differences),
    )


class InterpretationIntervalTransferService:
    def __init__(
        self,
        state: MutableMapping[str, Any],
        *,
        root: Path | str = DEFAULT_PROJECTS_ROOT,
        project_id: str,
        well_id: str,
        source_interpretation_id: str,
        target_interpretation_id: str,
    ) -> None:
        if source_interpretation_id == target_interpretation_id:
            raise ValueError("Источник и целевая интерпретация должны различаться.")
        self.state = state
        self.root = Path(root)
        self.project_id = project_id
        self.well_id = well_id
        self.source_interpretation_id = source_interpretation_id
        self.target_interpretation_id = target_interpretation_id

    def preview(
        self,
        interval_ids: Iterable[str],
        *,
        conflict_policy: ConflictPolicy = "overwrite",
    ) -> InterpretationIntervalTransferPreview:
        if conflict_policy not in {"overwrite", "skip", "copy"}:
            raise ValueError("Неизвестная политика конфликта UUID.")
        selected_ids = tuple(dict.fromkeys(str(item) for item in interval_ids if str(item).strip()))
        if not selected_ids:
            raise ValueError("Не выбраны интервалы для переноса.")
        source_set = load_interpretation_intervals(
            self.root, self.project_id, self.well_id, self.source_interpretation_id
        )
        target_set = load_interpretation_intervals(
            self.root, self.project_id, self.well_id, self.target_interpretation_id
        )
        source_by_id = {item.id: item for item in source_set.intervals}
        missing = [item for item in selected_ids if item not in source_by_id]
        if missing:
            raise KeyError(f"Интервалы источника не найдены: {', '.join(missing[:3])}")
        target_ids = {item.id for item in target_set.intervals}
        conflicts = sum(item in target_ids for item in selected_ids)
        add_count = len(selected_ids) - conflicts
        return InterpretationIntervalTransferPreview(
            source_interpretation_id=self.source_interpretation_id,
            target_interpretation_id=self.target_interpretation_id,
            selected_ids=selected_ids,
            conflict_policy=conflict_policy,
            add_count=add_count,
            overwrite_count=conflicts if conflict_policy == "overwrite" else 0,
            skip_count=conflicts if conflict_policy == "skip" else 0,
            copy_count=conflicts if conflict_policy == "copy" else 0,
            confirmation_token=_confirmation_token(
                self.source_interpretation_id,
                self.target_interpretation_id,
                source_set.intervals,
                target_set.intervals,
                selected_ids,
                conflict_policy,
            ),
        )

    def apply(
        self,
        preview: InterpretationIntervalTransferPreview,
        *,
        expected_confirmation_token: str,
        reject_overlaps: bool = False,
    ) -> InterpretationIntervalTransferResult:
        current_preview = self.preview(preview.selected_ids, conflict_policy=preview.conflict_policy)
        if not expected_confirmation_token or current_preview.confirmation_token != expected_confirmation_token:
            raise ValueError("Данные изменились после preview; повторите предварительный просмотр.")
        source_set = load_interpretation_intervals(
            self.root, self.project_id, self.well_id, self.source_interpretation_id
        )
        target_set = load_interpretation_intervals(
            self.root, self.project_id, self.well_id, self.target_interpretation_id
        )
        source_by_id = {item.id: item for item in source_set.intervals}
        target_by_id = {item.id: item for item in target_set.intervals}
        added = overwritten = skipped = copied = 0
        for interval_id in preview.selected_ids:
            source = source_by_id[interval_id]
            if interval_id not in target_by_id:
                target_by_id[interval_id] = source
                added += 1
            elif preview.conflict_policy == "skip":
                skipped += 1
            elif preview.conflict_policy == "overwrite":
                target_by_id[interval_id] = source
                overwritten += 1
            else:
                copied_interval = build_interpretation_interval(
                    label=source.label,
                    top=source.top,
                    base=source.base,
                    interval_type=source.interval_type,
                    color=source.color,
                    comment=source.comment,
                    source=source.source,
                )
                target_by_id[copied_interval.id] = copied_interval
                copied += 1

        final_intervals = tuple(target_by_id.values())
        if reject_overlaps:
            ordered = sorted(final_intervals, key=lambda item: (item.top, item.base, item.id))
            for index, current in enumerate(ordered):
                for other in ordered[index + 1 :]:
                    if other.top >= current.base:
                        break
                    if max(current.top, other.top) < min(current.base, other.base):
                        raise ValueError(
                            f"Перенос создаёт пересечение интервалов «{current.label}» и «{other.label}»."
                        )

        manager = InterpretationIntervalManager(
            self.state,
            root=self.root,
            project_id=self.project_id,
            well_id=self.well_id,
            interpretation_id=self.target_interpretation_id,
        )
        saved = manager.replace_all(final_intervals, action="transfer_from_interpretation")
        return InterpretationIntervalTransferResult(
            added_count=added,
            overwritten_count=overwritten,
            skipped_count=skipped,
            copied_count=copied,
            target_interval_count=len(saved),
        )
