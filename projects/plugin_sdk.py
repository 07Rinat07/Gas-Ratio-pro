from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import pandas as pd

from projects.project_manager import append_project_history
from projects.repository import safe_project_id
from projects.well_cards import safe_well_id

PROJECT_PLUGIN_SDK_FILE_NAME = "plugin_sdk.json"
PLUGIN_SDK_SCHEMA = "gas-ratio-pro.plugin-sdk.v1"
PLUGIN_PERMISSION_SCOPES = {
    "read:project",
    "write:project",
    "read:wells",
    "write:wells",
    "read:las",
    "write:las",
    "read:plots",
    "write:plots",
    "read:reports",
    "write:reports",
    "run:batch",
    "run:scripting",
}
PLUGIN_EXTENSION_POINTS = {
    "dashboard.card",
    "sidebar.section",
    "las.curve.processor",
    "plot.track.renderer",
    "report.block.renderer",
    "data.importer",
    "data.exporter",
    "workflow.step",
    "quality.rule",
}
PLUGIN_STATUSES = {"draft", "enabled", "disabled", "quarantined"}
PLUGIN_HOOK_EVENTS = {
    "project.opened",
    "project.saved",
    "well.created",
    "las.imported",
    "plot.rendered",
    "report.exported",
    "batch.started",
    "batch.completed",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _project_dir(root: Path | str, project_id: str) -> Path:
    return Path(root) / safe_project_id(project_id)


def _plugin_sdk_path(root: Path | str, project_id: str) -> Path:
    return _project_dir(root, project_id) / PROJECT_PLUGIN_SDK_FILE_NAME


def _json_read(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return default


def _json_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _payload(root: Path | str, project_id: str) -> dict[str, Any]:
    payload = _json_read(_plugin_sdk_path(root, project_id), {"plugins": [], "hooks": [], "developer_keys": []})
    if not isinstance(payload, dict):
        payload = {"plugins": [], "hooks": [], "developer_keys": []}
    payload.setdefault("plugins", [])
    payload.setdefault("hooks", [])
    payload.setdefault("developer_keys", [])
    return payload


def _clean_text(value: Any, field_label: str, *, max_length: int = 240, required: bool = False) -> str:
    text = "" if value is None else str(value).strip()
    if required and not text:
        raise ValueError(f"{field_label}: значение обязательно.")
    if len(text) > max_length:
        raise ValueError(f"{field_label}: максимум {max_length} символов.")
    return text


def _safe_plugin_id(value: Any, *, default: str = "plugin") -> str:
    text = _clean_text(value, "Plugin ID", max_length=160) or default
    normalized = re.sub(r"[^0-9A-Za-zА-Яа-я_.-]+", "-", text).strip("-_.").lower() or default
    return safe_well_id(normalized.replace(".", "-"))


def _normalize_version(value: Any) -> str:
    text = _clean_text(value, "Версия", max_length=40) or "0.1.0"
    if not re.match(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$", text):
        raise ValueError("Версия plugin manifest должна быть в формате SemVer, например 0.1.0.")
    return text


def _normalize_status(value: Any) -> str:
    status = _clean_text(value, "Статус", max_length=40).lower() or "draft"
    if status not in PLUGIN_STATUSES:
        raise ValueError(f"Статус plugin должен быть одним из: {', '.join(sorted(PLUGIN_STATUSES))}.")
    return status


def _normalize_sequence(values: Sequence[Any] | None) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(item).strip() for item in (values or ()) if str(item).strip()))


@dataclass(frozen=True)
class PluginManifest:
    """Validated metadata contract for one GAS RATIO PRO plugin."""

    id: str
    name: str
    version: str = "0.1.0"
    entry_point: str = "plugin.py"
    description: str = ""
    author: str = ""
    min_app_version: str = "0.1.0"
    permissions: tuple[str, ...] = ()
    extension_points: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    status: str = "draft"
    created_at: str = ""
    updated_at: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PluginHook:
    id: str
    plugin_id: str
    event: str
    handler: str
    priority: int = 100
    enabled: bool = True
    description: str = ""


@dataclass(frozen=True)
class PluginDeveloperKey:
    id: str
    plugin_id: str
    label: str
    scopes: tuple[str, ...]
    created_at: str = ""
    revoked: bool = False


@dataclass(frozen=True)
class PluginValidationIssue:
    code: str
    message: str
    severity: str = "error"
    plugin_id: str = ""
    field: str = ""


@dataclass(frozen=True)
class PluginSdkSummary:
    plugins: int
    enabled: int
    hooks: int
    developer_keys: int
    extension_points: tuple[str, ...]
    permissions: tuple[str, ...]


def normalize_plugin_manifest(raw: PluginManifest | Mapping[str, Any]) -> PluginManifest:
    if isinstance(raw, PluginManifest):
        manifest = raw
    elif isinstance(raw, Mapping):
        now = _utc_now()
        manifest = PluginManifest(
            id=_safe_plugin_id(raw.get("id") or raw.get("name")),
            name=_clean_text(raw.get("name"), "Название plugin", required=True),
            version=_normalize_version(raw.get("version") or "0.1.0"),
            entry_point=_clean_text(raw.get("entry_point") or "plugin.py", "Entry point", max_length=180, required=True),
            description=_clean_text(raw.get("description"), "Описание", max_length=1000),
            author=_clean_text(raw.get("author"), "Автор", max_length=160),
            min_app_version=_normalize_version(raw.get("min_app_version") or "0.1.0"),
            permissions=_normalize_sequence(raw.get("permissions")),
            extension_points=_normalize_sequence(raw.get("extension_points")),
            tags=_normalize_sequence(raw.get("tags")),
            status=_normalize_status(raw.get("status") or "draft"),
            created_at=_clean_text(raw.get("created_at") or now, "Дата создания", max_length=80),
            updated_at=_clean_text(raw.get("updated_at") or now, "Дата обновления", max_length=80),
            metadata=raw.get("metadata", {}) if isinstance(raw.get("metadata", {}), Mapping) else {},
        )
    else:
        raise TypeError("Plugin manifest должен быть PluginManifest или mapping.")

    return PluginManifest(
        id=_safe_plugin_id(manifest.id),
        name=_clean_text(manifest.name, "Название plugin", required=True),
        version=_normalize_version(manifest.version),
        entry_point=_clean_text(manifest.entry_point or "plugin.py", "Entry point", max_length=180, required=True),
        description=_clean_text(manifest.description, "Описание", max_length=1000),
        author=_clean_text(manifest.author, "Автор", max_length=160),
        min_app_version=_normalize_version(manifest.min_app_version or "0.1.0"),
        permissions=_normalize_sequence(manifest.permissions),
        extension_points=_normalize_sequence(manifest.extension_points),
        tags=_normalize_sequence(manifest.tags),
        status=_normalize_status(manifest.status),
        created_at=_clean_text(manifest.created_at or _utc_now(), "Дата создания", max_length=80),
        updated_at=_clean_text(manifest.updated_at or _utc_now(), "Дата обновления", max_length=80),
        metadata=dict(manifest.metadata),
    )


def plugin_manifest_to_dict(manifest: PluginManifest) -> dict[str, Any]:
    return {
        "schema": PLUGIN_SDK_SCHEMA,
        "id": manifest.id,
        "name": manifest.name,
        "version": manifest.version,
        "entry_point": manifest.entry_point,
        "description": manifest.description,
        "author": manifest.author,
        "min_app_version": manifest.min_app_version,
        "permissions": list(manifest.permissions),
        "extension_points": list(manifest.extension_points),
        "tags": list(manifest.tags),
        "status": manifest.status,
        "created_at": manifest.created_at,
        "updated_at": manifest.updated_at,
        "metadata": dict(manifest.metadata),
    }


def _manifest_from_dict(row: Mapping[str, Any]) -> PluginManifest:
    return normalize_plugin_manifest(row)


def normalize_plugin_hook(raw: PluginHook | Mapping[str, Any]) -> PluginHook:
    if isinstance(raw, PluginHook):
        hook = raw
    elif isinstance(raw, Mapping):
        hook = PluginHook(
            id=_safe_plugin_id(raw.get("id") or f"{raw.get('plugin_id', 'plugin')}-{raw.get('event', 'event')}-{raw.get('handler', 'handler')}", default="hook"),
            plugin_id=_safe_plugin_id(raw.get("plugin_id"), default="plugin"),
            event=_clean_text(raw.get("event"), "Hook event", max_length=80, required=True),
            handler=_clean_text(raw.get("handler"), "Hook handler", max_length=180, required=True),
            priority=int(raw.get("priority") or 100),
            enabled=bool(raw.get("enabled", True)),
            description=_clean_text(raw.get("description"), "Описание hook", max_length=500),
        )
    else:
        raise TypeError("Plugin hook должен быть PluginHook или mapping.")
    if hook.event not in PLUGIN_HOOK_EVENTS:
        raise ValueError(f"Hook event не поддерживается: {hook.event}.")
    return PluginHook(
        id=_safe_plugin_id(hook.id, default="hook"),
        plugin_id=_safe_plugin_id(hook.plugin_id, default="plugin"),
        event=hook.event,
        handler=_clean_text(hook.handler, "Hook handler", max_length=180, required=True),
        priority=int(hook.priority),
        enabled=bool(hook.enabled),
        description=_clean_text(hook.description, "Описание hook", max_length=500),
    )


def plugin_hook_to_dict(hook: PluginHook) -> dict[str, Any]:
    return {**hook.__dict__}


def _hook_from_dict(row: Mapping[str, Any]) -> PluginHook:
    return normalize_plugin_hook(row)


def validate_plugin_manifest(manifest: PluginManifest | Mapping[str, Any]) -> tuple[PluginValidationIssue, ...]:
    issues: list[PluginValidationIssue] = []
    try:
        normalized = normalize_plugin_manifest(manifest)
    except Exception as exc:
        return (PluginValidationIssue("invalid_manifest", str(exc), "error"),)

    if not normalized.extension_points:
        issues.append(PluginValidationIssue("no_extension_points", "Plugin не объявляет extension points.", "warning", normalized.id, "extension_points"))
    for permission in normalized.permissions:
        if permission not in PLUGIN_PERMISSION_SCOPES:
            issues.append(PluginValidationIssue("unknown_permission", f"Неизвестный permission scope: {permission}.", "error", normalized.id, "permissions"))
    for point in normalized.extension_points:
        if point not in PLUGIN_EXTENSION_POINTS:
            issues.append(PluginValidationIssue("unknown_extension_point", f"Неизвестный extension point: {point}.", "error", normalized.id, "extension_points"))
    if not normalized.entry_point.endswith(".py"):
        issues.append(PluginValidationIssue("invalid_entry_point", "Entry point должен ссылаться на Python-файл.", "error", normalized.id, "entry_point"))
    if normalized.status == "enabled" and any(issue.severity == "error" for issue in issues):
        issues.append(PluginValidationIssue("enabled_with_errors", "Plugin нельзя включать при ошибках manifest.", "error", normalized.id, "status"))
    return tuple(issues)


def create_plugin_manifest_template(name: str, *, plugin_id: str = "", extension_points: Sequence[str] | None = None) -> dict[str, Any]:
    manifest = normalize_plugin_manifest(
        {
            "id": plugin_id or name,
            "name": name,
            "version": "0.1.0",
            "entry_point": "plugin.py",
            "description": "",
            "author": "",
            "min_app_version": "0.1.0",
            "permissions": ["read:project"],
            "extension_points": list(extension_points or ("dashboard.card",)),
            "tags": ["custom"],
            "status": "draft",
        }
    )
    return plugin_manifest_to_dict(manifest)


def create_plugin_scaffold(root: Path | str, plugin_name: str, *, plugin_id: str = "", extension_points: Sequence[str] | None = None) -> Path:
    manifest = create_plugin_manifest_template(plugin_name, plugin_id=plugin_id, extension_points=extension_points)
    plugin_dir = Path(root) / "plugins" / manifest["id"]
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "plugin.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (plugin_dir / "plugin.py").write_text(
        "\"\"\"GAS RATIO PRO plugin entry point.\"\"\"\n\n"
        "def register(api):\n"
        "    \"\"\"Register plugin services, hooks or UI descriptors through the SDK API.\"\"\"\n"
        "    api.register_metadata({'name': '" + manifest["name"].replace("'", "\\'") + "'})\n",
        encoding="utf-8",
    )
    (plugin_dir / "README.md").write_text(f"# {manifest['name']}\n\nCustom GAS RATIO PRO plugin.\n", encoding="utf-8")
    return plugin_dir


