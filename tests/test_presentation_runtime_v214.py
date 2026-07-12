from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pandas as pd

from core.presentation_runtime import (
    ParsedLasCache,
    ReportDocumentModel,
    RevisionController,
    RevisionSnapshot,
    WellLogRenderModel,
    content_signature,
    dataframe_signature,
    persist_revisions,
    revision_controller_from_state,
)


def test_revision_boundaries_invalidate_only_downstream_layers() -> None:
    controller = RevisionController()
    assert controller.bump_export() == RevisionSnapshot(export=1)
    assert controller.bump_presentation() == RevisionSnapshot(presentation=1, export=2)
    assert controller.bump_calculation() == RevisionSnapshot(calculation=1, presentation=2, export=3)
    assert controller.bump_data() == RevisionSnapshot(data=1, calculation=2, presentation=3, export=4)


def test_revision_snapshot_round_trips_through_serializable_state() -> None:
    state: dict[str, object] = {}
    snapshot = RevisionSnapshot(data=2, calculation=3, presentation=4, export=5)
    persist_revisions(state, snapshot)
    assert revision_controller_from_state(state).snapshot == snapshot


def test_las_cache_uses_content_signature_and_returns_defensive_copies() -> None:
    cache = ParsedLasCache(max_entries=2)
    calls = 0

    def loader(source: object):
        nonlocal calls
        calls += 1
        return {"LAS": pd.DataFrame([["DEPT", "C1"], [1000.0, 1.5]])}

    first_source = BytesIO(b"same-las-content")
    second_source = BytesIO(b"same-las-content")
    first, first_signature, first_timing = cache.get_or_load(first_source, loader)
    first["LAS"].iloc[1, 1] = 999.0
    second, second_signature, second_timing = cache.get_or_load(second_source, loader)

    assert calls == 1
    assert first_signature == second_signature == content_signature(b"same-las-content")
    assert first_timing.cache_hit is False
    assert second_timing.cache_hit is True
    assert second["LAS"].iloc[1, 1] == 1.5


def test_las_cache_reloads_when_file_content_changes() -> None:
    cache = ParsedLasCache()
    calls = 0

    def loader(source: object):
        nonlocal calls
        calls += 1
        return {"LAS": pd.DataFrame([[calls]])}

    cache.get_or_load(BytesIO(b"version-1"), loader)
    cache.get_or_load(BytesIO(b"version-2"), loader)
    assert calls == 2
    assert len(cache) == 2


def test_dataframe_signature_is_content_based() -> None:
    first = pd.DataFrame({"depth": [1.0, 2.0], "c1": [3.0, 4.0]})
    second = first.copy()
    assert dataframe_signature(first) == dataframe_signature(second)
    second.loc[1, "c1"] = 5.0
    assert dataframe_signature(first) != dataframe_signature(second)


def test_initial_presentation_contracts_are_immutable_and_renderer_neutral() -> None:
    well_log = WellLogRenderModel(
        source_signature="abc",
        calculation_revision=1,
        presentation_revision=2,
        depth_range=(1000.0, 1100.0),
        tracks=("c1", "wh"),
        height=760,
        settings_signature="settings",
    )
    report = ReportDocumentModel(
        source_signature="abc",
        presentation_revision=2,
        export_revision=3,
        title="Engineering report",
        profile="engineering",
        sections=("summary", "well-log"),
    )
    assert well_log.tracks == ("c1", "wh")
    assert report.sections == ("summary", "well-log")


def test_applied_mapping_round_trip_and_source_guard():
    from core.presentation_runtime import (
        AppliedMappingState,
        applied_mapping_from_state,
        mapping_matches_source,
        persist_applied_mapping,
    )

    state: dict[str, object] = {}
    snapshot = AppliedMappingState(
        source_signature="abc123",
        sheet_name="Well A",
        header_row=2,
        mapping={"depth": "DEPT", "c1": "C1"},
        ch_mode="A",
    )
    persist_applied_mapping(state, snapshot)

    restored = applied_mapping_from_state(state)
    assert restored == snapshot
    assert mapping_matches_source(restored, "abc123") is True
    assert mapping_matches_source(restored, "different") is False


def test_applied_mapping_rejects_malformed_state():
    from core.presentation_runtime import applied_mapping_from_state

    assert applied_mapping_from_state({}) is None
    assert applied_mapping_from_state({"engineering_applied_mapping": {"mapping": []}}) is None


def test_applied_presentation_round_trip_and_revision_guard():
    from core.presentation_runtime import (
        AppliedPresentationState,
        applied_presentation_from_state,
        persist_applied_presentation,
        presentation_matches_source,
    )

    state: dict[str, object] = {}
    snapshot = AppliedPresentationState(
        source_signature="dataset-abc",
        calculation_revision=4,
        settings={"selected_tracks": ["C1-C5", "Планшет"], "height": 760},
    )
    persist_applied_presentation(state, snapshot)

    restored = applied_presentation_from_state(state)
    assert restored == snapshot
    assert presentation_matches_source(restored, "dataset-abc", 4) is True
    assert presentation_matches_source(restored, "dataset-other", 4) is False
    assert presentation_matches_source(restored, "dataset-abc", 5) is False


