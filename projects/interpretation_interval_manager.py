from __future__ import annotations

"""Application-facing manager for manual interpretation intervals.

The manager provides one stable API for listing, lookup, CRUD, overlap analysis
and Undo/Redo. Persistence remains delegated to the repository, while reversible
mutations remain delegated to ``InterpretationIntervalCommandService``.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, MutableMapping

from projects.interpretation_interval_commands import InterpretationIntervalCommandService
from projects.interpretation_intervals import (
    DEFAULT_INTERPRETATION_ID,
    InterpretationInterval,
    load_interpretation_intervals,
)
from projects.repository import DEFAULT_PROJECTS_ROOT


class InterpretationIntervalOverlapError(ValueError):
    """Raised when a mutation violates the optional non-overlap policy."""


@dataclass(frozen=True)
class InterpretationIntervalOverlap:
    """Serializable description of an overlap between two depth intervals."""

    interval_id: str
    label: str
    top: float
    base: float
    overlap_top: float
    overlap_base: float

    @property
    def overlap_thickness(self) -> float:
        return round(self.overlap_base - self.overlap_top, 6)


class InterpretationIntervalManager:
    """Coordinate repository access, validation and reversible mutations."""

    def __init__(
        self,
        state: MutableMapping[str, Any],
        *,
        root: Path | str = DEFAULT_PROJECTS_ROOT,
        project_id: str,
        well_id: str,
        interpretation_id: str = DEFAULT_INTERPRETATION_ID,
        history_limit: int = 50,
    ) -> None:
        self.root = Path(root)
        self.project_id = str(project_id)
        self.well_id = str(well_id)
        self.interpretation_id = str(interpretation_id)
        self.commands = InterpretationIntervalCommandService(
            state,
            root=self.root,
            project_id=self.project_id,
            well_id=self.well_id,
            interpretation_id=self.interpretation_id,
            history_limit=history_limit,
        )

    def list_intervals(self) -> tuple[InterpretationInterval, ...]:
        """Return intervals in deterministic top/base/label order."""

        return load_interpretation_intervals(
            self.root,
            self.project_id,
            self.well_id,
            self.interpretation_id,
        ).intervals

    def get_interval(self, interval_id: str) -> InterpretationInterval:
        """Return one interval by UUID or raise ``KeyError``."""

        clean_id = str(interval_id)
        interval = next((item for item in self.list_intervals() if item.id == clean_id), None)
        if interval is None:
            raise KeyError(f"Интервал не найден: {clean_id}")
        return interval

    def find_overlaps(
        self,
        *,
        top: float,
        base: float,
        exclude_interval_id: str | None = None,
    ) -> tuple[InterpretationIntervalOverlap, ...]:
        """Find positive-thickness intersections with the supplied depth range.

        Adjacent ranges such as ``100-110`` and ``110-120`` are not considered
        overlapping because their intersection thickness is zero.
        """

        clean_top, clean_base = self._validate_range(top, base)
        excluded = str(exclude_interval_id or "")
        overlaps: list[InterpretationIntervalOverlap] = []
        for interval in self.list_intervals():
            if excluded and interval.id == excluded:
                continue
            overlap_top = max(clean_top, interval.top)
            overlap_base = min(clean_base, interval.base)
            if overlap_top < overlap_base:
                overlaps.append(
                    InterpretationIntervalOverlap(
                        interval_id=interval.id,
                        label=interval.label,
                        top=interval.top,
                        base=interval.base,
                        overlap_top=overlap_top,
                        overlap_base=overlap_base,
                    )
                )
        return tuple(overlaps)

    def create(self, *, reject_overlaps: bool = False, **fields: Any) -> InterpretationInterval:
        self._check_overlap_policy(
            top=fields.get("top"),
            base=fields.get("base"),
            reject_overlaps=reject_overlaps,
        )
        return self.commands.create(**fields)

    def update(
        self,
        interval_id: str,
        *,
        reject_overlaps: bool = False,
        **fields: Any,
    ) -> InterpretationInterval:
        self.get_interval(interval_id)
        self._check_overlap_policy(
            top=fields.get("top"),
            base=fields.get("base"),
            reject_overlaps=reject_overlaps,
            exclude_interval_id=interval_id,
        )
        return self.commands.update(interval_id, **fields)

    def delete(self, interval_id: str) -> bool:
        return self.commands.delete(interval_id)

    def undo(self) -> bool:
        return self.commands.undo()

    def redo(self) -> bool:
        return self.commands.redo()

    @property
    def can_undo(self) -> bool:
        return self.commands.can_undo

    @property
    def can_redo(self) -> bool:
        return self.commands.can_redo

    def history_status(self) -> dict[str, Any]:
        return self.commands.history_status()

    @staticmethod
    def _validate_range(top: Any, base: Any) -> tuple[float, float]:
        try:
            clean_top = float(top)
            clean_base = float(base)
        except (TypeError, ValueError) as exc:
            raise ValueError("Верх и низ интервала должны быть числовыми.") from exc
        if not clean_top < clean_base:
            raise ValueError("Верх интервала должен быть меньше низа.")
        return clean_top, clean_base

    def _check_overlap_policy(
        self,
        *,
        top: Any,
        base: Any,
        reject_overlaps: bool,
        exclude_interval_id: str | None = None,
    ) -> None:
        if not reject_overlaps:
            return
        overlaps = self.find_overlaps(
            top=top,
            base=base,
            exclude_interval_id=exclude_interval_id,
        )
        if overlaps:
            labels = ", ".join(item.label for item in overlaps[:3])
            suffix = "" if len(overlaps) <= 3 else f" и ещё {len(overlaps) - 3}"
            raise InterpretationIntervalOverlapError(
                f"Интервал пересекается с существующими: {labels}{suffix}."
            )