def register_plugin(root: Path | str, project_id: str, manifest: PluginManifest | Mapping[str, Any]) -> PluginManifest:
    normalized = normalize_plugin_manifest(manifest)
    issues = validate_plugin_manifest(normalized)
    if any(issue.severity == "error" for issue in issues):
        details = "; ".join(issue.message for issue in issues if issue.severity == "error")
        raise ValueError(f"Plugin manifest содержит ошибки: {details}")
    payload = _payload(root, project_id)
    plugins = [row for row in payload.get("plugins", []) if row.get("id") != normalized.id]
    plugins.append(plugin_manifest_to_dict(normalized))
    _json_write(_plugin_sdk_path(root, project_id), {**payload, "plugins": plugins})
    append_project_history(root, project_id, "plugin_registered", f"Зарегистрирован plugin {normalized.name}", object_type="plugin", object_id=normalized.id)
    return normalized


def list_plugins(root: Path | str, project_id: str, *, status: str | None = None) -> tuple[PluginManifest, ...]:
    rows = _payload(root, project_id).get("plugins", [])
    plugins = tuple(_manifest_from_dict(row) for row in rows if isinstance(row, Mapping))
    if status:
        normalized_status = _normalize_status(status)
        plugins = tuple(plugin for plugin in plugins if plugin.status == normalized_status)
    return tuple(sorted(plugins, key=lambda item: (item.name.lower(), item.version)))


