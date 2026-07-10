"""Persistent renderer-neutral style presets for LAS Viewer interaction overlays."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Iterable, Mapping

from services.las_viewer_interaction_overlay import LasViewerInteractionOverlayStyle


_SCHEMA = "las.viewer.interaction-overlay-presets"
_VERSION = "1.0"


def _clean_name(value: object) -> str:
    name = str(value or "").strip()
    if not name:
        raise ValueError("preset name cannot be empty")
    return name


@dataclass(frozen=True, slots=True)
class LasViewerOverlayPreset:
    name: str
    style: LasViewerInteractionOverlayStyle
    description: str = ""
    builtin: bool = False
    tags: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _clean_name(self.name))
        object.__setattr__(self, "description", str(self.description or "").strip())
        object.__setattr__(
            self,
            "tags",
            tuple(dict.fromkeys(str(item).strip() for item in self.tags if str(item).strip())),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "builtin": self.builtin,
            "tags": list(self.tags),
            "style": self.style.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "LasViewerOverlayPreset":
        style = data.get("style")
        if not isinstance(style, Mapping):
            raise ValueError("overlay preset requires style")
        return cls(
            name=_clean_name(data.get("name")),
            description=str(data.get("description") or ""),
            builtin=bool(data.get("builtin", False)),
            tags=tuple(data.get("tags") or ()),
            style=LasViewerInteractionOverlayStyle.from_dict(style),
        )


class LasViewerOverlayPresetRepository:
    """Own named overlay presets and preserve deterministic ordering."""

    def __init__(self, presets: Iterable[LasViewerOverlayPreset] = ()) -> None:
        self._presets: dict[str, LasViewerOverlayPreset] = {}
        for preset in presets:
            self.save(preset, overwrite=False)

    @classmethod
    def with_defaults(cls) -> "LasViewerOverlayPresetRepository":
        return cls(
            (
                LasViewerOverlayPreset(
                    "Default",
                    LasViewerInteractionOverlayStyle(),
                    "Balanced cursor and selection overlay",
                    True,
                    ("default",),
                ),
                LasViewerOverlayPreset(
                    "High Contrast",
                    LasViewerInteractionOverlayStyle(
                        cursor_color="#000000",
                        cursor_width=2.0,
                        selection_accent="#ff3b30",
                        selection_opacity=1.0,
                    ),
                    "High visibility for field and presentation use",
                    True,
                    ("accessibility", "contrast"),
                ),
                LasViewerOverlayPreset(
                    "Presentation",
                    LasViewerInteractionOverlayStyle(
                        cursor_color="#1f4e79",
                        cursor_width=1.5,
                        cursor_opacity=0.85,
                        selection_accent="#f4b183",
                        selection_opacity=0.75,
                    ),
                    "Reduced opacity for clean presentations",
                    True,
                    ("presentation",),
                ),
            )
        )

    def save(self, preset: LasViewerOverlayPreset, *, overwrite: bool = True) -> LasViewerOverlayPreset:
        key = preset.name.casefold()
        current = self._presets.get(key)
        if current is not None and not overwrite:
            raise ValueError(f"overlay preset already exists: {preset.name}")
        if current is not None and current.builtin and not preset.builtin:
            raise ValueError("builtin overlay preset cannot be overwritten")
        self._presets[key] = preset
        return preset

    def get(self, name: str) -> LasViewerOverlayPreset:
        key = _clean_name(name).casefold()
        try:
            return self._presets[key]
        except KeyError as exc:
            raise KeyError(f"unknown overlay preset: {name}") from exc

    def delete(self, name: str) -> bool:
        key = _clean_name(name).casefold()
        preset = self._presets.get(key)
        if preset is None:
            return False
        if preset.builtin:
            raise ValueError("builtin overlay preset cannot be deleted")
        del self._presets[key]
        return True

    def list(self) -> tuple[LasViewerOverlayPreset, ...]:
        return tuple(sorted(self._presets.values(), key=lambda item: (not item.builtin, item.name.casefold())))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": _SCHEMA,
            "version": _VERSION,
            "presets": [item.to_dict() for item in self.list()],
            "renderer_neutral": True,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "LasViewerOverlayPresetRepository":
        if str(data.get("schema") or "") != _SCHEMA:
            raise ValueError("unsupported overlay preset repository schema")
        raw = data.get("presets")
        if not isinstance(raw, list):
            raise ValueError("overlay preset repository requires presets list")
        return cls(LasViewerOverlayPreset.from_dict(item) for item in raw if isinstance(item, Mapping))


class LasViewerOverlayPresetFileStore:
    """Atomically persist overlay preset repositories as UTF-8 JSON."""

    def save(self, path: str | os.PathLike[str], repository: LasViewerOverlayPresetRepository) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(repository.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        temp_name: str | None = None
        try:
            with NamedTemporaryFile("w", encoding="utf-8", dir=target.parent, delete=False) as handle:
                temp_name = handle.name
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, target)
        finally:
            if temp_name and os.path.exists(temp_name):
                os.unlink(temp_name)
        return target

    def load(self, path: str | os.PathLike[str]) -> LasViewerOverlayPresetRepository:
        target = Path(path)
        data = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(data, Mapping):
            raise ValueError("overlay preset file must contain an object")
        return LasViewerOverlayPresetRepository.from_dict(data)
