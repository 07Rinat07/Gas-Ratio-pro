"""Runtime synchronization of LAS Viewer overlay presets.

The module binds a preset repository to a LAS Viewer session without placing
state or style calculations in UI adapters. Repository changes can be applied
at runtime and immediately affect generated interaction overlays.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping

from services.las_viewer_interaction_overlay import (
    LasViewerInteractionOverlay,
    LasViewerInteractionOverlayEngine,
    LasViewerInteractionOverlayStyle,
)
from services.las_viewer_overlay_presets import (
    LasViewerOverlayPresetRepository,
)
from services.las_viewer_session import LasViewerSession
from services.visualization_render_model import VisualizationRenderModel


_SCHEMA = "las.viewer.overlay-preset-runtime"
_VERSION = "1.0"


def _fingerprint(repository: LasViewerOverlayPresetRepository) -> str:
    payload = json.dumps(
        repository.to_dict(),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _fallback_name(repository: LasViewerOverlayPresetRepository) -> str:
    presets = repository.list()
    if not presets:
        raise ValueError("overlay preset repository cannot be empty")
    for preset in presets:
        if preset.name.casefold() == "default":
            return preset.name
    for preset in presets:
        if preset.builtin:
            return preset.name
    return presets[0].name


@dataclass(frozen=True, slots=True)
class LasViewerOverlayRuntimeState:
    project_id: str
    las_id: str
    active_preset: str
    style: LasViewerInteractionOverlayStyle
    repository_fingerprint: str
    revision: int = 0
    fallback_applied: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": _SCHEMA,
            "version": _VERSION,
            "project_id": self.project_id,
            "las_id": self.las_id,
            "active_preset": self.active_preset,
            "style": self.style.to_dict(),
            "repository_fingerprint": self.repository_fingerprint,
            "revision": self.revision,
            "fallback_applied": self.fallback_applied,
            "renderer_neutral": True,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "LasViewerOverlayRuntimeState":
        if str(data.get("schema") or "") != _SCHEMA:
            raise ValueError("unsupported LAS viewer overlay runtime schema")
        if str(data.get("version") or "") != _VERSION:
            raise ValueError("unsupported LAS viewer overlay runtime version")
        style = data.get("style")
        if not isinstance(style, Mapping):
            raise ValueError("LAS viewer overlay runtime requires style")
        return cls(
            project_id=str(data.get("project_id") or "").strip(),
            las_id=str(data.get("las_id") or "").strip(),
            active_preset=str(data.get("active_preset") or "").strip(),
            style=LasViewerInteractionOverlayStyle.from_dict(style),
            repository_fingerprint=str(data.get("repository_fingerprint") or "").strip(),
            revision=max(0, int(data.get("revision") or 0)),
            fallback_applied=bool(data.get("fallback_applied", False)),
        )


class LasViewerOverlayPresetRuntime:
    """Apply and synchronize overlay presets for a live LAS Viewer session."""

    def __init__(
        self,
        session: LasViewerSession,
        repository: LasViewerOverlayPresetRepository,
        *,
        active_preset: str = "Default",
        overlay_engine: LasViewerInteractionOverlayEngine | None = None,
    ) -> None:
        self._session = session
        self._repository = repository
        self._overlay_engine = overlay_engine or LasViewerInteractionOverlayEngine()
        self._revision = 0
        self._fallback_applied = False
        self._active_preset = ""
        self._style = LasViewerInteractionOverlayStyle()
        self._repository_fingerprint = _fingerprint(repository)
        self._set_active(active_preset, allow_fallback=True, increment=False)

    @property
    def state(self) -> LasViewerOverlayRuntimeState:
        viewer = self._session.state
        return LasViewerOverlayRuntimeState(
            project_id=viewer.project_id,
            las_id=viewer.las_id,
            active_preset=self._active_preset,
            style=self._style,
            repository_fingerprint=self._repository_fingerprint,
            revision=self._revision,
            fallback_applied=self._fallback_applied,
        )

    @property
    def style(self) -> LasViewerInteractionOverlayStyle:
        return self._style

    @property
    def active_preset(self) -> str:
        return self._active_preset

    def apply(self, name: str) -> LasViewerOverlayRuntimeState:
        self._set_active(name, allow_fallback=False, increment=True)
        return self.state

    def synchronize(
        self,
        repository: LasViewerOverlayPresetRepository,
    ) -> LasViewerOverlayRuntimeState:
        """Hot-reload repository content while preserving the active preset."""
        fingerprint = _fingerprint(repository)
        if fingerprint == self._repository_fingerprint:
            return self.state

        previous_name = self._active_preset
        previous_style = self._style
        self._repository = repository
        self._repository_fingerprint = fingerprint
        self._set_active(previous_name, allow_fallback=True, increment=False)
        if self._active_preset != previous_name or self._style != previous_style:
            self._revision += 1
        return self.state

    def resolve_overlay(
        self,
        model: VisualizationRenderModel | Mapping[str, Any],
        *,
        track_ids: tuple[str, ...] | None = None,
        synchronize_source_layers: bool = True,
    ) -> LasViewerInteractionOverlay:
        return self._overlay_engine.resolve(
            model,
            self._session.state.interaction,
            track_ids=track_ids,
            synchronize_source_layers=synchronize_source_layers,
            style=self._style,
        )

    def snapshot(self) -> dict[str, Any]:
        return self.state.to_dict()

    def restore(self, state: LasViewerOverlayRuntimeState | Mapping[str, Any]) -> LasViewerOverlayRuntimeState:
        resolved = state if isinstance(state, LasViewerOverlayRuntimeState) else LasViewerOverlayRuntimeState.from_dict(state)
        viewer = self._session.state
        if resolved.las_id and resolved.las_id != viewer.las_id:
            raise ValueError("overlay runtime state belongs to another LAS session")
        self._set_active(resolved.active_preset, allow_fallback=True, increment=False)
        self._revision = resolved.revision
        return self.state

    def _set_active(self, name: str, *, allow_fallback: bool, increment: bool) -> None:
        requested = str(name or "").strip()
        fallback = False
        try:
            preset = self._repository.get(requested)
        except (KeyError, ValueError):
            if not allow_fallback:
                raise
            preset = self._repository.get(_fallback_name(self._repository))
            fallback = True

        changed = preset.name != self._active_preset or preset.style != self._style
        self._active_preset = preset.name
        self._style = preset.style
        self._fallback_applied = fallback
        if increment and changed:
            self._revision += 1
