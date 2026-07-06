"""Workspace infrastructure services for Gas Ratio Pro.

This module contains small, dependency-free building blocks used by the
application shell and future enterprise-grade modules. The services are kept
pure Python so they can be tested without Streamlit installed.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
from pathlib import Path
import uuid
from typing import Any, Callable, Iterable


ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def utc_now() -> str:
    """Return a stable UTC timestamp for persisted workspace records."""
    return datetime.now(timezone.utc).strftime(ISO_FORMAT)


class NotificationLevel(str, Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class WorkspaceSettings:
    """User and workspace preferences saved outside the Streamlit session."""

    theme: str = "dark"
    accent: str = "cyan"
    density: str = "compact"
    language: str = "ru"
    show_recent_activity: bool = True
    show_favorites: bool = True
    autosave_enabled: bool = True
    autosave_interval_minutes: int = 5
    default_depth_unit: str = "m"
    default_export_dir: str = "exports"

    def normalized(self) -> "WorkspaceSettings":
        """Return a sanitized copy suitable for persistence and UI rendering."""
        theme = self.theme if self.theme in {"dark", "light"} else "dark"
        density = self.density if self.density in {"compact", "comfortable"} else "compact"
        default_depth_unit = self.default_depth_unit if self.default_depth_unit in {"m", "ft"} else "m"
        interval = max(1, int(self.autosave_interval_minutes))
        return WorkspaceSettings(
            theme=theme,
            accent=self.accent.strip() or "cyan",
            density=density,
            language=self.language.strip() or "ru",
            show_recent_activity=bool(self.show_recent_activity),
            show_favorites=bool(self.show_favorites),
            autosave_enabled=bool(self.autosave_enabled),
            autosave_interval_minutes=interval,
            default_depth_unit=default_depth_unit,
            default_export_dir=self.default_export_dir.strip() or "exports",
        )


@dataclass(slots=True)
class WorkspaceConfiguration:
    """Named persisted configuration snapshot."""

    name: str
    settings: WorkspaceSettings = field(default_factory=WorkspaceSettings)
    modules: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "settings": asdict(self.settings.normalized()),
            "modules": self.modules,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "WorkspaceConfiguration":
        settings_payload = payload.get("settings") or {}
        return cls(
            name=str(payload.get("name") or "default"),
            settings=WorkspaceSettings(**{k: v for k, v in settings_payload.items() if k in WorkspaceSettings.__dataclass_fields__}).normalized(),
            modules=dict(payload.get("modules") or {}),
            created_at=str(payload.get("created_at") or utc_now()),
            updated_at=str(payload.get("updated_at") or utc_now()),
        )


class ConfigurationManager:
    """Read, write and backup workspace configuration JSON files."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.backup_dir = self.root / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, name: str) -> Path:
        safe_name = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in name.strip()) or "default"
        return self.root / f"{safe_name}.json"

    def save(self, config: WorkspaceConfiguration) -> Path:
        config = WorkspaceConfiguration(
            name=config.name,
            settings=config.settings.normalized(),
            modules=config.modules,
            created_at=config.created_at,
            updated_at=utc_now(),
        )
        path = self._path(config.name)
        path.write_text(json.dumps(config.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def load(self, name: str = "default") -> WorkspaceConfiguration:
        path = self._path(name)
        if not path.exists():
            return WorkspaceConfiguration(name=name)
        return WorkspaceConfiguration.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def backup(self, name: str = "default") -> Path:
        source = self._path(name)
        if not source.exists():
            self.save(WorkspaceConfiguration(name=name))
        stamp = utc_now().replace(":", "").replace("-", "")
        target = self.backup_dir / f"{source.stem}_{stamp}.json"
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        return target

    def list_configurations(self) -> list[str]:
        return sorted(path.stem for path in self.root.glob("*.json"))


@dataclass(slots=True)
class WorkspaceNotification:
    title: str
    message: str
    level: NotificationLevel = NotificationLevel.INFO
    source: str = "workspace"
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    created_at: str = field(default_factory=utc_now)
    read: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["level"] = self.level.value
        return payload


class NotificationCenter:
    """In-memory notification journal with filtering and acknowledgement."""

    def __init__(self):
        self._items: list[WorkspaceNotification] = []

    def push(self, title: str, message: str, level: NotificationLevel | str = NotificationLevel.INFO, source: str = "workspace") -> WorkspaceNotification:
        notification = WorkspaceNotification(
            title=title,
            message=message,
            level=NotificationLevel(level),
            source=source,
        )
        self._items.insert(0, notification)
        return notification

    def mark_read(self, notification_id: str) -> bool:
        for item in self._items:
            if item.id == notification_id:
                item.read = True
                return True
        return False

    def list(self, level: NotificationLevel | str | None = None, unread_only: bool = False) -> list[WorkspaceNotification]:
        items = self._items
        if level is not None:
            level_value = NotificationLevel(level)
            items = [item for item in items if item.level == level_value]
        if unread_only:
            items = [item for item in items if not item.read]
        return list(items)


@dataclass(slots=True)
class WorkspaceTask:
    title: str
    operation: str
    status: TaskStatus = TaskStatus.PENDING
    progress: int = 0
    message: str = ""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    def update(self, status: TaskStatus | str | None = None, progress: int | None = None, message: str | None = None) -> None:
        if status is not None:
            self.status = TaskStatus(status)
        if progress is not None:
            self.progress = max(0, min(100, int(progress)))
        if message is not None:
            self.message = message
        self.updated_at = utc_now()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        return payload


class TaskManager:
    """Queue and journal for long-running workspace operations."""

    def __init__(self):
        self._tasks: dict[str, WorkspaceTask] = {}
        self._order: list[str] = []

    def create(self, title: str, operation: str) -> WorkspaceTask:
        task = WorkspaceTask(title=title, operation=operation)
        self._tasks[task.id] = task
        self._order.insert(0, task.id)
        return task

    def update(self, task_id: str, status: TaskStatus | str | None = None, progress: int | None = None, message: str | None = None) -> WorkspaceTask:
        if task_id not in self._tasks:
            raise KeyError(f"Unknown task id: {task_id}")
        task = self._tasks[task_id]
        task.update(status=status, progress=progress, message=message)
        return task

    def list(self, status: TaskStatus | str | None = None) -> list[WorkspaceTask]:
        tasks = [self._tasks[task_id] for task_id in self._order]
        if status is not None:
            status_value = TaskStatus(status)
            tasks = [task for task in tasks if task.status == status_value]
        return tasks


@dataclass(slots=True)
class LogRecordView:
    timestamp: str
    level: str
    message: str
    source: str = "application"


class LoggingCenter:
    """Small log reader/exporter for application log files."""

    def __init__(self, log_dir: str | Path):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def append(self, message: str, level: str = "INFO", source: str = "application") -> Path:
        path = self.log_dir / "workspace.log"
        line = f"{utc_now()}\t{level.upper()}\t{source}\t{message}\n"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line)
        return path

    def read(self, level: str | None = None, contains: str | None = None, limit: int = 200) -> list[LogRecordView]:
        records: list[LogRecordView] = []
        for path in sorted(self.log_dir.glob("*.log")):
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                parts = line.split("\t", 3)
                if len(parts) == 4:
                    timestamp, record_level, source, message = parts
                else:
                    timestamp, record_level, source, message = "", "INFO", path.name, line
                if level and record_level.upper() != level.upper():
                    continue
                if contains and contains.lower() not in message.lower():
                    continue
                records.append(LogRecordView(timestamp, record_level, message, source))
        return records[-limit:]

    def export(self, target: str | Path, records: Iterable[LogRecordView] | None = None) -> Path:
        target_path = Path(target)
        source_records = list(records) if records is not None else self.read(limit=10_000)
        payload = [asdict(record) for record in source_records]
        target_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return target_path


class ServiceRegistry:
    """Shared registry for internal services and future Plugin API hooks."""

    def __init__(self):
        self._services: dict[str, Any] = {}

    def register(self, name: str, service: Any, replace: bool = False) -> None:
        key = name.strip()
        if not key:
            raise ValueError("Service name must not be empty")
        if key in self._services and not replace:
            raise KeyError(f"Service already registered: {key}")
        self._services[key] = service

    def get(self, name: str) -> Any:
        if name not in self._services:
            raise KeyError(f"Service not registered: {name}")
        return self._services[name]

    def names(self) -> list[str]:
        return sorted(self._services)

    def bind_plugin_api(self, register_callable: Callable[[str, Any], Any] | None) -> None:
        """Expose registered services to a plugin manager-like callback."""
        if register_callable is None:
            return
        for name, service in self._services.items():
            register_callable(name, service)


def build_default_workspace_services(root: str | Path) -> ServiceRegistry:
    """Create the default infrastructure service graph for the workspace."""
    root_path = Path(root)
    registry = ServiceRegistry()
    registry.register("configuration", ConfigurationManager(root_path / "configurations"))
    registry.register("notifications", NotificationCenter())
    registry.register("tasks", TaskManager())
    registry.register("logs", LoggingCenter(root_path / "logs"))
    registry.register("settings", WorkspaceSettings().normalized())
    return registry
