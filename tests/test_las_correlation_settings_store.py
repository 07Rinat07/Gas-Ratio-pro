from __future__ import annotations

import pytest

from las_correlation import (
    DEFAULT_PROJECT_ID,
    LasCorrelationSettings,
    load_project_correlation_settings,
    project_correlation_settings_exists,
    save_project_correlation_settings,
)


def test_project_correlation_settings_roundtrip(tmp_path):
    settings = LasCorrelationSettings(
        selected_well_names=("Well A",),
        curve_group_overrides={"Well A": {"TGAS": "gamma"}},
        depth_range=(1000.0, 1010.0),
        gis_x_range=(0.0, 150.0),
        height_per_well=520,
    )

    path = save_project_correlation_settings(settings, root=tmp_path, project_id=DEFAULT_PROJECT_ID)
    restored = load_project_correlation_settings(tmp_path, DEFAULT_PROJECT_ID)

    assert path.name == "correlation_settings.json"
    assert project_correlation_settings_exists(tmp_path, DEFAULT_PROJECT_ID)
    assert restored == settings


def test_load_project_correlation_settings_returns_none_when_missing(tmp_path):
    assert load_project_correlation_settings(tmp_path, DEFAULT_PROJECT_ID) is None


def test_project_correlation_settings_rejects_unsafe_project_id(tmp_path):
    settings = LasCorrelationSettings()

    with pytest.raises(ValueError, match="Некорректный идентификатор проекта"):
        save_project_correlation_settings(settings, root=tmp_path, project_id="../bad")
