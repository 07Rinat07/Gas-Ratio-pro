from __future__ import annotations

from pathlib import Path

import pytest

from projects import create_project, save_project_well_card
from projects.formation_manager import (
    build_formation_manager_table,
    export_formation_objects_csv,
    filter_formation_objects,
    import_formation_objects_csv,
    list_formation_objects,
    save_formation_object,
    summarize_formation_manager,
)


def test_formation_manager_saves_tops_contacts_horizons_and_markers(tmp_path: Path):
    project = create_project(tmp_path, name="Formation Demo")
    save_project_well_card(tmp_path, project.id, "well-01", "Well 01")

    top = save_formation_object(tmp_path, project.id, "A10", object_type="top", well_id="well-01", md_m=1510, tvd_m=1502, color="#ffaa00")
    contact = save_formation_object(tmp_path, project.id, "OWC", object_type="contact", well_id="well-01", md_m=1642.5, source="interpretation")
    horizon = save_formation_object(tmp_path, project.id, "Regional H1", object_type="horizon", color="#00aaff")
    marker = save_formation_object(tmp_path, project.id, "Core point", object_type="marker", well_id="well-01", md_m=1535)

    summary = summarize_formation_manager(tmp_path, project.id)

    assert top.name == "A10"
    assert contact.source == "interpretation"
    assert horizon.well_id == ""
    assert marker.md_m == 1535
    assert summary.objects == 4
    assert summary.tops == 1
    assert summary.contacts == 1
    assert summary.horizons == 1
    assert summary.markers == 1
    assert summary.wells == 1


def test_formation_manager_filters_tables_and_csv_roundtrip(tmp_path: Path):
    project = create_project(tmp_path, name="Formation CSV")
    save_formation_object(tmp_path, project.id, "A10", object_type="top", well_id="well-01", md_m=1510, note="north block")
    save_formation_object(tmp_path, project.id, "B20", object_type="top", well_id="well-02", md_m=1810)

    filtered = filter_formation_objects(list_formation_objects(tmp_path, project.id), query="north", object_type="top")
    table = build_formation_manager_table(filtered)
    csv_text = export_formation_objects_csv(filtered)
    imported = import_formation_objects_csv(tmp_path, project.id, csv_text)

    assert len(filtered) == 1
    assert table[0]["Название"] == "A10"
    assert "north block" in csv_text
    assert imported[0].name == "A10"


def test_formation_manager_validates_engineering_inputs(tmp_path: Path):
    project = create_project(tmp_path, name="Formation Validation")

    with pytest.raises(ValueError, match="Тип объекта"):
        save_formation_object(tmp_path, project.id, "Bad", object_type="bad")

    with pytest.raises(ValueError, match="MD"):
        save_formation_object(tmp_path, project.id, "No MD", object_type="contact")

    with pytest.raises(ValueError, match="0..15000"):
        save_formation_object(tmp_path, project.id, "Deep", object_type="top", md_m=20000)
