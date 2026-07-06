from __future__ import annotations

from pathlib import Path

import pytest

from projects import (
    build_project_well_manager_table,
    create_project,
    filter_project_well_manager_records,
    list_project_formation_tops,
    list_project_trajectory_stations,
    list_project_well_manager_records,
    list_project_well_notes,
    project_well_manager_status,
    save_project_formation_top,
    save_project_trajectory_station,
    save_project_well_card,
    save_project_well_note,
)
from projects.well_cards import (
    merge_project_well_coordinates_metadata,
    merge_project_well_depth_reference_metadata,
    merge_project_well_drilling_dates_metadata,
    merge_project_well_field_metadata,
    merge_project_well_operator_metadata,
)


def _save_ready_well(root: Path, project_id: str):
    metadata = {}
    metadata = merge_project_well_coordinates_metadata(metadata, x="421000.5", y="5123400.25", latitude="47.5", longitude="53.2")
    metadata = merge_project_well_depth_reference_metadata(metadata, kb_m="145.5", gl_m="140.0", planned_td_m="3200", actual_td_m="3188")
    metadata = merge_project_well_drilling_dates_metadata(metadata, spud_date="2026-01-20")
    metadata = merge_project_well_operator_metadata(metadata, operator="Demo Operator")
    metadata = merge_project_well_field_metadata(metadata, field="Demo Field")
    return save_project_well_card(root, project_id, "well-01", "Well 01", "ready", "Base metadata", metadata)


def test_well_manager_saves_tops_trajectory_and_notes(tmp_path: Path):
    project = create_project(tmp_path, name="Well Manager Demo")
    _save_ready_well(tmp_path, project.id)

    top = save_project_formation_top(tmp_path, project.id, "well-01", "A10", 1520.5, tvd_m="1512.4", color="#9ad")
    station = save_project_trajectory_station(tmp_path, project.id, "well-01", 1000, 12.5, 178.0, tvd_m=992, north_m=8, east_m=-3)
    note = save_project_well_note(tmp_path, project.id, "well-01", "Проверить tops", "Согласовать с геологом", category="qa")

    assert top.md_m == 1520.5
    assert station.azimuth_deg == 178.0
    assert note.category == "qa"
    assert len(list_project_formation_tops(tmp_path, project.id, "well-01")) == 1
    assert len(list_project_trajectory_stations(tmp_path, project.id, "well-01")) == 1
    assert len(list_project_well_notes(tmp_path, project.id, "well-01")) == 1


def test_well_manager_records_filter_and_status(tmp_path: Path):
    project = create_project(tmp_path, name="Well Filter Demo")
    _save_ready_well(tmp_path, project.id)
    save_project_formation_top(tmp_path, project.id, "well-01", "A10", 1520.5)
    save_project_trajectory_station(tmp_path, project.id, "well-01", 1000, 12.5, 178.0)
    save_project_well_note(tmp_path, project.id, "well-01", "QA", "Ready")

    records = list_project_well_manager_records(tmp_path, project.id)
    filtered = filter_project_well_manager_records(records, query="demo field", status="ready")
    table = build_project_well_manager_table(filtered)
    status = project_well_manager_status(tmp_path, project.id)

    assert len(records) == 1
    assert filtered[0].completeness_percent == 100
    assert table[0]["Пласты"] == 1
    assert status["average_completeness_percent"] == 100
    assert status["trajectory_stations"] == 1


def test_well_manager_validates_engineering_ranges(tmp_path: Path):
    project = create_project(tmp_path, name="Well Validation Demo")

    with pytest.raises(ValueError, match="MD пласта"):
        save_project_formation_top(tmp_path, project.id, "well-01", "Bad", -1)

    with pytest.raises(ValueError, match="Азимут"):
        save_project_trajectory_station(tmp_path, project.id, "well-01", 100, 10, 360)

    with pytest.raises(ValueError, match="Текст заметки"):
        save_project_well_note(tmp_path, project.id, "well-01", "Empty", "")