def get_plugin(root: Path | str, project_id: str, plugin_id: str) -> PluginManifest:
    target = _safe_plugin_id(plugin_id)
    for plugin in list_plugins(root, project_id):
        if plugin.id == target:
            return plugin
    raise KeyError(f"Plugin не найден: {plugin_id}")


def update_plugin_status(root: Path | str, project_id: str, plugin_id: str, status: str) -> PluginManifest:
    target = _safe_plugin_id(plugin_id)
    new_status = _normalize_status(status)
    payload = _payload(root, project_id)
    updated: list[dict[str, Any]] = []
    result: PluginManifest | None = None
    for row in payload.get("plugins", []):
        plugin = _manifest_from_dict(row)
        if plugin.id == target:
            plugin = PluginManifest(**{**plugin.__dict__, "status": new_status, "updated_at": _utc_now()})
            if new_status == "enabled":
                issues = validate_plugin_manifest(plugin)
                if any(issue.severity == "error" for issue in issues):
                    raise ValueError("Plugin нельзя включить: manifest содержит ошибки.")
            result = plugin
        updated.append(plugin_manifest_to_dict(plugin))
    if result is None:
        raise KeyError(f"Plugin не найден: {plugin_id}")
    _json_write(_plugin_sdk_path(root, project_id), {**payload, "plugins": updated})
    append_project_history(root, project_id, "plugin_status_updated", f"Статус plugin {result.name}: {new_status}", object_type="plugin", object_id=result.id)
    return result


