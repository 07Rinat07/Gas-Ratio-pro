from dataclasses import dataclass

from ui.interpretation_interval_navigator import (
    build_manual_interval_navigator,
    selected_interval_id_from_plotly_event,
)


@dataclass(frozen=True)
class _Interval:
    id: str
    label: str
    top: float
    base: float
    interval_type: str = "pay"
    color: str = "#123456"
    comment: str = "Проверить по ГИС"


def test_navigator_builds_clickable_markers_and_selected_style() -> None:
    intervals = (
        _Interval("id-1", "Пласт A", 1000.0, 1010.0),
        _Interval("id-2", "Пласт B", 1020.0, 1035.0, color="#654321"),
    )

    figure = build_manual_interval_navigator(intervals, selected_interval_id="id-2")

    assert len(figure.data) == 1
    trace = figure.data[0]
    assert list(trace.customdata[0])[:2] == ["id-1", "Пласт A"]
    assert list(trace.customdata[1])[:2] == ["id-2", "Пласт B"]
    assert list(trace.marker.symbol) == ["square", "diamond"]
    assert len(figure.layout.shapes) == 2
    assert list(figure.layout.yaxis.range)[0] > list(figure.layout.yaxis.range)[1]


def test_selection_event_extracts_only_allowed_interval_id() -> None:
    event = {"selection": {"points": [{"customdata": ["id-2", "Пласт B"]}]}}

    assert selected_interval_id_from_plotly_event(
        event,
        valid_interval_ids=("id-1", "id-2"),
    ) == "id-2"
    assert selected_interval_id_from_plotly_event(
        event,
        valid_interval_ids=("id-1",),
    ) == ""


def test_selection_event_is_tolerant_of_empty_payloads() -> None:
    assert selected_interval_id_from_plotly_event(None) == ""
    assert selected_interval_id_from_plotly_event({"selection": {"points": []}}) == ""
    assert selected_interval_id_from_plotly_event({"selection": {"points": [{}]}}) == ""
