"""Framework-neutral command registry for the Modern Workbench.

The command framework is the first boundary of the Workbench sprint.  It keeps
UI buttons, keyboard shortcuts and future command-palette entries as plain data
instead of hard-coding actions inside Streamlit render functions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, MutableMapping

from core.event_bus import ApplicationEvent, ApplicationEventBus
from core.workbench_runtime_diagnostics import record_runtime_exception

CommandHandler = Callable[[dict[str, Any]], Any]


@dataclass(frozen=True, slots=True)
class WorkbenchCommand:
    """Serializable command descriptor used by toolbar and command palette UI."""

    id: str
    title: str
    group: str = "workspace"
    description: str = ""
    shortcut: str = ""
    icon: str = ""
    enabled: bool = True
    visible: bool = True
    payload: dict[str, Any] = field(default_factory=dict)

    def normalized(self) -> "WorkbenchCommand":
        """Return a sanitized command descriptor.

        Command ids are intentionally limited to stable tokens because they are
        persisted in session state, used by tests and can later be exposed to a
        plugin API.
        """

        clean_id = str(self.id or "").strip()
        if not clean_id:
            raise ValueError("Command id must not be empty.")
        clean_title = str(self.title or "").strip()
        if not clean_title:
            raise ValueError("Command title must not be empty.")
        return WorkbenchCommand(
            id=clean_id,
            title=clean_title,
            group=str(self.group or "workspace").strip() or "workspace",
            description=str(self.description or "").strip(),
            shortcut=str(self.shortcut or "").strip(),
            icon=str(self.icon or "").strip(),
            enabled=bool(self.enabled),
            visible=bool(self.visible),
            payload=dict(self.payload or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        command = self.normalized()
        return {
            "id": command.id,
            "title": command.title,
            "group": command.group,
            "description": command.description,
            "shortcut": command.shortcut,
            "icon": command.icon,
            "enabled": command.enabled,
            "visible": command.visible,
            "payload": dict(command.payload),
        }


@dataclass(frozen=True, slots=True)
class CommandExecutionResult:
    """Result returned after a command execution attempt."""

    command_id: str
    executed: bool
    message: str = ""
    result: Any = None
    event: ApplicationEvent | None = None


class WorkbenchCommandRegistry:
    """Register, list and execute Workbench commands without UI coupling."""

    def __init__(self, state: MutableMapping[str, Any] | None = None) -> None:
        self.state = state if state is not None else {}
        self._commands: dict[str, WorkbenchCommand] = {}
        self._handlers: dict[str, CommandHandler] = {}

    def register(self, command: WorkbenchCommand, handler: CommandHandler | None = None, *, replace: bool = False) -> WorkbenchCommand:
        normalized = command.normalized()
        if normalized.id in self._commands and not replace:
            raise KeyError(f"Command already registered: {normalized.id}")
        self._commands[normalized.id] = normalized
        if handler is not None:
            self._handlers[normalized.id] = handler
        return normalized

    def register_many(self, commands: Iterable[WorkbenchCommand]) -> tuple[WorkbenchCommand, ...]:
        registered: list[WorkbenchCommand] = []
        for command in commands:
            registered.append(self.register(command, replace=True))
        return tuple(registered)

    def get(self, command_id: str) -> WorkbenchCommand:
        clean_id = str(command_id or "").strip()
        if clean_id not in self._commands:
            raise KeyError(f"Unknown command: {clean_id}")
        return self._commands[clean_id]

    def list(self, *, group: str | None = None, visible_only: bool = True) -> tuple[WorkbenchCommand, ...]:
        commands = sorted(self._commands.values(), key=lambda item: (item.group, item.title, item.id))
        if group is not None:
            commands = [command for command in commands if command.group == group]
        if visible_only:
            commands = [command for command in commands if command.visible]
        return tuple(commands)

    def execute(self, command_id: str, payload: dict[str, Any] | None = None) -> CommandExecutionResult:
        command = self.get(command_id)
        if not command.enabled:
            return CommandExecutionResult(command.id, executed=False, message="Command is disabled.")

        merged_payload = dict(command.payload)
        merged_payload.update(dict(payload or {}))
        handler = self._handlers.get(command.id)
        try:
            handler_result = handler(merged_payload) if handler is not None else None
        except Exception as exc:
            incident = record_runtime_exception(
                self.state,
                exc,
                boundary="command",
                operation=command.id,
                context={"payload_keys": tuple(sorted(merged_payload))},
            )
            event = ApplicationEventBus(self.state).publish(
                "workbench.command_failed",
                {"command_id": command.id, "correlation_id": incident["correlation_id"]},
                source="WorkbenchCommandRegistry",
            )
            return CommandExecutionResult(
                command.id,
                executed=False,
                message=f"{exc}. Error ID: {incident['correlation_id']}",
                result=None,
                event=event,
            )
        event = ApplicationEventBus(self.state).publish(
            "workbench.command_executed",
            {"command_id": command.id, "payload": merged_payload},
            source="WorkbenchCommandRegistry",
        )
        return CommandExecutionResult(command.id, executed=True, message="Command executed.", result=handler_result, event=event)


def default_workbench_commands() -> tuple[WorkbenchCommand, ...]:
    """Return the first stable Workbench command set."""

    return (
        WorkbenchCommand("workspace.open", "Открыть рабочую область", "workspace", "Открыть выбранный проект или LAS.", "Ctrl+O", "folder"),
        WorkbenchCommand("workspace.save_session", "Сохранить сессию", "workspace", "Сохранить легкое состояние Workbench.", "Ctrl+S", "save"),
        WorkbenchCommand("workspace.restore_session", "Восстановить сессию", "workspace", "Восстановить ранее сохраненную сессию.", "Ctrl+Shift+O", "restore"),
        WorkbenchCommand("workspace.reset", "Сбросить рабочую область", "workspace", "Очистить производные данные текущей области.", "Ctrl+Shift+R", "reset"),
        WorkbenchCommand("export.bundle", "Экспортировать пакет", "export", "Создать HTML PDF DOCX пакет отчета.", "Ctrl+E", "export"),
    )
