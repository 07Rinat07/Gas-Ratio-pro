from pathlib import Path

import pytest

from projects import create_project
from projects.formation_manager import save_formation_object, list_formation_objects
from projects.geological_modeling import (
    build_cross_section_node_table,
    build_geological_model_state,
    build_reservoir_zone_table,
    build_stratigraphic_zone_table,
    build_stratigraphic_zones_from_tops,
    export_geological_model_csv,
    load_project_geological_model_state,
    normalize_reservoir_zones,
    validate_stratigraphic_zones,
)


def _formation_demo(tmp_path: Path):
    project = create_project(tmp_path, name="Geo Model Demo")
    save_formation_object(tmp_path, project.id, "A10", object_type="top", well_id="well-01", md_m=1000.0, tvd_m=995.0)
    save_formation_object(tmp_path, project.id, "B20", object_type="top", well_id="well-01", md_m=1100.0, tvd_m=1090.0)
    save_formation_object(tmp_path, project.id, "C30", object_type="top", well_id="well-01", md_m=1250.0, tvd_m=1235.0)
    save_formation_object(tmp_path, project.id, "A10", object_type="top", well_id="well-02", md_m=1020.0, tvd_m=1010.0)
    save_formation_object(tmp_path, project.id, "B20", object_type="top", well_id="well-02", md_m=1130.0, tvd_m=1118.0)
    save_formation_object(tmp_path, project.id, "OWC", object_type="contact", well_id="well-01", md_m=1190.0)
    return project


def test_build_stratigraphic_zones_from_consecutive_tops(tmp_path: Path):
    project = _formation_demo(tmp_path)
    zones = build_stratigraphic_zones_from_tops(list_formation_objects(tmp_path, project.id))
    table = build_stratigraphic_zone_table(zones)

    assert len(zones) == 3
    assert zones[0].name == "A10-B20"
    assert zones[0].thickness_m == 100.0
    assert table[0]["Толщина, м"] == 100.0


def test_reservoir_zone_normalization_classifies_quality():
    reservoirs = normalize_reservoir_zones([
        {"zone_name": "A10-B20", "well_id": "well-01", "gross_m": 100, "net_m": 65, "avg_vsh": 0.22, "avg_phie": 0.19, "avg_sw": 0.38},
        {"zone_name": "B20-C30", "gross_m": 150, "net_m": 20, "avg_vsh": 0.70, "avg_phie": 0.07, "avg_sw": 0.80},
    ])
    table = build_reservoir_zone_table(reservoirs)

    assert reservoirs[0].quality == "good"
    assert reservoirs[1].quality == "poor"
    assert table[0]["NTG"] == 0.65


def test_geological_model_state_builds_nodes_summary_and_csv(tmp_path: Path):
    project = _formation_demo(tmp_path)
    state = load_project_geological_model_state(
        tmp_path,
        project.id,
        reservoir_rows=[{"zone_name": "A10-B20", "well_id": "well-01", "gross_m": 100, "net_m": 55}],
        well_spacing_m=750,
    )
    node_table = build_cross_section_node_table(state.cross_section_nodes)
    csv_text = export_geological_model_csv(state)

    assert state.summary.zones == 3
    assert state.summary.reservoir_zones == 1
    assert state.summary.wells == 2
    assert any(row["X, м"] == 750 for row in node_table)
    assert "A10-B20" in csv_text
    assert "reservoir" in csv_text


def test_geological_model_validation_and_inputs():
    with pytest.raises(ValueError, match="Net"):
        normalize_reservoir_zones([{"zone_name": "Bad", "gross_m": 10, "net_m": 11}])

    state = build_geological_model_state([], reservoir_rows=[])
    assert state.summary.zones == 0
    assert validate_stratigraphic_zones([]) == {"errors": (), "warnings": ()}

from projects.geological_modeling import (
    build_zone_color_scheme,
    build_zone_manager_table,
    delete_project_geological_zone,
    list_project_geological_zones,
    merge_stratigraphic_zones,
    save_project_geological_zone,
    split_stratigraphic_zone,
    StratigraphicZone,
)


def test_zone_manager_crud_persistence_and_table(tmp_path: Path):
    project = create_project(tmp_path, name="Zone Manager Demo")

    saved = save_project_geological_zone(
        tmp_path,
        project.id,
        "A10-B20",
        well_id="well-01",
        top_name="A10",
        base_name="B20",
        top_md_m="1000,0",
        base_md_m=1100,
        zone_type="reservoir",
        color="#336699",
        note="Engineer-approved interval",
    )
    zones = list_project_geological_zones(tmp_path, project.id)
    table = build_zone_manager_table(zones)

    assert saved.well_id == "well-01"
    assert zones == (saved,)
    assert table[0]["Толщина, м"] == 100.0
    assert table[0]["Цвет"] == "#336699"

    assert delete_project_geological_zone(tmp_path, project.id, "A10-B20", well_id="well-01") is True
    assert list_project_geological_zones(tmp_path, project.id) == ()


def test_zone_manager_merge_split_and_color_scheme():
    z1 = StratigraphicZone(
        name="A-B",
        top_name="A",
        base_name="B",
        well_id="well-01",
        top_md_m=1000.0,
        base_md_m=1100.0,
        zone_type="formation",
        color="",
    )
    z2 = StratigraphicZone(
        name="B-C",
        top_name="B",
        base_name="C",
        well_id="well-01",
        top_md_m=1100.0,
        base_md_m=1200.0,
        zone_type="formation",
        color="",
    )

    merged = merge_stratigraphic_zones([z1, z2], "A-C", color="#123456")
    upper, lower = split_stratigraphic_zone(merged, 1125, upper_name="A-M", lower_name="M-C", split_marker_name="M")
    scheme = build_zone_color_scheme([upper, lower])

    assert merged.top_md_m == 1000.0
    assert merged.base_md_m == 1200.0
    assert upper.base_name == "M"
    assert lower.top_name == "M"
    assert upper.thickness_m == 125.0
    assert scheme["A-M"] == "#123456"


def test_zone_manager_rejects_invalid_merge_and_split(tmp_path: Path):
    project = create_project(tmp_path, name="Zone Manager Validation")
    zone = save_project_geological_zone(
        tmp_path,
        project.id,
        "A-B",
        top_name="A",
        base_name="B",
        top_md_m=100,
        base_md_m=200,
    )

    with pytest.raises(ValueError, match="внутри зоны"):
        split_stratigraphic_zone(zone, 250)

    with pytest.raises(ValueError, match="минимум две"):
        merge_stratigraphic_zones([zone], "bad")
