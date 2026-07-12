from projects.graph_settings import InterpretationGraphSettings, settings_from_dict, settings_to_dict
from app.streamlit_app import _adaptive_tablet_height


def test_view_mode_settings_round_trip():
    original = InterpretationGraphSettings(
        tablet_view_mode="detail",
        tablet_min_interval_thickness=2.5,
        selected_interval_id="HC-022",
        tablet_adaptive_height=True,
    )
    restored = settings_from_dict(settings_to_dict(original))
    assert restored.tablet_view_mode == "detail"
    assert restored.tablet_min_interval_thickness == 2.5
    assert restored.selected_interval_id == "HC-022"
    assert restored.tablet_adaptive_height is True


def test_detail_mode_uses_more_vertical_space_for_small_interval():
    detail = _adaptive_tablet_height((1485.6, 1496.6), "detail", 650)
    overview = _adaptive_tablet_height((47.0, 2016.2), "overview", 650)
    assert detail >= 680
    assert detail > overview
    assert detail <= 1500