def delete_plugin(root: Path | str, project_id: str, plugin_id: str) -> bool:
    target = _safe_plugin_id(plugin_id)
    payload = _payload(root, project_id)
    before = len(payload.get("plugins", []))
    plugins = [row for row in payload.get("plugins", []) if row.get("id") != target]
    hooks = [row for row in payload.get("hooks", []) if row.get("plugin_id") != target]
    payload = {**payload, "plugins": plugins, "hooks": hooks}
    _json_write(_plugin_sdk_path(root, project_id), payload)
    removed = len(plugins) != before
    if removed:
        append_project_history(root, project_id, "plugin_deleted", f"Удален plugin {target}", object_type="plugin", object_id=target)
    return removed


def register_plugin_hook(root: Path | str, project_id: str, hook: PluginHook | Mapping[str, Any]) -> PluginHook:
    normalized = normalize_plugin_hook(hook)
    get_plugin(root, project_id, normalized.plugin_id)
    payload = _payload(root, project_id)
    hooks = [row for row in payload.get("hooks", []) if row.get("id") != normalized.id]
    hooks.append(plugin_hook_to_dict(normalized))
    _json_write(_plugin_sdk_path(root, project_id), {**payload, "hooks": hooks})
    append_project_history(root, project_id, "plugin_hook_registered", f"Зарегистрирован hook {normalized.event}", object_type="plugin", object_id=normalized.plugin_id)
    return normalized


