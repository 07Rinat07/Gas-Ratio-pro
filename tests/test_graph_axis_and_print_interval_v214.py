from __future__ import annotations

import pandas as pd

from palettes.depth_tracks import build_depth_gas_tracks
from palettes.well_log_tablet import TabletTrackConfig, build_well_log_tablet
from projects.graph_settings import InterpretationGraphSettings, settings_from_dict, settings_to_dict


def test_depth_graph_uses_factual_las_bounds_without_zero_padding() -> None:
    frame = pd.DataFrame({"depth": [47.0, 50.0, 2016.2], "c1": [1.0, 2.0, 3.0]})
    figure = build_depth_gas_tracks(frame)
    assert tuple(figure.layout.yaxis.range) == (2016.2, 47.0)
    assert figure.layout.yaxis.autorange is False


def test_tablet_uses_factual_las_bounds_without_zero_padding() -> None:
    frame = pd.DataFrame({"depth": [47.0, 50.0, 2016.2], "c1": [1.0, 2.0, 3.0]})
    figure = build_well_log_tablet(frame, [TabletTrackConfig(column="c1")])
    assert tuple(figure.layout.yaxis.range) == (2016.2, 47.0)
    assert figure.layout.yaxis.autorange is False


def test_pixler_manual_y_range_round_trip() -> None:
    settings = InterpretationGraphSettings(pixler_palette_y_range=(0.01, 1000.0))
    restored = settings_from_dict(settings_to_dict(settings))
    assert restored.pixler_palette_y_range == (0.01, 1000.0)
