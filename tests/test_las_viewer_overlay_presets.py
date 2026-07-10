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

from services.las_viewer_overlay_presets import LasViewerOverlayPresetExchange


def test_exchange_exports_custom_presets_only_by_default() -> None:
    repository = LasViewerOverlayPresetRepository.with_defaults()
    repository.save(LasViewerOverlayPreset("Night", LasViewerInteractionOverlayStyle(cursor_color="#fff")))
    package = LasViewerOverlayPresetExchange().export_dict(repository)
    assert [item["name"] for item in package["presets"]] == ["Night"]
    assert package["renderer_neutral"] is True


def test_exchange_can_export_selected_presets() -> None:
    repository = LasViewerOverlayPresetRepository()
    repository.save(LasViewerOverlayPreset("A", LasViewerInteractionOverlayStyle()))
    repository.save(LasViewerOverlayPreset("B", LasViewerInteractionOverlayStyle()))
    package = LasViewerOverlayPresetExchange().export_dict(repository, names=("b",))
    assert [item["name"] for item in package["presets"]] == ["B"]


def test_exchange_imports_new_preset_and_reports_result() -> None:
    source = LasViewerOverlayPresetRepository()
    source.save(LasViewerOverlayPreset("Field", LasViewerInteractionOverlayStyle(cursor_width=2.0)))
    package = LasViewerOverlayPresetExchange().export_dict(source)
    target = LasViewerOverlayPresetRepository.with_defaults()
    result = LasViewerOverlayPresetExchange().import_dict(target, package)
    assert result.imported == ("Field",)
    assert result.changed is True
    assert target.get("Field").style.cursor_width == 2.0


def test_exchange_collision_skip_replace_and_error() -> None:
    exchange = LasViewerOverlayPresetExchange()
    source = LasViewerOverlayPresetRepository()
    source.save(LasViewerOverlayPreset("Custom", LasViewerInteractionOverlayStyle(cursor_width=3.0)))
    package = exchange.export_dict(source)

    target = LasViewerOverlayPresetRepository()
    target.save(LasViewerOverlayPreset("Custom", LasViewerInteractionOverlayStyle(cursor_width=1.0)))
    assert exchange.import_dict(target, package, collision="skip").skipped == ("Custom",)
    assert target.get("Custom").style.cursor_width == 1.0
    assert exchange.import_dict(target, package, collision="replace").replaced == ("Custom",)
    assert target.get("Custom").style.cursor_width == 3.0
    with pytest.raises(ValueError):
        exchange.import_dict(target, package, collision="error")


def test_exchange_never_replaces_builtin_preset() -> None:
    exchange = LasViewerOverlayPresetExchange()
    package = {
        "schema": "las.viewer.interaction-overlay-preset-exchange",
        "version": "1.0",
        "presets": [LasViewerOverlayPreset("Default", LasViewerInteractionOverlayStyle(cursor_width=4.0)).to_dict()],
    }
    target = LasViewerOverlayPresetRepository.with_defaults()
    assert exchange.import_dict(target, package, collision="replace").skipped == ("Default",)
    assert target.get("Default").style.cursor_width != 4.0


def test_exchange_rejects_duplicate_names_in_package() -> None:
    preset = LasViewerOverlayPreset("Duplicate", LasViewerInteractionOverlayStyle()).to_dict()
    package = {
        "schema": "las.viewer.interaction-overlay-preset-exchange",
        "version": "1.0",
        "presets": [preset, preset],
    }
    with pytest.raises(ValueError):
        LasViewerOverlayPresetExchange().import_dict(LasViewerOverlayPresetRepository(), package)


def test_exchange_file_round_trip_preserves_unicode(tmp_path) -> None:
    repository = LasViewerOverlayPresetRepository()
    repository.save(LasViewerOverlayPreset("Полевой", LasViewerInteractionOverlayStyle(cursor_width=2.2)))
    path = tmp_path / "shared-overlay-presets.json"
    exchange = LasViewerOverlayPresetExchange()
    exchange.export_file(path, repository)
    restored = LasViewerOverlayPresetRepository()
    result = exchange.import_file(path, restored)
    assert result.imported == ("Полевой",)
    assert restored.get("Полевой").style.cursor_width == 2.2
    assert "Полевой" in path.read_text(encoding="utf-8")


