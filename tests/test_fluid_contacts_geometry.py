from pathlib import Path

import pytest

from projects.fluid_contacts_geometry import (
    FluidContact,
    GridCellGeometry,
    build_contact_set_cells,
    build_contact_set_table,
    build_fluid_contact_table,
    build_fluid_geometry_manifest,
    build_geometry_properties,
    build_geometry_property_table,
    calculate_above_contact,
    calculate_bulk_volume,
    calculate_cell_height,
    calculate_cell_mid_depth,
    calculate_cell_volume,
    classify_contact_zone,
    create_fluid_geometry_job,
    list_fluid_geometry_contacts,
    list_fluid_geometry_jobs,
    render_fluid_geometry_markdown,
    save_fluid_contact,
    seed_fluid_geometry_workspace,
    summarize_geometry_properties,
)


def test_cell_geometry_calculations():
    cell = GridCellGeometry("c1", top_m=1000, base_m=1010, x_size_m=20, y_size_m=30)
    assert calculate_cell_height(cell) == 10
    assert calculate_cell_volume(cell) == 6000
    assert calculate_cell_mid_depth(cell) == 1005
    assert calculate_above_contact(cell, 1020) == 15


def test_bulk_volume_from_dict_cells():
    cells = [
        {"cell_id": "a", "top_m": 0, "base_m": 10, "x_size_m": 2, "y_size_m": 3},
        {"cell_id": "b", "top_m": 10, "base_m": 20, "x_size_m": 2, "y_size_m": 3},
    ]
    assert calculate_bulk_volume(cells) == 120


def test_classify_contact_zone_with_owc_and_goc():
    assert classify_contact_zone(1500, owc_m=1700, goc_m=1600) == "gas"
    assert classify_contact_zone(1650, owc_m=1700, goc_m=1600) == "oil"
    assert classify_contact_zone(1800, owc_m=1700, goc_m=1600) == "water"
    assert classify_contact_zone(1650) == "unknown"


def test_contact_set_cells_and_table():
    cells = [GridCellGeometry("gas", 1500, 1510), GridCellGeometry("oil", 1650, 1660), GridCellGeometry("water", 1800, 1810)]
    contact_set = build_contact_set_cells(cells, owc_m=1700, goc_m=1600)
    table = build_contact_set_table(contact_set)
    assert [row["zone"] for row in table] == ["gas", "oil", "water"]
    assert table[0]["zone_code"] == 1
    assert table[2]["zone_code"] == 3


def test_build_geometry_properties_and_summary():
    cells = [GridCellGeometry("c1", 1000, 1010, 10, 10), GridCellGeometry("c2", 1010, 1020, 10, 10)]
    props = build_geometry_properties(cells, contact_depth_m=1030, reference_depth_m=1000)
    table = build_geometry_property_table(props)
    summary = summarize_geometry_properties(props)
    assert any(row["property"] == "Above Contact" for row in table)
    assert summary["cell_volume"]["mean"] == 1000
    assert summary["above_contact"]["count"] == 2.0


def test_save_contacts_and_jobs(tmp_path: Path):
    contact = save_fluid_contact(tmp_path, "demo", FluidContact("OWC", "owc", depth_m=1683.0, confidence=0.9))
    job = create_fluid_geometry_job(tmp_path, "demo", name="Geometry Run", contact_names=("OWC",))
    assert contact.name == "OWC"
    assert list_fluid_geometry_contacts(tmp_path, "demo")[0].depth_m == 1683.0
    assert list_fluid_geometry_jobs(tmp_path, "demo")[0].job_id == "geometry_run"
    assert build_fluid_contact_table((contact,))[0]["type"] == "OWC"
    assert job.status == "planned"


def test_duplicate_contact_policy(tmp_path: Path):
    save_fluid_contact(tmp_path, "demo", {"name": "OWC", "contact_type": "owc", "depth_m": 1000})
    with pytest.raises(ValueError):
        save_fluid_contact(tmp_path, "demo", {"name": "OWC", "contact_type": "owc", "depth_m": 1001}, replace=False)


def test_seed_manifest_and_markdown(tmp_path: Path):
    seed_fluid_geometry_workspace(tmp_path, "demo", overwrite=True)
    cells = [GridCellGeometry("c1", 1600, 1610), GridCellGeometry("c2", 1700, 1710)]
    props = build_geometry_properties(cells, contact_depth_m=1683)
    contact_set = build_contact_set_cells(cells, owc_m=1683, goc_m=1610)
    manifest = build_fluid_geometry_manifest(tmp_path, "demo", geometry_properties=props)
    report = render_fluid_geometry_markdown(tmp_path, "demo", geometry_properties=props, contact_set_cells=contact_set)
    assert manifest.contact_count >= 2
    assert manifest.job_count >= 1
    assert manifest.geometry_property_count == len(props)
    assert "Fluid Contacts & Geometrical Properties Report" in report
    assert "Contact Set Preview" in report


def test_invalid_values_rejected():
    with pytest.raises(ValueError):
        calculate_cell_height({"cell_id": "bad", "top_m": 10, "base_m": 0})
    with pytest.raises(ValueError):
        save_fluid_contact(Path("/tmp/nonexistent"), "demo", {"name": "BAD", "contact_type": "bad", "depth_m": 1})
