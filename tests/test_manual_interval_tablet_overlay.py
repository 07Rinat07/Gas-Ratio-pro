from dataclasses import dataclass

import pandas as pd

from palettes.depth_tracks import build_depth_gas_tracks
from palettes.well_log_tablet import (
    TabletTrackConfig,
    build_well_log_tablet,
    manual_interval_overlays,
)


@dataclass(frozen=True)
class _ManualInterval:
    id: str = "8a97d9c8-bf8b-4d48-a247-bf3543946572"
    label: str = "Газонасыщенный пласт"
    top: float = 1000.0
    base: float = 1012.5
    interval_type: str = "pay"
    color: str = "#123456"
    comment: str = "Проверить по ГИС"


def test_manual_intervals_are_converted_to_colored_overlays() -> None:
    overlays = manual_interval_overlays((_ManualInterval(),))

    assert len(overlays) == 1
    overlay = overlays[0]
    assert overlay.interval_id == _ManualInterval.id
    assert overlay.display_label == "Газонасыщенный пласт"
    assert overlay.color == "#123456"
    assert overlay.source_kind == "manual"
    assert overlay.thickness == 12.5
    assert "Проверить" in overlay.recommendation


def test_manual_overlay_is_rendered_on_tablet_and_depth_track() -> None:
    frame = pd.DataFrame(
        {
            "depth": [999.0, 1005.0, 1013.0],
            "c1": [1.0, 2.0, 3.0],
        }
    )
    overlay = manual_interval_overlays((_ManualInterval(),))[0]

    tablet = build_well_log_tablet(
        frame,
        (TabletTrackConfig(column="c1"),),
        reservoir_intervals=(overlay,),
        selected_depth=1006.0,
    )
    depth_track = build_depth_gas_tracks(
        frame,
        reservoir_intervals=(overlay,),
        selected_interval_id=overlay.interval_id,
    )

    tablet_shapes = list(tablet.layout.shapes or ())
    depth_shapes = list(depth_track.layout.shapes or ())
    assert any(getattr(shape, "fillcolor", None) == "#123456" for shape in tablet_shapes)
    assert any(getattr(shape, "fillcolor", None) == "#123456" for shape in depth_shapes)
