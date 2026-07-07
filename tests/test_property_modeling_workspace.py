from pathlib import Path

import pytest

from projects.property_modeling_workspace import (
    FluidContactSpec,
    GeometryPropertySpec,
    PropertyCubeSpec,
    build_default_property_modeling_seed,
    build_fluid_contact_table,
    build_net_gross_property_cube,
    build_property_cube_table,
    build_property_modeling_manifest,
    calculate_net_gross_from_facies,
    calculate_property_statistics,
    list_fluid_contacts,
    list_geometry_properties,
    list_property_cubes,
    render_property_modeling_markdown,
    save_fluid_contact,
    save_geometry_property,
    save_property_cube,
    seed_property_modeling_workspace,
)


def test_calculate_net_gross_from_facies_accepts_common_sand_labels():
    values = ["Sand", "Shale", "sandstone", "Limestone", 1, 0, "reservoir"]
    assert calculate_net_gross_from_facies(values) == (1, 0, 1, 0, 1, 0, 1)


def test_build_net_gross_property_cube_returns_metadata_and_values():
    cube, values = build_net_gross_property_cube(["Sand", "Shale", "Sand"], author="Tester")
    assert cube.name == "NG"
    assert cube.property_type == "net_gross"
    assert cube.status == "computed"
    assert cube.statistics["mean"] == pytest.approx(2 / 3)
    assert values == (1, 0, 1)


def test_calculate_property_statistics_ignores_nulls():
    stats = calculate_property_statistics([1, 2, -999.25, None, "", 4])
    assert stats["count"] == 3.0
    assert stats["min"] == 1
    assert stats["max"] == 4
    assert stats["mean"] == pytest.approx(7 / 3)


def test_save_and_list_property_cube(tmp_path: Path):
    cube = save_property_cube(
        tmp_path,
        "demo",
        PropertyCubeSpec(name="POR", property_type="porosity", unit="fraction", statistics={"mean": 0.2}),
    )
    assert cube.created_at
    cubes = list_property_cubes(tmp_path, "demo")
    assert len(cubes) == 1
    assert cubes[0].name == "POR"
    assert list_property_cubes(tmp_path, "demo", property_type="porosity")[0].unit == "fraction"


def test_property_cube_duplicate_policy(tmp_path: Path):
    save_property_cube(tmp_path, "demo", {"name": "POR", "property_type": "porosity"})
    with pytest.raises(ValueError):
        save_property_cube(tmp_path, "demo", {"name": "POR", "property_type": "porosity"}, replace=False)


def test_save_contacts_and_geometry(tmp_path: Path):
    contact = save_fluid_contact(tmp_path, "demo", FluidContactSpec(name="OWC", contact_type="owc", depth_m=-1683.0))
    geometry = save_geometry_property(tmp_path, "demo", GeometryPropertySpec(name="Above OWC", method="above_contact", contact_name="OWC"))
    assert contact.depth_m == -1683.0
    assert list_fluid_contacts(tmp_path, "demo")[0].name == "OWC"
    assert geometry.method == "above_contact"
    assert list_geometry_properties(tmp_path, "demo")[0].contact_name == "OWC"


def test_seed_workspace_and_manifest(tmp_path: Path):
    seed_property_modeling_workspace(tmp_path, "demo", author="Rinat", overwrite=True)
    manifest = build_property_modeling_manifest(tmp_path, "demo")
    assert manifest.property_count >= 5
    assert manifest.contact_count >= 2
    assert manifest.geometry_count >= 3
    assert manifest.warnings == ()


def test_ui_tables_and_markdown(tmp_path: Path):
    seed_property_modeling_workspace(tmp_path, "demo", overwrite=True)
    cubes = list_property_cubes(tmp_path, "demo")
    contacts = list_fluid_contacts(tmp_path, "demo")
    cube_table = build_property_cube_table(cubes)
    contact_table = build_fluid_contact_table(contacts)
    report = render_property_modeling_markdown(tmp_path, "demo")
    assert cube_table[0]["name"]
    assert contact_table[0]["name"]
    assert "Property Modeling Workspace Report" in report
    assert "Net/Gross" not in report or "NG" in report


def test_invalid_property_type_rejected(tmp_path: Path):
    with pytest.raises(ValueError):
        save_property_cube(tmp_path, "demo", {"name": "BAD", "property_type": "unknown"})


def test_default_seed_contains_required_foundation_items():
    seed = build_default_property_modeling_seed(author="Rinat")
    names = {row["name"] for row in seed["properties"]}
    assert {"Facies", "NG", "POR", "PERM", "SW"}.issubset(names)
