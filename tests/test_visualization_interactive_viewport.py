from __future__ import annotations

import pytest

from services.visualization_interactive_viewport import (
    InteractiveViewport,
    ViewportLimits,
)


def _viewport(**changes):
    values = {
        "domain_start": 1000.0,
        "domain_stop": 1100.0,
        "screen_start": 64.0,
        "screen_stop": 684.0,
        "inverted": True,
        "unit": "M",
        "limits": ViewportLimits(minimum=900.0, maximum=1200.0, minimum_span=1.0),
    }
    values.update(changes)
    return InteractiveViewport(**values)


def test_domain_and_screen_transforms_are_reversible():
    viewport = _viewport()

    assert viewport.domain_to_screen(1000.0) == pytest.approx(64.0)
    assert viewport.domain_to_screen(1100.0) == pytest.approx(684.0)
    assert viewport.screen_to_domain(374.0) == pytest.approx(1050.0)

    for depth in (1000.0, 1012.5, 1050.0, 1099.9, 1100.0):
        assert viewport.screen_to_domain(viewport.domain_to_screen(depth)) == pytest.approx(depth)


def test_non_inverted_viewport_reverses_vertical_direction():
    viewport = _viewport(inverted=False)

    assert viewport.domain_to_screen(1000.0) == pytest.approx(684.0)
    assert viewport.domain_to_screen(1100.0) == pytest.approx(64.0)
    assert viewport.screen_to_domain(64.0) == pytest.approx(1100.0)


def test_clamped_transforms_do_not_escape_visible_range():
    viewport = _viewport()

    assert viewport.domain_to_screen(900.0, clamp=True) == pytest.approx(64.0)
    assert viewport.screen_to_domain(800.0, clamp=True) == pytest.approx(1100.0)


def test_pan_domain_respects_global_limits():
    viewport = _viewport(domain_start=900.0, domain_stop=1000.0)

    left = viewport.pan_domain(-50.0)
    right = viewport.pan_domain(500.0)

    assert (left.domain_start, left.domain_stop) == pytest.approx((900.0, 1000.0))
    assert (right.domain_start, right.domain_stop) == pytest.approx((1100.0, 1200.0))


def test_pan_pixels_converts_drag_to_domain_delta():
    viewport = _viewport()

    moved = viewport.pan_pixels(62.0)

    assert moved.domain_start == pytest.approx(990.0)
    assert moved.domain_stop == pytest.approx(1090.0)


def test_zoom_keeps_anchor_stationary_and_limits_span():
    viewport = _viewport()

    zoomed = viewport.zoom(2.0, anchor_domain=1025.0)
    minimum = viewport.zoom(1_000_000.0)

    assert zoomed.domain_start == pytest.approx(1012.5)
    assert zoomed.domain_stop == pytest.approx(1062.5)
    assert minimum.domain_span == pytest.approx(1.0)


def test_zoom_at_screen_preserves_cursor_domain_value():
    viewport = _viewport()
    cursor_y = 219.0
    anchor_before = viewport.screen_to_domain(cursor_y)

    zoomed = viewport.zoom_at_screen(2.0, cursor_y)

    assert zoomed.screen_to_domain(cursor_y) == pytest.approx(anchor_before)


def test_fit_and_serialization_round_trip():
    viewport = _viewport().fit(1020.0, 1040.0)
    restored = InteractiveViewport.from_dict(viewport.to_dict())

    assert restored == viewport
    assert restored.to_dict()["schema"] == "visualization.interactive.viewport"
    assert restored.to_dict()["renderer_neutral"] is True


def test_invalid_viewport_rejects_coordinate_operations():
    viewport = _viewport(domain_start=1000.0, domain_stop=1000.0)

    assert viewport.valid is False
    with pytest.raises(ValueError, match="invalid"):
        viewport.domain_to_screen(1000.0)


def test_invalid_zoom_factor_is_rejected():
    with pytest.raises(ValueError, match="positive finite"):
        _viewport().zoom(0.0)
