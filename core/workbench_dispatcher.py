"""Atomic command dispatcher for the Modern Workbench shell.

The dispatcher is the application boundary that coordinates command execution
for navigation, tools and dock lifecycle.  Individual commands remain small
and reusable, while one normalized shell event describes the final coherent
state observed by renderers.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable, Iterable, MutableMapping
from uuid import uuid4

from core.command_framework import CommandExecutionResult, WorkbenchCommandRegistry
from core.event_bus import ApplicationEvent, ApplicationEventBus

ShellSnapshotFactory = Callable[[], dict[str, Any]]


@dataclass(frozen=True, slots=True)
class WorkbenchDispatchStep:
    """One command in an atomic Workbench shell dispatch."""

    command_id: str
    payload: dict[str, Any]

    def normalized(self) -> "WorkbenchDispatchStep":
        command_id = str(self.command_id or "").strip()
        if not command_id:
            raise ValueError("Dispatch command id must not be empty.")
        return WorkbenchDispatchStep(command_id, dict(self.payload or {}))


@dataclass(frozen=True, slots=True)
class WorkbenchShellDispatchResult:
    """Outcome of one atomic shell interaction."""

    dispatch_id: str
    primary_result: CommandExecutionResult
    command_results: tuple[CommandExecutionResult, ...]
    event: ApplicationEvent
    shell_state: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "dispatch_id": self.dispatch_id,
            "primary_command_id": self.primary_result.command_id,
            "command_ids": [result.command_id for result in self.command_results],
            "event": self.event.to_dict(),
            "shell_state": dict(self.shell_state),
        }


class WorkbenchShellDispatcher:
    """Execute related Workbench commands as one coherent shell transition."""

    EVENT_NAME = "workbench.shell.state_changed"

    def __init__(
        self,
        state: MutableMapping[str, Any],
        command_registry: WorkbenchCommandRegistry,
        snapshot_factory: ShellSnapshotFactory,
    ) -> None:
        self.state = state
        self.command_registry = command_registry
        self.snapshot_factory = snapshot_factory
        self.event_bus = ApplicationEventBus(state)

    def dispatch(
        self,
        intent: str,
        steps: Iterable[WorkbenchDispatchStep],
        *,
        metadata: dict[str, Any] | None = None,
    ) -> WorkbenchShellDispatchResult:
        """Execute all steps and publish one normalized final-state event.

        A deep state snapshot is restored when a handler raises, preventing a
        partially updated navigation/tool/dock combination from leaking to the
        renderer boundary.
        """

        clean_intent = str(intent or "").strip()
        if not clean_intent:
            raise ValueError("Workbench dispatch intent must not be empty.")
        normalized_steps = tuple(step.normalized() for step in steps)
        if not normalized_steps:
            raise ValueError("Workbench shell dispatch requires at least one command.")

        before = deepcopy(dict(self.state))
        results: list[CommandExecutionResult] = []
        dispatch_id = uuid4().hex
        try:
            for step in normalized_steps:
                result = self.command_registry.execute(step.command_id, step.payload)
                if not result.executed:
                    raise RuntimeError(result.message or f"Command was not executed: {step.command_id}")
                results.append(result)
            shell_state = dict(self.snapshot_factory())
            event = self.event_bus.publish(
                self.EVENT_NAME,
                {
                    "dispatch_id": dispatch_id,
                    "intent": clean_intent,
                    "command_ids": [result.command_id for result in results],
                    "shell_state": shell_state,
                    "metadata": dict(metadata or {}),
                },
                source="WorkbenchShellDispatcher",
            )
        except Exception:
            self.state.clear()
            self.state.update(before)
            raise

        return WorkbenchShellDispatchResult(
            dispatch_id=dispatch_id,
            primary_result=results[0],
            command_results=tuple(results),
            event=event,
            shell_state=shell_state,
        )
