from __future__ import annotations

"""Serializable property-panel model for manual interpretation intervals.

This module contains no Streamlit or runtime objects.  It prepares immutable,
JSON-compatible values for a UI form and validates submitted edits before they
are delegated to :class:`InterpretationIntervalManager`.
"""

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from projects.interpretation_interval_manager import InterpretationIntervalManager
from projects.interpretation_intervals import InterpretationInterval, build_interpretation_interval


@dataclass(frozen=True)
class InterpretationIntervalProperties:
    """Editable values and derived read-only metrics for one interval."""

    interval_id: str
    label: str
    top: float
    base: float
    thickness: float
    middle_depth: float
    interval_type: str
    color: str
    comment: str
    source: str

    def to_form_values(self) -> dict[str, Any]:
        """Return a plain dictionary suitable for session/form state."""

        return asdict(self)


_EDITABLE_FIELDS = ("label", "top", "base", "interval_type", "color", "comment")


def interval_properties(interval: InterpretationInterval) -> InterpretationIntervalProperties:
    """Build the property-panel projection for a persisted interval."""

    return InterpretationIntervalProperties(
        interval_id=interval.id,
        label=interval.label,
        top=interval.top,
        base=interval.base,
        thickness=interval.thickness,
        middle_depth=interval.middle_depth,
        interval_type=interval.interval_type,
        color=interval.color,
        comment=interval.comment,
        source=interval.source,
    )


def validate_interval_property_changes(
    current: InterpretationInterval,
    changes: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate a partial property form and return normalized editable fields.

    Unknown keys are ignored so UI-only values such as button flags cannot leak
    into the repository API.  Validation reuses the canonical interval builder,
    guaranteeing the same depth, text and colour rules as direct repository use.
    """

    merged = {field: getattr(current, field) for field in _EDITABLE_FIELDS}
    for field in _EDITABLE_FIELDS:
        if field in changes:
            merged[field] = changes[field]

    normalized = build_interpretation_interval(
        interval_id=current.id,
        label=merged["label"],
        top=merged["top"],
        base=merged["base"],
        interval_type=merged["interval_type"],
        color=merged["color"],
        comment=merged["comment"],
        source=current.source,
        created_at=current.created_at,
        updated_at=current.updated_at,
    )
    return {field: getattr(normalized, field) for field in _EDITABLE_FIELDS}


class InterpretationIntervalPropertiesService:
    """Prepare and apply property-panel edits through the interval manager."""

    def __init__(self, manager: InterpretationIntervalManager) -> None:
        self.manager = manager

    def get(self, interval_id: str) -> InterpretationIntervalProperties:
        return interval_properties(self.manager.get_interval(interval_id))

    def apply(
        self,
        interval_id: str,
        changes: Mapping[str, Any],
        *,
        reject_overlaps: bool = False,
    ) -> InterpretationIntervalProperties:
        current = self.manager.get_interval(interval_id)
        fields = validate_interval_property_changes(current, changes)
        updated = self.manager.update(
            interval_id,
            reject_overlaps=reject_overlaps,
            **fields,
        )
        return interval_properties(updated)
