from __future__ import annotations

import json

import pytest

from projects.interpretation_interval_display_settings import (
    InterpretationIntervalDisplaySettings,
    interval_display_settings_path,
    load_interpretation_interval_display_settings,
    normalize_interval_display_settings,
    save_interpretation_interval_display_settings,
)


def test_interval_display_settings_roundtrip_is_scoped_to_project_and_well(tmp_path):
    settings = InterpretationIntervalDisplaySettings(visible=False, opacity=0.37)

    path = save_interpretation_interval_display_settings(
        settings,
        root=tmp_path,
        project_id="project-a",
        well_id="well-1",
    )

    assert path == interval_display_settings_path(tmp_path, "project-a", "well-1")
    assert load_interpretation_interval_display_settings(
        tmp_path,
        "project-a",
        "well-1",
    ) == settings
    assert load_interpretation_interval_display_settings(
        tmp_path,
        "project-a",
        "well-2",
    ) == InterpretationIntervalDisplaySettings()

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["settings"] == {"visible": False, "opacity": 0.37}


def test_interval_display_settings_normalize_opacity_bounds():
    assert normalize_interval_display_settings(opacity=-10).opacity == 0.04
    assert normalize_interval_display_settings(opacity=10).opacity == 0.55
    assert normalize_interval_display_settings(opacity="bad").opacity == 0.18


def test_interval_display_settings_reject_unknown_schema(tmp_path):
    path = interval_display_settings_path(tmp_path, "project-a", "well-1")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"schema":"unknown","settings":{}}', encoding="utf-8")

    with pytest.raises(ValueError, match="Неподдерживаемая схема"):
        load_interpretation_interval_display_settings(tmp_path, "project-a", "well-1")
