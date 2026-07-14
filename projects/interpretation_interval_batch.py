from __future__ import annotations

"""Undo/Redo-aware batch operations for manual interpretation intervals."""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from typing import Iterable

from projects.interpretation_interval_manager import InterpretationIntervalManager
from projects.interpretation_intervals import InterpretationInterval, build_interpretation_interval


class InterpretationIntervalBatchConflict(RuntimeError):
    """Raised when confirmed batch preview no longer matches repository state."""


@dataclass(frozen=True)
class InterpretationIntervalBatchResult:
    action: str
    selected_count: int
    changed_count: int
    interval_ids: tuple[str, ...]


@dataclass(frozen=True)
class InterpretationIntervalBatchPreviewItem:
    interval_id: str
    label: str
    top: float
    base: float
    current_type: str
    target_type: str
    current_color: str
    target_color: str
    current_comment: str
    target_comment: str
    current_source: str
    target_source: str
    will_change: bool


@dataclass(frozen=True)
class InterpretationIntervalBatchPreview:
    action: str
    selected_count: int
    changed_count: int
    items: tuple[InterpretationIntervalBatchPreviewItem, ...]
    confirmation_token: str


class InterpretationIntervalBatchService:
    """Apply one validated mutation to several intervals as a single command."""

    def __init__(self, manager: InterpretationIntervalManager) -> None:
        self.manager = manager
        self._journal_key = (
            f"interpretation_interval_batch_journal::{manager.project_id}::"
            f"{manager.well_id}::{manager.interpretation_id}"
        )


    def preview_assign_type(
        self,
        interval_ids: Iterable[str],
        *,
        interval_type: str,
        color: str | None = None,
    ) -> InterpretationIntervalBatchPreview:
        selected_ids = self._normalize_ids(interval_ids)
        selected_intervals = self._selected_intervals(selected_ids)
        items: list[InterpretationIntervalBatchPreviewItem] = []
        for interval in selected_intervals:
            target_color = interval.color if color is None else str(color)
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
            items.append(self._preview_item(interval, replacement))
        return self._preview("assign_type", selected_ids, items, {"interval_type": str(interval_type), "color": color})

    def preview_edit_metadata(
        self,
        interval_ids: Iterable[str],
        *,
        comment: str | None = None,
        comment_mode: str = "replace",
        source: str | None = None,
    ) -> InterpretationIntervalBatchPreview:
        selected_ids = self._normalize_ids(interval_ids)
        clean_mode = self._validate_metadata_request(comment, comment_mode, source)
        items: list[InterpretationIntervalBatchPreviewItem] = []
        for interval in self._selected_intervals(selected_ids):
            target_comment, target_source = self._metadata_targets(
                interval, comment=comment, comment_mode=clean_mode, source=source
            )
            replacement = build_interpretation_interval(
                interval_id=interval.id,
                label=interval.label,
                top=interval.top,
                base=interval.base,
                interval_type=interval.interval_type,
                color=interval.color,
                comment=target_comment,
                source=target_source,
                created_at=interval.created_at,
            )
            items.append(self._preview_item(interval, replacement))
        return self._preview("edit_metadata", selected_ids, items, {"comment": comment, "comment_mode": clean_mode, "source": source})

    def preview_delete(self, interval_ids: Iterable[str]) -> InterpretationIntervalBatchPreview:
        selected_ids = self._normalize_ids(interval_ids)
        items = [self._preview_item(interval, None) for interval in self._selected_intervals(selected_ids)]
        return self._preview("delete", selected_ids, items, {})

    def confirm_assign_type(
        self, preview: InterpretationIntervalBatchPreview, *, interval_type: str, color: str | None = None
    ) -> InterpretationIntervalBatchResult:
        self._validate_confirmation(preview, "assign_type", {"interval_type": str(interval_type), "color": color})
        result = self.assign_type([item.interval_id for item in preview.items], interval_type=interval_type, color=color)
        self._record_journal(result, preview.confirmation_token)
        return result

    def confirm_edit_metadata(
        self, preview: InterpretationIntervalBatchPreview, *, comment: str | None = None,
        comment_mode: str = "replace", source: str | None = None
    ) -> InterpretationIntervalBatchResult:
        clean_mode = self._validate_metadata_request(comment, comment_mode, source)
        params = {"comment": comment, "comment_mode": clean_mode, "source": source}
        self._validate_confirmation(preview, "edit_metadata", params)
        result = self.edit_metadata([item.interval_id for item in preview.items], comment=comment, comment_mode=clean_mode, source=source)
        self._record_journal(result, preview.confirmation_token)
        return result

    def confirm_delete(self, preview: InterpretationIntervalBatchPreview) -> InterpretationIntervalBatchResult:
        self._validate_confirmation(preview, "delete", {})
        result = self.delete([item.interval_id for item in preview.items])
        self._record_journal(result, preview.confirmation_token)
        return result

    def list_journal(self, limit: int = 20) -> tuple[dict, ...]:
        entries = self.manager.state.get(self._journal_key, [])
        if not isinstance(entries, list):
            return ()
        return tuple(reversed(entries[-max(1, int(limit)):]))

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


    def edit_metadata(
        self,
        interval_ids: Iterable[str],
        *,
        comment: str | None = None,
        comment_mode: str = "replace",
        source: str | None = None,
    ) -> InterpretationIntervalBatchResult:
        """Update comment/source for several intervals as one reversible command.

        ``comment_mode`` may be ``replace`` or ``append``.  ``None`` means that
        the corresponding field must remain unchanged; an empty string is a
        valid explicit replacement.
        """

        selected_ids = self._normalize_ids(interval_ids)
        clean_mode = self._validate_metadata_request(comment, comment_mode, source)

        selected = set(selected_ids)
        current = self.manager.list_intervals()
        self._ensure_known(selected, current)

        updated: list[InterpretationInterval] = []
        changed_ids: list[str] = []
        for interval in current:
            if interval.id not in selected:
                updated.append(interval)
                continue

            target_comment, target_source = self._metadata_targets(
                interval, comment=comment, comment_mode=clean_mode, source=source
            )
            replacement = build_interpretation_interval(
                interval_id=interval.id,
                label=interval.label,
                top=interval.top,
                base=interval.base,
                interval_type=interval.interval_type,
                color=interval.color,
                comment=target_comment,
                source=target_source,
                created_at=interval.created_at,
            )
            updated.append(replacement)
            if replacement != interval:
                changed_ids.append(interval.id)

        if changed_ids:
            self.manager.replace_all(tuple(updated), action="batch_edit_metadata")
        return InterpretationIntervalBatchResult(
            action="edit_metadata",
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


    def _selected_intervals(self, selected_ids: tuple[str, ...]) -> tuple[InterpretationInterval, ...]:
        current = self.manager.list_intervals()
        selected = set(selected_ids)
        self._ensure_known(selected, current)
        by_id = {interval.id: interval for interval in current}
        return tuple(by_id[interval_id] for interval_id in selected_ids)

    @staticmethod
    def _validate_metadata_request(
        comment: str | None, comment_mode: str, source: str | None
    ) -> str:
        if comment is None and source is None:
            raise ValueError("Укажите комментарий или источник для изменения.")
        clean_mode = str(comment_mode or "replace").strip().lower()
        if clean_mode not in {"replace", "append"}:
            raise ValueError("Режим комментария должен быть replace или append.")
        return clean_mode

    @staticmethod
    def _metadata_targets(
        interval: InterpretationInterval,
        *,
        comment: str | None,
        comment_mode: str,
        source: str | None,
    ) -> tuple[str, str]:
        target_comment = interval.comment
        if comment is not None:
            clean_comment = str(comment).strip()
            if comment_mode == "append" and clean_comment:
                target_comment = (
                    f"{interval.comment.rstrip()}\n{clean_comment}"
                    if interval.comment.strip()
                    else clean_comment
                )
            elif comment_mode == "replace":
                target_comment = clean_comment
        target_source = interval.source if source is None else str(source).strip()
        return target_comment, target_source

    @staticmethod
    def _preview_item(
        current: InterpretationInterval, replacement: InterpretationInterval | None
    ) -> InterpretationIntervalBatchPreviewItem:
        target = replacement or current
        return InterpretationIntervalBatchPreviewItem(
            interval_id=current.id,
            label=current.label,
            top=current.top,
            base=current.base,
            current_type=current.interval_type,
            target_type="—" if replacement is None else target.interval_type,
            current_color=current.color,
            target_color="—" if replacement is None else target.color,
            current_comment=current.comment,
            target_comment="—" if replacement is None else target.comment,
            current_source=current.source,
            target_source="—" if replacement is None else target.source,
            will_change=replacement is None or replacement != current,
        )

    def _preview(
        self,
        action: str,
        selected_ids: tuple[str, ...],
        items: list[InterpretationIntervalBatchPreviewItem],
        params: dict,
    ) -> InterpretationIntervalBatchPreview:
        frozen_items = tuple(items)
        return InterpretationIntervalBatchPreview(
            action=action,
            selected_count=len(selected_ids),
            changed_count=sum(1 for item in frozen_items if item.will_change),
            items=frozen_items,
            confirmation_token=self._confirmation_token(action, frozen_items, params),
        )

    def _confirmation_token(
        self, action: str, items: tuple[InterpretationIntervalBatchPreviewItem, ...], params: dict
    ) -> str:
        current = {item.id: asdict(item) for item in self.manager.list_intervals()}
        payload = {
            "action": action,
            "params": params,
            "items": [asdict(item) for item in items],
            "current": {item.interval_id: current.get(item.interval_id) for item in items},
        }
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _validate_confirmation(self, preview: InterpretationIntervalBatchPreview, action: str, params: dict) -> None:
        if preview.action != action:
            raise InterpretationIntervalBatchConflict("Тип подтверждаемой операции не совпадает с preview.")
        expected = self._confirmation_token(action, preview.items, params)
        if expected != preview.confirmation_token:
            raise InterpretationIntervalBatchConflict(
                "Интервалы изменились после предварительного просмотра; сформируйте preview повторно."
            )

    def _record_journal(self, result: InterpretationIntervalBatchResult, token: str) -> None:
        entries = self.manager.state.get(self._journal_key, [])
        if not isinstance(entries, list):
            entries = []
        entries.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": result.action,
            "selected_count": result.selected_count,
            "changed_count": result.changed_count,
            "interval_ids": list(result.interval_ids),
            "confirmation_token": token,
        })
        self.manager.state[self._journal_key] = entries[-100:]

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
