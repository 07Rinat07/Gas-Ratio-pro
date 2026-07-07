from pathlib import Path

import pytest

from las_correlation import CorrelationMarker
from projects import create_project
from projects.correlation_studio import (
    build_correlation_export_manifest,
    build_correlation_session_table,
    delete_correlation_session,
    export_correlation_session_json,
    get_correlation_session,
    import_correlation_session_json,
    list_correlation_sessions,
    save_correlation_session,
    summarize_correlation_sessions,
)


def _session_payload():
    return {
        "id": "demo-session",
        "name": "Demo multi-well correlation",
        "wells": ["Well-A", "Well-B"],
        "markers": [
            {"well": "Well-A", "name": "Top A", "depth": 1000.0, "kind": "formation", "color": "#f59e0b"},
            {"well": "Well-B", "name": "Top A", "depth": 1002.5, "kind": "formation", "color": "#f59e0b"},
        ],
        "lines": [
            {
                "source_well": "Well-A",
                "target_well": "Well-B",
                "name": "Top A",
                "source_depth": 1000.0,
                "target_depth": 1002.5,
                "confidence": 0.9,
            }
        ],
        "alignments": [{"well": "Well-B", "shift": -2.5, "reference": "Top A"}],
        "depth_range": [990, 1040],
        "selected_groups": ["gamma", "resistivity"],
        "grid_mode": "overlap",
        "status": "active",
    }


def test_correlation_session_crud_summary_and_table(tmp_path: Path):
    project = create_project(tmp_path, name="Correlation Demo")

    saved = save_correlation_session(tmp_path, project.id, _session_payload())
    sessions = list_correlation_sessions(tmp_path, project.id)
    table = build_correlation_session_table(sessions)
    summary = summarize_correlation_sessions(sessions)

    assert sessions == (saved,)
    assert get_correlation_session(tmp_path, project.id, "demo-session") == saved
    assert table[0]["Скважины"] == 2
    assert table[0]["Линии"] == 1
    assert summary.active == 1
    assert summary.markers == 2
    assert summary.alignments == 1

    assert delete_correlation_session(tmp_path, project.id, "demo-session") is True
    assert list_correlation_sessions(tmp_path, project.id) == ()


def test_correlation_session_json_roundtrip():
    session = save_payload = _session_payload()
    imported = import_correlation_session_json(export_correlation_session_json(import_correlation_session_json(__import__("json").dumps(save_payload))))

    assert imported.id == "demo-session"
    assert imported.wells == ("Well-A", "Well-B")
    assert imported.markers[0].name == "Top A"
    assert imported.lines[0].confidence == 0.9


def test_correlation_session_requires_well_and_valid_status(tmp_path: Path):
    project = create_project(tmp_path, name="Validation Demo")

    with pytest.raises(ValueError, match="минимум одну скважину"):
        save_correlation_session(tmp_path, project.id, {"name": "Broken", "wells": []})

    with pytest.raises(ValueError, match="Статус"):
        save_correlation_session(tmp_path, project.id, {**_session_payload(), "status": "published"})


def test_correlation_export_manifest_formats():
    session = import_correlation_session_json(__import__("json").dumps(_session_payload()))

    manifest = build_correlation_export_manifest(session, formats=("json", "svg", "pdf", "json"))

    assert manifest["session_id"] == "demo-session"
    assert manifest["formats"] == ("json", "svg", "pdf")
    assert manifest["markers"] == 2
    assert manifest["lines"] == 1


def test_correlation_session_accepts_marker_objects(tmp_path: Path):
    project = create_project(tmp_path, name="Object Demo")

    saved = save_correlation_session(
        tmp_path,
        project.id,
        {
            "id": "object-session",
            "name": "Object session",
            "wells": ["Well-A"],
            "markers": [CorrelationMarker(well="Well-A", name="Top B", depth=1010.0).__dict__],
        },
    )

    assert saved.markers[0].name == "Top B"
