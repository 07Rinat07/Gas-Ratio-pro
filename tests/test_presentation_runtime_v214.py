from __future__ import annotations

from io import BytesIO

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
