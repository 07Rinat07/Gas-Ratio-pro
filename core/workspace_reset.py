"""Workspace reset controller for Modern UI actions.

The application already has low-level cleanup helpers for context switches.
This module adds a user-facing, framework-neutral reset workflow for the
Modern UI: preview what will be cleared, require confirmation for destructive
context resets, clear derived tables/plots/reports, and optionally reset the
active LAS/workspace/project context.

No Streamlit dependency lives here.  The UI can call these functions from
buttons/dialogs while tests use a plain dictionary.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Literal, MutableMapping

from core.application_state import (
    ACTIVE_LAS_ID_KEY,
    ACTIVE_PROJECT_ID_KEY,
    ACTIVE_WELL_ID_KEY,
    ACTIVE_WORKSPACE_ID_KEY,
    ApplicationStateController,
)
from core.session_state_manager import (
    DEFAULT_PRESERVED_KEYS,
    SessionCleanupResult,
    clear_transient_session_state,
    is_transient_session_key,
)

WorkspaceResetMode = Literal["derived", "las_context", "workspace_context", "full_context"]
CacheClearer = Callable[[], None]

_CONTEXT_KEYS = (
    ACTIVE_PROJECT_ID_KEY,
    ACTIVE_WELL_ID_KEY,
    ACTIVE_LAS_ID_KEY,
    ACTIVE_WORKSPACE_ID_KEY,
)


@dataclass(frozen=True)
class WorkspaceResetOption:
    """UI-facing reset option metadata."""

    id: WorkspaceResetMode
    label: str
    description: str
    requires_confirmation: bool


@dataclass(frozen=True)
class WorkspaceResetPreview:
    """Dry-run information shown before a reset is executed."""

    mode: WorkspaceResetMode
    affected_keys: tuple[str, ...]
    preserved_keys: tuple[str, ...]
    context_after: dict[str, str]


@dataclass(frozen=True)
class WorkspaceResetResult:
    """Result of executing or refusing a workspace reset."""

    mode: WorkspaceResetMode
    executed: bool
    cleanup: SessionCleanupResult | None
    cache_cleared: bool
    refresh_requested: bool
    message: str

    @property
    def cleared_keys(self) -> tuple[str, ...]:
        return self.cleanup.cleared_keys if self.cleanup is not None else ()


_RESET_OPTIONS: tuple[WorkspaceResetOption, ...] = (
    WorkspaceResetOption(
        id="derived",
        label="Очистить результаты расчета",
        description=(
            "Удаляет временные таблицы, графики, отчеты, диагностику и кэш, "
            "но сохраняет активный проект, скважину и LAS."
        ),
        requires_confirmation=False,
    ),
    WorkspaceResetOption(
        id="las_context",
        label="Сбросить активный LAS",
        description=(
            "Удаляет результаты расчета и снимает выбранный LAS, сохраняя "
            "активный проект и скважину."
        ),
        requires_confirmation=True,
    ),
    WorkspaceResetOption(
        id="workspace_context",
        label="Сбросить рабочую область",
        description=(
            "Удаляет результаты расчета и снимает выбранную рабочую область, "
            "сохраняя активный проект, скважину и LAS."
        ),
        requires_confirmation=True,
    ),
    WorkspaceResetOption(
        id="full_context",
        label="Очистить текущий контекст проекта",
        description=(
            "Удаляет временные результаты и очищает активный проект, скважину, "
            "LAS и рабочую область. Файлы проекта с диска не удаляются."
        ),
        requires_confirmation=True,
    ),
)


def workspace_reset_options() -> tuple[WorkspaceResetOption, ...]:
    """Return stable reset actions for Modern UI selectors/buttons."""

    return _RESET_OPTIONS


def normalize_workspace_reset_mode(value: str | None) -> WorkspaceResetMode:
    """Normalize UI input to a supported reset mode."""

    normalized = str(value or "").strip().lower()
    aliases: dict[str, WorkspaceResetMode] = {
        "derived": "derived",
        "results": "derived",
        "calculations": "derived",
        "расчеты": "derived",
        "las": "las_context",
        "las_context": "las_context",
        "active_las": "las_context",
        "workspace": "workspace_context",
        "workspace_context": "workspace_context",
        "full": "full_context",
        "full_context": "full_context",
        "project": "full_context",
    }
    return aliases.get(normalized, "derived")


def workspace_reset_option(mode: str | None) -> WorkspaceResetOption:
    """Return reset option metadata by id with safe default."""

    reset_mode = normalize_workspace_reset_mode(mode)
    return next(option for option in _RESET_OPTIONS if option.id == reset_mode)


def _context_after_for_mode(state: MutableMapping[str, Any], mode: WorkspaceResetMode) -> dict[str, str]:
    project_id = str(state.get(ACTIVE_PROJECT_ID_KEY, "") or "")
    well_id = str(state.get(ACTIVE_WELL_ID_KEY, "") or "")
    las_id = str(state.get(ACTIVE_LAS_ID_KEY, "") or "")
    workspace_id = str(state.get(ACTIVE_WORKSPACE_ID_KEY, "") or "")

    if mode == "las_context":
        las_id = ""
    elif mode == "workspace_context":
        workspace_id = ""
    elif mode == "full_context":
        project_id = well_id = las_id = workspace_id = ""

    return {
        "project_id": project_id,
        "well_id": well_id,
        "las_id": las_id,
        "workspace_id": workspace_id,
    }


def _context_keys_changed_by_mode(state: MutableMapping[str, Any], mode: WorkspaceResetMode) -> tuple[str, ...]:
    after = _context_after_for_mode(state, mode)
    expected = {
        ACTIVE_PROJECT_ID_KEY: after["project_id"],
        ACTIVE_WELL_ID_KEY: after["well_id"],
        ACTIVE_LAS_ID_KEY: after["las_id"],
        ACTIVE_WORKSPACE_ID_KEY: after["workspace_id"],
    }
    changed: list[str] = []
    for key in _CONTEXT_KEYS:
        if str(state.get(key, "") or "") != expected[key]:
            changed.append(key)
    return tuple(changed)


class WorkspaceResetController:
    """Single entry point for Modern UI reset actions.

    The controller deliberately separates preview and execution.  UI code can
    show affected keys and require explicit confirmation before clearing active
    LAS/workspace/project context.
    """

    def __init__(self, state: MutableMapping[str, Any], *, cache_clearer: CacheClearer | None = None) -> None:
        self.state = state
        self.cache_clearer = cache_clearer
        self.state_controller = ApplicationStateController(state)

    def preview(self, mode: str | None = "derived") -> WorkspaceResetPreview:
        """Return affected/preserved state keys without mutating state."""

        reset_mode = normalize_workspace_reset_mode(mode)
        affected = [
            str(key)
            for key in self.state.keys()
            if is_transient_session_key(str(key))
        ]
        affected.extend(_context_keys_changed_by_mode(self.state, reset_mode))
        affected = sorted(set(affected))
        preserved = sorted(str(key) for key in self.state.keys() if str(key) not in affected)
        return WorkspaceResetPreview(
            mode=reset_mode,
            affected_keys=tuple(affected),
            preserved_keys=tuple(preserved),
            context_after=_context_after_for_mode(self.state, reset_mode),
        )

    def reset(
        self,
        mode: str | None = "derived",
        *,
        confirmed: bool = False,
        source: str = "workspace_reset",
        request_refresh: bool = True,
    ) -> WorkspaceResetResult:
        """Execute a reset action after confirmation rules are satisfied."""

        option = workspace_reset_option(mode)
        if option.requires_confirmation and not confirmed:
            self.state_controller.publish_event(
                "workspace.reset_confirmation_required",
                {"mode": option.id, "label": option.label},
                source=source,
            )
            return WorkspaceResetResult(
                mode=option.id,
                executed=False,
                cleanup=None,
                cache_cleared=False,
                refresh_requested=False,
                message="Требуется подтверждение действия.",
            )

        after = _context_after_for_mode(self.state, option.id)
        cleanup = clear_transient_session_state(
            self.state,
            reason=f"{option.id}_reset",
            project_id=after["project_id"],
            well_id=after["well_id"],
            las_id=after["las_id"],
            workspace_id=after["workspace_id"],
        )

        cache_cleared = False
        if self.cache_clearer is not None:
            try:
                self.cache_clearer()
                cache_cleared = True
            except Exception as exc:  # pragma: no cover - defensive runtime path
                self.state_controller.publish_event(
                    "workspace.reset_cache_clear_failed",
                    {"mode": option.id, "error": str(exc)},
                    source=source,
                )

        self.state_controller.publish_event(
            "workspace.reset_completed",
            {
                "mode": option.id,
                "cleared_keys": list(cleanup.cleared_keys),
                "context_after": cleanup.active_context,
                "cache_cleared": cache_cleared,
            },
            source=source,
        )
        if request_refresh:
            self.state_controller.request_refresh(f"{option.id}_reset", source=source)

        return WorkspaceResetResult(
            mode=option.id,
            executed=True,
            cleanup=cleanup,
            cache_cleared=cache_cleared,
            refresh_requested=request_refresh,
            message="Рабочее состояние очищено.",
        )
