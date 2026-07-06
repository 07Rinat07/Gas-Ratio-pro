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
