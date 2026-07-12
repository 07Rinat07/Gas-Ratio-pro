from __future__ import annotations

import pandas as pd

from palettes.well_log_tablet import (
    ReservoirIntervalOverlay,
    TabletTrackConfig,
    build_well_log_tablet,
    reservoir_interval_overlays,
)


class _Interval:
    top = 1001.0
    base = 1003.0
    fluid_type = "oil"
    confidence_score = 88
    decision_level = "high"
    engineering_note = "Вероятный нефтенасыщенный интервал"

    @property
    def thickness(self) -> float:
        return 2.0


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "depth": [1000.0, 1001.0, 1002.0, 1003.0, 1004.0],
            "c1": [1.0, 2.0, 3.0, 2.5, 1.5],
            "wh": [10.0, 20.0, 30.0, 25.0, 15.0],
        }
    )


def test_reservoir_interval_overlays_preserve_engineering_fields() -> None:
    overlays = reservoir_interval_overlays((_Interval(),))

    assert len(overlays) == 1
    overlay = overlays[0]
    assert overlay.interval_id == "HC-001"
    assert overlay.top_depth == 1001.0
    assert overlay.bottom_depth == 1003.0
    assert overlay.fluid_type == "oil"
    assert overlay.confidence_score == 88
    assert overlay.thickness == 2.0


def test_depth_panel_adds_interval_track_boundaries_and_selected_depth() -> None:
    overlay = ReservoirIntervalOverlay(
        interval_id="HC-001",
        top_depth=1001.0,
        bottom_depth=1003.0,
        fluid_type="oil",
        confidence_score=88,
        thickness=2.0,
    )

    figure = build_well_log_tablet(
        _frame(),
        (TabletTrackConfig("c1"), TabletTrackConfig("wh")),
        reservoir_intervals=(overlay,),
        selected_depth=1002.0,
    )

    assert figure.layout.title.text.startswith("Depth Panel 2.0")
    assert len(figure.data) == 5  # three engineering tracks + two curves
    annotation_texts = [str(item.text) for item in figure.layout.annotations]
    assert any("HC-001" in text and "Нефть" in text for text in annotation_texts)
    assert any("Выбрано: 1002" in text for text in annotation_texts)

    shapes = list(figure.layout.shapes)
    assert any(shape.type == "rect" for shape in shapes)
    boundary_depths = {
        float(shape.y0)
        for shape in shapes
        if shape.type == "line" and float(shape.y0) == float(shape.y1)
    }
    assert {1001.0, 1002.0, 1003.0}.issubset(boundary_depths)


def test_depth_panel_remains_backward_compatible_without_intervals() -> None:
    figure = build_well_log_tablet(
        _frame(),
        (TabletTrackConfig("c1"),),
    )

    assert len(figure.data) == 1
    assert not any("HC-" in str(item.text) for item in figure.layout.annotations)


def test_depth_panel_adds_confidence_and_recommendation_tracks() -> None:
    overlay = ReservoirIntervalOverlay(
        interval_id="HC-017",
        top_depth=1001.0,
        bottom_depth=1003.0,
        fluid_type="gas",
        confidence_score=82,
        thickness=2.0,
        decision_level="high",
        recommendation="Сопоставить с ГИС, литологией и испытаниями.",
    )

    figure = build_well_log_tablet(
        _frame(),
        (TabletTrackConfig("c1"),),
        reservoir_intervals=(overlay,),
    )

    subplot_titles = [str(annotation.text) for annotation in figure.layout.annotations[:4]]
    assert subplot_titles[:3] == ["Тип пласта", "Достоверность", "Рекомендации"]
    texts = [str(annotation.text) for annotation in figure.layout.annotations]
    assert any("82%" in text and "high" in text for text in texts)
    assert any("Сопоставить с ГИС" in text for text in texts)
    assert any(shape.type == "rect" and shape.xref == "x2" for shape in figure.layout.shapes)
    assert any(shape.type == "rect" and shape.xref == "x3" for shape in figure.layout.shapes)
