from __future__ import annotations

import json

import pytest

from services.las_viewer_interaction_overlay import LasViewerInteractionOverlayStyle
from services.las_viewer_overlay_presets import (
    LasViewerOverlayPreset,
    LasViewerOverlayPresetFileStore,
    LasViewerOverlayPresetRepository,
)


def test_default_repository_contains_stable_builtin_presets() -> None:
    repository = LasViewerOverlayPresetRepository.with_defaults()
    names = [item.name for item in repository.list()]
    assert names == ["Default", "High Contrast", "Presentation"]
    assert all(item.builtin for item in repository.list())


def test_custom_preset_round_trip() -> None:
    preset = LasViewerOverlayPreset(
        "Night",
        LasViewerInteractionOverlayStyle(cursor_color="#ffffff", selection_accent="#00ffff"),
        tags=("dark", "dark"),
    )
    restored = LasViewerOverlayPreset.from_dict(preset.to_dict())
    assert restored == preset
    assert restored.tags == ("dark",)


def test_repository_save_get_and_case_insensitive_lookup() -> None:
    repository = LasViewerOverlayPresetRepository()
    preset = LasViewerOverlayPreset("Custom", LasViewerInteractionOverlayStyle())
    repository.save(preset)
    assert repository.get("custom") == preset


def test_repository_rejects_duplicate_without_overwrite() -> None:
    repository = LasViewerOverlayPresetRepository()
    repository.save(LasViewerOverlayPreset("Custom", LasViewerInteractionOverlayStyle()))
    with pytest.raises(ValueError):
        repository.save(
            LasViewerOverlayPreset("CUSTOM", LasViewerInteractionOverlayStyle(cursor_width=2.0)),
            overwrite=False,
        )


def test_builtin_preset_cannot_be_deleted_or_replaced_by_custom() -> None:
    repository = LasViewerOverlayPresetRepository.with_defaults()
    with pytest.raises(ValueError):
        repository.delete("Default")
    with pytest.raises(ValueError):
        repository.save(LasViewerOverlayPreset("Default", LasViewerInteractionOverlayStyle(cursor_width=3.0)))


def test_custom_preset_can_be_deleted() -> None:
    repository = LasViewerOverlayPresetRepository()
    repository.save(LasViewerOverlayPreset("Custom", LasViewerInteractionOverlayStyle()))
    assert repository.delete("Custom") is True
    assert repository.delete("Custom") is False


def test_repository_serialization_is_renderer_neutral() -> None:
    repository = LasViewerOverlayPresetRepository.with_defaults()
    payload = repository.to_dict()
    assert payload["schema"] == "las.viewer.interaction-overlay-presets"
    assert payload["renderer_neutral"] is True
    assert LasViewerOverlayPresetRepository.from_dict(payload).to_dict() == payload


def test_file_store_saves_and_loads_utf8_atomically(tmp_path) -> None:
    repository = LasViewerOverlayPresetRepository.with_defaults()
    repository.save(
        LasViewerOverlayPreset(
            "Полевой режим",
            LasViewerInteractionOverlayStyle(cursor_width=2.5),
            "Для работы на скважине",
        )
    )
    path = tmp_path / "overlay-presets.json"
    store = LasViewerOverlayPresetFileStore()
    store.save(path, repository)
    restored = store.load(path)
    assert restored.get("Полевой режим").style.cursor_width == 2.5
    assert "Полевой режим" in path.read_text(encoding="utf-8")


def test_file_store_rejects_invalid_document(tmp_path) -> None:
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps([]), encoding="utf-8")
    with pytest.raises(ValueError):
        LasViewerOverlayPresetFileStore().load(path)
