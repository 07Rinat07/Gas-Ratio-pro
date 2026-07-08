from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence, Any

from projects.plugin_sdk import (
    PluginHook,
    PluginManifest,
    PluginSdkSummary,
    build_plugin_api_registry,
    create_plugin_manifest_template,
    delete_plugin,
    list_plugin_hooks,
    list_plugins,
    register_plugin,
    register_plugin_hook,
    summarize_plugin_sdk,
    update_plugin_status,
)
from projects.repository import DEFAULT_PROJECTS_ROOT, safe_project_id


@dataclass(frozen=True)
class PluginDeleteResult:
    project_id: str
    plugin_id: str
    deleted: bool


class PluginManagerService:
    """Service-layer foundation for the future Plugin API.

    Sprint 1 does not execute arbitrary plugin code. It only standardizes plugin
    manifests, hooks, lifecycle status and registry summaries so that future
    modules can extend the application without changing core UI code.
    """

    def __init__(self, root: Path | str = DEFAULT_PROJECTS_ROOT) -> None:
        self.root = Path(root)

    def manifest_template(
        self,
        name: str,
        *,
        plugin_id: str = "",
        extension_points: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        return create_plugin_manifest_template(name, plugin_id=plugin_id, extension_points=extension_points)

    def register(self, project_id: str, manifest: PluginManifest | Mapping[str, Any]) -> PluginManifest:
        return register_plugin(self.root, safe_project_id(project_id), manifest)

    def list(self, project_id: str, *, status: str | None = None) -> tuple[PluginManifest, ...]:
        return list_plugins(self.root, safe_project_id(project_id), status=status)

    def enable(self, project_id: str, plugin_id: str) -> PluginManifest:
        return update_plugin_status(self.root, safe_project_id(project_id), plugin_id, "enabled")

    def disable(self, project_id: str, plugin_id: str) -> PluginManifest:
        return update_plugin_status(self.root, safe_project_id(project_id), plugin_id, "disabled")

    def delete(self, project_id: str, plugin_id: str) -> PluginDeleteResult:
        clean_project_id = safe_project_id(project_id)
        deleted = delete_plugin(self.root, clean_project_id, plugin_id)
        return PluginDeleteResult(clean_project_id, plugin_id, deleted)

    def register_hook(self, project_id: str, hook: PluginHook | Mapping[str, Any]) -> PluginHook:
        return register_plugin_hook(self.root, safe_project_id(project_id), hook)

    def hooks(self, project_id: str, *, plugin_id: str | None = None, event: str | None = None) -> tuple[PluginHook, ...]:
        return list_plugin_hooks(self.root, safe_project_id(project_id), plugin_id=plugin_id, event=event)

    def registry(self, project_id: str) -> dict[str, Any]:
        clean_project_id = safe_project_id(project_id)
        return build_plugin_api_registry(self.list(clean_project_id), self.hooks(clean_project_id))

    def summary(self, project_id: str) -> PluginSdkSummary:
        return summarize_plugin_sdk(self.root, safe_project_id(project_id))
