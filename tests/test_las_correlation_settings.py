from __future__ import annotations

from las_correlation import (
    LasCorrelationSettings,
    VIEW_MODE_BY_CURVE,
    VIEW_MODE_BY_WELL,
    settings_from_dict,
    settings_summary,
    settings_to_dict,
)


def test_las_correlation_settings_roundtrip_preserves_values():
    settings = LasCorrelationSettings(
        selected_well_names=("Well A", "Well B"),
        curve_group_overrides={"Well A": {"TGAS": "gamma"}},
        gis_groups=("gamma", "resistivity"),
        gas_groups=("total_gas",),
        depth_range=(1000.0, 1200.0),
        gis_x_range=(0.0, 150.0),
        gas_x_range=(0.0, 50.0),
        height_per_well=520,
        view_mode=VIEW_MODE_BY_CURVE,
        comparison_curve="GR",
    )

    restored = settings_from_dict(settings_to_dict(settings))

    assert restored == settings


def test_las_correlation_settings_from_dict_normalizes_ranges_and_height():
    settings = settings_from_dict(
        {
            "selected_well_names": ["Well A"],
            "depth_range": [1200, 1000],
            "gis_x_range": [10, 10],
            "gas_x_range": ["bad", 1],
            "height_per_well": 2000,
            "view_mode": "bad value",
            "comparison_curve": "TGAS",
        }
    )

    assert settings.selected_well_names == ("Well A",)
    assert settings.depth_range == (1000.0, 1200.0)
    assert settings.gis_x_range is None
    assert settings.gas_x_range is None
    assert settings.height_per_well == 750
    assert settings.view_mode == VIEW_MODE_BY_WELL
    assert settings.comparison_curve == "TGAS"


def test_las_correlation_settings_summary_mentions_saved_scope():
    settings = LasCorrelationSettings(
        selected_well_names=("Well A",),
        curve_group_overrides={"Well A": {"TGAS": "gamma", "GR": "other"}},
        gis_x_range=(0.0, 100.0),
        view_mode=VIEW_MODE_BY_CURVE,
        comparison_curve="GR",
    )

    summary = settings_summary(settings)

    assert any("Well A" in line for line in summary)
    assert any("Ручные группы кривых: 2" in line for line in summary)
    assert any("X-scale ГИС: (0.0, 100.0)" in line for line in summary)
    assert any("Представление: По кривой" in line for line in summary)
    assert any("Кривая сравнения: GR" in line for line in summary)
