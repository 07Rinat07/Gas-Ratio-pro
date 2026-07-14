from __future__ import annotations

"""Undo/Redo-aware batch operations for manual interpretation intervals."""

from dataclasses import dataclass
from typing import Iterable

from projects.interpretation_interval_manager import InterpretationIntervalManager
from projects.interpretation_intervals import InterpretationInterval, build_interpretation_interval


@dataclass(frozen=True)
class InterpretationIntervalBatchResult:
    action: str
    selected_count: int
    changed_count: int
    interval_ids: tuple[str, ...]


class InterpretationIntervalBatchService:
    """Apply one validated mutation to several intervals as a single command."""

    def __init__(self, manager: InterpretationIntervalManager) -> None:
        self.manager = manager

    def assign_type(
        self,
        interval_ids: Iterable[str],
        *,
        interval_type: str,
        color: str | None = None,
    ) -> InterpretationIntervalBatchResult:
        selected_ids = self._normalize_ids(interval_ids)
        selected = set(selected_ids)
        current = self.manager.list_intervals()
        self._ensure_known(selected, current)

        updated: list[InterpretationInterval] = []
        changed_ids: list[str] = []
        for interval in current:
            if interval.id not in selected:
                updated.append(interval)
                continue
            target_color = interval.color if color is None else color
            replacement = build_interpretation_interval(
                interval_id=interval.id,
                label=interval.label,
                top=interval.top,
                base=interval.base,
                interval_type=interval_type,
                color=target_color,
                comment=interval.comment,
                source=interval.source,
                created_at=interval.created_at,
            )
            updated.append(replacement)
            if replacement != interval:
                changed_ids.append(interval.id)

        if changed_ids:
            self.manager.replace_all(tuple(updated), action="batch_assign_type")
        return InterpretationIntervalBatchResult(
            action="assign_type",
            selected_count=len(selected_ids),
            changed_count=len(changed_ids),
            interval_ids=tuple(changed_ids),
        )

    def delete(self, interval_ids: Iterable[str]) -> InterpretationIntervalBatchResult:
        selected_ids = self._normalize_ids(interval_ids)
        selected = set(selected_ids)
        current = self.manager.list_intervals()
        self._ensure_known(selected, current)
        remaining = tuple(interval for interval in current if interval.id not in selected)
        self.manager.replace_all(remaining, action="batch_delete")
        return InterpretationIntervalBatchResult(
            action="delete",
            selected_count=len(selected_ids),
            changed_count=len(selected_ids),
            interval_ids=selected_ids,
        )

    @staticmethod
    def _normalize_ids(interval_ids: Iterable[str]) -> tuple[str, ...]:
        normalized = tuple(dict.fromkeys(str(value).strip() for value in interval_ids if str(value).strip()))
        if not normalized:
            raise ValueError("Выберите хотя бы один интервал.")
        return normalized

    @staticmethod
    def _ensure_known(selected: set[str], current: tuple[InterpretationInterval, ...]) -> None:
        known = {interval.id for interval in current}
        missing = sorted(selected - known)
        if missing:
            raise KeyError(f"Интервалы не найдены: {', '.join(missing)}")