def test_applied_presentation_rejects_malformed_state():
    from core.presentation_runtime import applied_presentation_from_state

    assert applied_presentation_from_state({}) is None
    assert applied_presentation_from_state({"engineering_applied_presentation": {"settings": []}}) is None
    assert applied_presentation_from_state(
        {
            "engineering_applied_presentation": {
                "source_signature": "abc",
                "calculation_revision": -1,
                "settings": {},
            }
        }
    ) is None


def test_streamlit_operations_use_inline_status_without_spinner_overlay() -> None:
    source = (Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py").read_text(encoding="utf-8")

    assert "st.spinner(" not in source
    assert "grp-inline-operation" in source
    assert '_set_inline_operation_status(' in source
    assert 'export_progress.info(' not in source
    assert 'calculation_duration_ms' in source
    assert 'render_duration_ms' in source


def test_applied_correlation_round_trip_and_source_guard():
    from core.presentation_runtime import (
        AppliedCorrelationState,
        applied_correlation_from_state,
        correlation_matches_source,
        persist_applied_correlation,
    )

    state: dict[str, object] = {}
    snapshot = AppliedCorrelationState(
        source_signature="well-a:123|well-b:456",
        settings={"selected_well_names": ["Well A", "Well B"], "height_per_well": 430},
        studio_settings={"grid_mode": "union", "depth_step": 0.5, "markers": ({"name": "Top", "depth": 1000.0},)},
    )
    persist_applied_correlation(state, snapshot)

    restored = applied_correlation_from_state(state)
    assert restored == snapshot
    assert correlation_matches_source(restored, snapshot.source_signature) is True
    assert correlation_matches_source(restored, "other-source") is False


def test_applied_correlation_rejects_malformed_state():
    from core.presentation_runtime import applied_correlation_from_state

    assert applied_correlation_from_state({}) is None
    assert applied_correlation_from_state({"engineering_applied_correlation": {"settings": []}}) is None
    assert applied_correlation_from_state(
        {
            "engineering_applied_correlation": {
                "source_signature": "abc",
                "settings": {},
                "studio_settings": [],
            }
        }
    ) is None


def test_las_correlation_uses_explicit_apply_and_figure_cache():
    source = (Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py").read_text(encoding="utf-8")
    function_source = source[source.index("def _render_las_correlation_tab"):source.index("WORKBENCH_LAS_MODE_KEY")]

    button_position = function_source.index('"Построить корреляцию"')
    first_panel_build = function_source.index("build_correlation_panel(")
    first_main_build = function_source.index("build_las_correlation_figure(")

    assert button_position < first_panel_build
    assert button_position < first_main_build
    assert "las_correlation_figure_cache" in function_source
    assert "correlation_matches_source" in function_source
    assert "Черновые изменения не запускают Plotly-рендер" in function_source


def test_applied_export_round_trip_and_presentation_guard():
    from core.presentation_runtime import (
        AppliedExportState,
        applied_export_from_state,
        export_matches_source,
        persist_applied_export,
    )

    state: dict[str, object] = {}
    snapshot = AppliedExportState(
        source_signature="dataset-abc",
        presentation_revision=7,
        settings={"kind": "static_plotly", "width": 1600, "height": 1200},
    )
    persist_applied_export(state, snapshot)

    restored = applied_export_from_state(state)
    assert restored == snapshot
    assert export_matches_source(restored, "dataset-abc", 7) is True
    assert export_matches_source(restored, "dataset-other", 7) is False
    assert export_matches_source(restored, "dataset-abc", 8) is False


def test_applied_export_rejects_malformed_state():
    from core.presentation_runtime import applied_export_from_state

    assert applied_export_from_state({}) is None
    assert applied_export_from_state({"engineering_applied_export": {"settings": []}}) is None
    assert applied_export_from_state(
        {
            "engineering_applied_export": {
                "source_signature": "abc",
                "presentation_revision": -1,
                "settings": {},
            }
        }
    ) is None


def test_expensive_exports_require_explicit_actions():
    source = (Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py").read_text(encoding="utf-8")

    assert "Подготовить PNG, PDF и SVG" in source
    assert "Подготовить HTML и отчет интервала" in source
    assert "Подготовить CSV выбранного интервала" in source
    assert "Подготовить HTML корреляции" in source
    assert "Подготовить PNG/PDF/SVG файлы" not in source
    assert "interpretation_interval_csv_completed" in source
    assert "las_correlation_html_export_completed" in source