def list_plugin_hooks(root: Path | str, project_id: str, *, plugin_id: str | None = None, event: str | None = None) -> tuple[PluginHook, ...]:
    hooks = tuple(_hook_from_dict(row) for row in _payload(root, project_id).get("hooks", []) if isinstance(row, Mapping))
    if plugin_id:
        target = _safe_plugin_id(plugin_id)
        hooks = tuple(hook for hook in hooks if hook.plugin_id == target)
    if event:
        hooks = tuple(hook for hook in hooks if hook.event == event)
    return tuple(sorted(hooks, key=lambda item: (item.priority, item.event, item.plugin_id)))


def build_plugin_api_registry(plugins: Sequence[PluginManifest], hooks: Sequence[PluginHook] = ()) -> dict[str, Any]:
    enabled_plugins = [plugin for plugin in plugins if plugin.status == "enabled"]
    return {
        "schema": PLUGIN_SDK_SCHEMA,
        "plugins": [plugin_manifest_to_dict(plugin) for plugin in enabled_plugins],
        "extension_points": {point: [plugin.id for plugin in enabled_plugins if point in plugin.extension_points] for point in sorted(PLUGIN_EXTENSION_POINTS)},
        "hooks": [plugin_hook_to_dict(hook) for hook in hooks if hook.enabled and any(plugin.id == hook.plugin_id for plugin in enabled_plugins)],
        "permissions": sorted({permission for plugin in enabled_plugins for permission in plugin.permissions}),
    }


def issue_rows(issues: Sequence[PluginValidationIssue]) -> list[dict[str, Any]]:
    return [
        {
            "Plugin": issue.plugin_id,
            "Код": issue.code,
            "Поле": issue.field,
            "Уровень": issue.severity,
            "Сообщение": issue.message,
        }
        for issue in issues
    ]


def build_plugin_validation_table(issues: Sequence[PluginValidationIssue]) -> pd.DataFrame:
    return pd.DataFrame(issue_rows(issues), columns=["Plugin", "Код", "Поле", "Уровень", "Сообщение"])


def build_plugin_table(plugins: Sequence[PluginManifest]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ID": plugin.id,
                "Название": plugin.name,
                "Версия": plugin.version,
                "Статус": plugin.status,
                "Extension points": ", ".join(plugin.extension_points),
                "Permissions": ", ".join(plugin.permissions),
                "Entry point": plugin.entry_point,
                "Обновлен": plugin.updated_at,
            }
            for plugin in plugins
        ],
        columns=["ID", "Название", "Версия", "Статус", "Extension points", "Permissions", "Entry point", "Обновлен"],
    )


def build_plugin_hook_table(hooks: Sequence[PluginHook]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ID": hook.id,
                "Plugin": hook.plugin_id,
                "Event": hook.event,
                "Handler": hook.handler,
                "Priority": hook.priority,
                "Enabled": hook.enabled,
            }
            for hook in hooks
        ],
        columns=["ID", "Plugin", "Event", "Handler", "Priority", "Enabled"],
    )


def summarize_plugin_sdk(root: Path | str, project_id: str) -> PluginSdkSummary:
    plugins = list_plugins(root, project_id)
    hooks = list_plugin_hooks(root, project_id)
    payload = _payload(root, project_id)
    keys = payload.get("developer_keys", []) if isinstance(payload.get("developer_keys", []), list) else []
    return PluginSdkSummary(
        plugins=len(plugins),
        enabled=sum(1 for plugin in plugins if plugin.status == "enabled"),
        hooks=len(hooks),
        developer_keys=len(keys),
        extension_points=tuple(sorted(PLUGIN_EXTENSION_POINTS)),
        permissions=tuple(sorted(PLUGIN_PERMISSION_SCOPES)),
    )


def export_plugin_manifest_json(manifest: PluginManifest | Mapping[str, Any]) -> str:
    return json.dumps(plugin_manifest_to_dict(normalize_plugin_manifest(manifest)), ensure_ascii=False, indent=2)


def import_plugin_manifest_json(content: str | bytes) -> PluginManifest:
    text = content.decode("utf-8") if isinstance(content, bytes) else content
    raw = json.loads(text)
    if not isinstance(raw, Mapping):
        raise ValueError("Plugin manifest JSON должен быть объектом.")
    return normalize_plugin_manifest(raw)
