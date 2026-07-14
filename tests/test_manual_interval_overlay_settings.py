from dataclasses import dataclass

from palettes.well_log_tablet import (
    configure_manual_interval_overlays,
    manual_interval_overlays,
)


@dataclass(frozen=True)
class _Interval:
    id: str = "interval-1"
    label: str = "Пласт A"
    top: float = 1000.0
    base: float = 1010.0
    interval_type: str = "pay"
    color: str = "#123456"
    comment: str = "Проверить"


def test_manual_overlay_visibility_can_be_disabled_without_mutating_source() -> None:
    source = manual_interval_overlays((_Interval(),))

    configured = configure_manual_interval_overlays(source, visible=False, opacity=0.30)

    assert configured == ()
    assert source[0].opacity == 0.18


def test_manual_overlay_opacity_is_applied_and_clamped() -> None:
    source = manual_interval_overlays((_Interval(),))

    configured = configure_manual_interval_overlays(source, opacity=0.42)
    maximum = configure_manual_interval_overlays(source, opacity=5.0)
    minimum = configure_manual_interval_overlays(source, opacity=-1.0)

    assert configured[0].opacity == 0.42
    assert maximum[0].opacity == 0.55
    assert minimum[0].opacity == 0.04
    assert source[0].opacity == 0.18