def test_exchange_inspection_reports_compatible_package() -> None:
    repository = LasViewerOverlayPresetRepository()
    repository.save(LasViewerOverlayPreset("Field", LasViewerInteractionOverlayStyle(cursor_width=2.0)))
    exchange = LasViewerOverlayPresetExchange()
    report = exchange.inspect_package(exchange.export_dict(repository))
    assert report.compatible is True
    assert report.version == "1.0"
    assert report.preset_count == 1
    assert report.preset_names == ("Field",)
    assert report.warnings == ()


def test_exchange_rejects_unsupported_version_before_import() -> None:
    package = {
        "schema": "las.viewer.interaction-overlay-preset-exchange",
        "version": "2.0",
        "presets": [],
        "renderer_neutral": True,
    }
    with pytest.raises(ValueError, match="unsupported overlay preset exchange version"):
        LasViewerOverlayPresetExchange().import_dict(LasViewerOverlayPresetRepository(), package)


def test_exchange_accepts_legacy_package_without_renderer_flag_with_warning() -> None:
    package = {
        "schema": "las.viewer.interaction-overlay-preset-exchange",
        "version": "1.0",
        "presets": [],
    }
    report = LasViewerOverlayPresetExchange().inspect_package(package)
    assert report.compatible is True
    assert report.warnings == ("renderer_neutral flag is missing; legacy package accepted",)


def test_exchange_rejects_non_renderer_neutral_package() -> None:
    package = {
        "schema": "las.viewer.interaction-overlay-preset-exchange",
        "version": "1.0",
        "presets": [],
        "renderer_neutral": False,
    }
    with pytest.raises(ValueError, match="must be renderer neutral"):
        LasViewerOverlayPresetExchange().inspect_package(package)


def test_error_collision_policy_is_transactional() -> None:
    exchange = LasViewerOverlayPresetExchange()
    package = {
        "schema": "las.viewer.interaction-overlay-preset-exchange",
        "version": "1.0",
        "renderer_neutral": True,
        "presets": [
            LasViewerOverlayPreset("New", LasViewerInteractionOverlayStyle(cursor_width=2.0)).to_dict(),
            LasViewerOverlayPreset("Existing", LasViewerInteractionOverlayStyle(cursor_width=3.0)).to_dict(),
        ],
    }
    target = LasViewerOverlayPresetRepository()
    target.save(LasViewerOverlayPreset("Existing", LasViewerInteractionOverlayStyle(cursor_width=1.0)))
    with pytest.raises(ValueError, match="already exists"):
        exchange.import_dict(target, package, collision="error")
    with pytest.raises(KeyError):
        target.get("New")
    assert target.get("Existing").style.cursor_width == 1.0


def test_exchange_migrates_legacy_version_09_package() -> None:
    package = {
        "schema": "las.viewer.interaction-overlay-preset-exchange",
        "version": "0.9",
        "renderer_neutral": True,
        "presets": [
            {
                "title": "Legacy Field",
                "labels": ["legacy", "field"],
                "overlay_style": {
                    "show_cursor": False,
                    "show_selection": True,
                    "cursor_line_color": "#112233",
                    "cursor_line_width": 2.5,
                    "selection_color": "#445566",
                },
            }
        ],
    }
    exchange = LasViewerOverlayPresetExchange()
    report = exchange.inspect_package(package)
    assert report.compatible is True
    assert report.version == "1.0"
    assert report.source_version == "0.9"
    assert report.migrated is True
    assert report.warnings == ("package migrated from version 0.9 to 1.0",)

    repository = LasViewerOverlayPresetRepository()
    result = exchange.import_dict(repository, package)
    assert result.imported == ("Legacy Field",)
    preset = repository.get("Legacy Field")
    assert preset.tags == ("legacy", "field")
    assert preset.style.cursor_visible is False
    assert preset.style.cursor_color == "#112233"
    assert preset.style.cursor_width == 2.5
    assert preset.style.selection_accent == "#445566"


def test_exchange_migration_does_not_mutate_source_package() -> None:
    package = {
        "schema": "las.viewer.interaction-overlay-preset-exchange",
        "version": "0.9",
        "presets": [{"title": "Legacy", "overlay_style": {"cursor_line_width": 2.0}}],
    }
    original = json.loads(json.dumps(package))
    LasViewerOverlayPresetExchange().inspect_package(package)
    assert package == original


def test_repository_rejects_unknown_version() -> None:
    payload = LasViewerOverlayPresetRepository().to_dict()
    payload["version"] = "99.0"
    with pytest.raises(ValueError, match="unsupported overlay preset repository version"):
        LasViewerOverlayPresetRepository.from_dict(payload)
