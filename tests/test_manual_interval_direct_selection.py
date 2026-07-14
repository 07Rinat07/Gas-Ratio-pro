from types import SimpleNamespace

import pandas as pd

from palettes.depth_tracks import build_depth_gas_tracks
from ui.interpretation_interval_navigator import selected_interval_id_from_plotly_event


def _manual_overlay(interval_id: str = "manual-1") -> SimpleNamespace:
    return SimpleNamespace(
        interval_id=interval_id,
        top_depth=1000.0,
        bottom_depth=1012.0,
        fluid_type="manual",
        display_label="Пласт A",
        color="#336699",
        opacity=0.20,
        note="Проверить насыщение",
    )


def test_depth_track_exposes_clickable_manual_interval_uuid() -> None:
    frame = pd.DataFrame({"depth": [999.0, 1005.0, 1013.0], "c1": [1.0, 2.0, 3.0]})

    figure = build_depth_gas_tracks(
        frame,
        reservoir_intervals=(_manual_overlay(),),
        selected_interval_id="manual-1",
    )

    selector_traces = [
        trace for trace in figure.data
        if getattr(trace, "customdata", None) is not None
        and len(trace.customdata)
        and list(trace.customdata[0])[0] == "manual-1"
    ]
    assert len(selector_traces) == 1
    selector = selector_traces[0]
    assert selector.xaxis == "x2"
    assert list(selector.customdata[0])[:2] == ["manual-1", "Пласт A"]
    assert selector.marker.symbol == "diamond"
    assert figure.layout.xaxis2.overlaying == "x"


def test_main_chart_selection_payload_reuses_uuid_extractor() -> None:
    event = {"selection": {"points": [{"customdata": ["manual-1", "Пласт A"]}]}}

    assert selected_interval_id_from_plotly_event(
        event,
        valid_interval_ids=("manual-1", "manual-2"),
    ) == "manual-1"
