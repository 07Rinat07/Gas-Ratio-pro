"""Renderer-neutral commands and state controller for interactive viewports.

The module deliberately contains no UI or renderer dependencies. Adapters emit
serializable :class:`ViewportCommand` values; the controller applies them to an
:class:`InteractiveViewport` and owns deterministic undo/redo history.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from typing import Any, Mapping

from services.visualization_interactive_viewport import InteractiveViewport


class ViewportCommandType(str, Enum):
    """Supported viewport interaction operations."""

    PAN_DOMAIN = "pan_domain"
    PAN_PIXELS = "pan_pixels"
    ZOOM = "zoom"
    ZOOM_AT_SCREEN = "zoom_at_screen"
    FIT = "fit"
    SET_RANGE = "set_range"
    RESET = "reset"


@dataclass(frozen=True, slots=True)
class ViewportCommand:
    """Serializable renderer-neutral viewport command."""

    kind: ViewportCommandType
    parameters: Mapping[str, Any] = field(default_factory=dict)
    source: str = ""
    correlation_id: str = ""

    @classmethod
    def pan_domain(cls, delta: float, **metadata: str) -> "ViewportCommand":
        return cls(ViewportCommandType.PAN_DOMAIN, {"delta": float(delta)}, **metadata)

    @classmethod
    def pan_pixels(cls, delta_pixels: float, **metadata: str) -> "ViewportCommand":
        return cls(
            ViewportCommandType.PAN_PIXELS,
            {"delta_pixels": float(delta_pixels)},
            **metadata,
        )

    @classmethod
    def zoom(
        cls,
        factor: float,
        *,
        anchor_domain: float | None = None,
        **metadata: str,
    ) -> "ViewportCommand":
        parameters: dict[str, Any] = {"factor": float(factor)}
        if anchor_domain is not None:
            parameters["anchor_domain"] = float(anchor_domain)
        return cls(ViewportCommandType.ZOOM, parameters, **metadata)

    @classmethod
    def zoom_at_screen(
        cls,
        factor: float,
        screen_coordinate: float,
        **metadata: str,
    ) -> "ViewportCommand":
        return cls(
            ViewportCommandType.ZOOM_AT_SCREEN,
            {
                "factor": float(factor),
                "screen_coordinate": float(screen_coordinate),
            },
            **metadata,
        )

    @classmethod
    def fit(cls, domain_start: float, domain_stop: float, **metadata: str) -> "ViewportCommand":
        return cls(
            ViewportCommandType.FIT,
            {"domain_start": float(domain_start), "domain_stop": float(domain_stop)},
            **metadata,
        )

    @classmethod
    def set_range(
        cls,
        domain_start: float,
        domain_stop: float,
        **metadata: str,
    ) -> "ViewportCommand":
        return cls(
            ViewportCommandType.SET_RANGE,
            {"domain_start": float(domain_start), "domain_stop": float(domain_stop)},
            **metadata,
        )

    @classmethod
    def reset(cls, **metadata: str) -> "ViewportCommand":
        return cls(ViewportCommandType.RESET, {}, **metadata)

    @property
    def valid(self) -> bool:
        try:
            self._validated_parameters()
        except (TypeError, ValueError):
            return False
        return True

    def apply(
        self,
        viewport: InteractiveViewport,
        *,
        initial_viewport: InteractiveViewport,
    ) -> InteractiveViewport:
        """Apply the command without mutating either viewport."""

        if not viewport.valid or not initial_viewport.valid:
            raise ValueError("viewport command requires valid current and initial viewports")

        values = self._validated_parameters()
        if self.kind is ViewportCommandType.PAN_DOMAIN:
            return viewport.pan_domain(values["delta"])
        if self.kind is ViewportCommandType.PAN_PIXELS:
            return viewport.pan_pixels(values["delta_pixels"])
        if self.kind is ViewportCommandType.ZOOM:
            return viewport.zoom(values["factor"], anchor_domain=values.get("anchor_domain"))
        if self.kind is ViewportCommandType.ZOOM_AT_SCREEN:
            return viewport.zoom_at_screen(values["factor"], values["screen_coordinate"])
        if self.kind in (ViewportCommandType.FIT, ViewportCommandType.SET_RANGE):
            return viewport.fit(values["domain_start"], values["domain_stop"])
        if self.kind is ViewportCommandType.RESET:
            return initial_viewport
        raise ValueError(f"unsupported viewport command: {self.kind}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "visualization.interactive.viewport-command",
            "version": "1.0",
            "kind": self.kind.value,
            "parameters": dict(self.parameters),
            "source": self.source,
            "correlation_id": self.correlation_id,
            "valid": self.valid,
            "renderer_neutral": True,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ViewportCommand":
        try:
            kind = ViewportCommandType(str(value.get("kind") or ""))
        except ValueError as exc:
            raise ValueError("unknown viewport command kind") from exc
        raw_parameters = value.get("parameters")
        parameters = dict(raw_parameters) if isinstance(raw_parameters, Mapping) else {}
        return cls(
            kind=kind,
            parameters=parameters,
            source=str(value.get("source") or ""),
            correlation_id=str(value.get("correlation_id") or ""),
        )

    def _validated_parameters(self) -> dict[str, float]:
        raw = dict(self.parameters)
        if self.kind is ViewportCommandType.RESET:
            return {}
        if self.kind is ViewportCommandType.PAN_DOMAIN:
            return {"delta": _finite(raw, "delta")}
        if self.kind is ViewportCommandType.PAN_PIXELS:
            return {"delta_pixels": _finite(raw, "delta_pixels")}
        if self.kind is ViewportCommandType.ZOOM:
            result = {"factor": _positive(raw, "factor")}
            if raw.get("anchor_domain") is not None:
                result["anchor_domain"] = _finite(raw, "anchor_domain")
            return result
        if self.kind is ViewportCommandType.ZOOM_AT_SCREEN:
            return {
                "factor": _positive(raw, "factor"),
                "screen_coordinate": _finite(raw, "screen_coordinate"),
            }
        if self.kind in (ViewportCommandType.FIT, ViewportCommandType.SET_RANGE):
            start = _finite(raw, "domain_start")
            stop = _finite(raw, "domain_stop")
            if stop <= start:
                raise ValueError("domain_stop must be greater than domain_start")
            return {"domain_start": start, "domain_stop": stop}
        raise ValueError(f"unsupported viewport command: {self.kind}")


@dataclass(frozen=True, slots=True)
class ViewportTransition:
    """One committed controller transition used for diagnostics and history."""

    command: ViewportCommand
    before: InteractiveViewport
    after: InteractiveViewport

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": self.command.to_dict(),
            "before": self.before.to_dict(),
            "after": self.after.to_dict(),
            "changed": self.before != self.after,
        }


class ViewportController:
    """Stateful command executor with bounded deterministic undo/redo history."""

    def __init__(self, initial_viewport: InteractiveViewport, *, history_limit: int = 100) -> None:
        if not initial_viewport.valid:
            raise ValueError("initial viewport must be valid")
        if int(history_limit) < 0:
            raise ValueError("history_limit cannot be negative")
        self._initial = initial_viewport
        self._current = initial_viewport
        self._history_limit = int(history_limit)
        self._undo: list[ViewportTransition] = []
        self._redo: list[ViewportTransition] = []

    @property
    def initial(self) -> InteractiveViewport:
        return self._initial

    @property
    def current(self) -> InteractiveViewport:
        return self._current

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    @property
    def undo_depth(self) -> int:
        return len(self._undo)

    @property
    def redo_depth(self) -> int:
        return len(self._redo)

    def execute(self, command: ViewportCommand) -> InteractiveViewport:
        """Apply and commit a command; no-op transitions are not recorded."""

        after = command.apply(self._current, initial_viewport=self._initial)
        if after == self._current:
            return self._current

        transition = ViewportTransition(command=command, before=self._current, after=after)
        self._current = after
        self._redo.clear()
        if self._history_limit > 0:
            self._undo.append(transition)
            overflow = len(self._undo) - self._history_limit
            if overflow > 0:
                del self._undo[:overflow]
        return self._current

    def undo(self) -> InteractiveViewport:
        if not self._undo:
            return self._current
        transition = self._undo.pop()
        self._current = transition.before
        self._redo.append(transition)
        return self._current

    def redo(self) -> InteractiveViewport:
        if not self._redo:
            return self._current
        transition = self._redo.pop()
        self._current = transition.after
        self._undo.append(transition)
        return self._current

    def clear_history(self) -> None:
        self._undo.clear()
        self._redo.clear()

    def snapshot(self) -> dict[str, Any]:
        """Return a compact serializable controller state for Workspace/Event Bus."""

        return {
            "schema": "visualization.interactive.viewport-controller",
            "version": "1.0",
            "initial": self._initial.to_dict(),
            "current": self._current.to_dict(),
            "history_limit": self._history_limit,
            "undo_depth": self.undo_depth,
            "redo_depth": self.redo_depth,
            "can_undo": self.can_undo,
            "can_redo": self.can_redo,
            "renderer_neutral": True,
        }


def _finite(parameters: Mapping[str, Any], name: str) -> float:
    if name not in parameters:
        raise ValueError(f"missing viewport command parameter: {name}")
    try:
        value = float(parameters[name])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"viewport command parameter {name} must be numeric") from exc
    if not isfinite(value):
        raise ValueError(f"viewport command parameter {name} must be finite")
    return value


def _positive(parameters: Mapping[str, Any], name: str) -> float:
    value = _finite(parameters, name)
    if value <= 0:
        raise ValueError(f"viewport command parameter {name} must be positive")
    return value
