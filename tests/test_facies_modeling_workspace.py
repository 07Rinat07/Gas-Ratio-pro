from pathlib import Path

import pytest

from projects.facies_modeling_workspace import (
    FaciesDefinition,
    FaciesZoneSettings,
    build_default_facies_modeling_seed,
    build_facies_definition_table,
    build_facies_modeling_manifest,
    build_facies_statistics_table,
    build_facies_zone_table,
    build_vertical_proportion_curves,
    build_vertical_proportion_table,
    calculate_facies_statistics,
    list_facies_definitions,
    list_facies_simulation_jobs,
    list_facies_zones,
    normalize_facies_values,
    render_facies_modeling_markdown,
    save_facies_definition,
    save_facies_simulation_job,
    save_facies_zone,
    seed_facies_modeling_workspace,
)


def test_normalize_facies_values():
    assert normalize_facies_values(["Sand", "Shaly Sand", None, ""]) == ("sand", "shaly_sand", "undefined", "undefined")


def test_calculate_facies_statistics_counts_runs():
    stats = calculate_facies_statistics(["Sand", "Sand", "Shale", "Sand"])
    table = {row.facies_code: row for row in stats}
    assert table["sand"].sample_count == 3
    assert table["sand"].proportion == pytest.approx(0.75)
    assert table["sand"].max_run == 2
    assert table["shale"].sample_count == 1


def test_build_vertical_proportion_curves():
    layers = build_vertical_proportion_curves([1000, 1001, 1002, 1003], ["Sand", "Shale", "Sand", "Sand"], layer_count=2)
    assert len(layers) == 2
    assert layers[0].sample_count == 2
    assert layers[0].proportions["sand"] == pytest.approx(0.5)
    assert layers[1].proportions["sand"] == pytest.approx(1.0)


def test_save_and_list_facies_definition(tmp_path: Path):
    save_facies_definition(tmp_path, "demo", FaciesDefinition("sand", "Sand", is_reservoir=True, is_pay_candidate=True))
    definitions = list_facies_definitions(tmp_path, "demo")
    assert definitions[0].code == "sand"
    assert definitions[0].is_reservoir is True


def test_duplicate_facies_definition_policy(tmp_path: Path):
    save_facies_definition(tmp_path, "demo", {"code": "sand", "name": "Sand"})
    with pytest.raises(ValueError):
        save_facies_definition(tmp_path, "demo", {"code": "sand", "name": "Sand"}, replace=False)


def test_save_zone_and_job(tmp_path: Path):
    zone = save_facies_zone(
        tmp_path,
        "demo",
        FaciesZoneSettings("P2", top_depth=1000, base_depth=1100, allowed_facies=("sand", "shale"), trend_type="vertical"),
    )
    job = save_facies_simulation_job(tmp_path, "demo", {"name": "P2 facies", "zone_name": "P2", "method": "vertical_proportion_curve"})
    assert zone.zone_name == "P2"
    assert list_facies_zones(tmp_path, "demo")[0].allowed_facies == ("sand", "shale")
    assert job.created_at
    assert list_facies_simulation_jobs(tmp_path, "demo")[0].name == "P2 facies"


def test_invalid_zone_depth_rejected(tmp_path: Path):
    with pytest.raises(ValueError):
        save_facies_zone(tmp_path, "demo", {"zone_name": "bad", "top_depth": 1200, "base_depth": 1100})


def test_seed_manifest_tables_and_markdown(tmp_path: Path):
    seed_facies_modeling_workspace(tmp_path, "demo", author="Rinat", overwrite=True)
    manifest = build_facies_modeling_manifest(tmp_path, "demo")
    report = render_facies_modeling_markdown(tmp_path, "demo")
    assert manifest.facies_count >= 6
    assert manifest.zone_count >= 2
    assert manifest.warnings == ()
    assert "Facies Modeling Workspace Report" in report
    assert "docs/sources/lab-4-property-cubes.pdf" in report
    assert build_facies_definition_table(list_facies_definitions(tmp_path, "demo"))[0]["code"]
    assert build_facies_zone_table(list_facies_zones(tmp_path, "demo"))[0]["zone"]


def test_default_seed_contains_core_facies():
    seed = build_default_facies_modeling_seed(author="Rinat")
    codes = {row["code"] for row in seed["facies"]}
    assert {"sand", "shale", "shaly_sand", "undefined"}.issubset(codes)


def test_ui_statistics_tables():
    stats_table = build_facies_statistics_table(calculate_facies_statistics(["Sand", "Shale", "Sand"]))
    vpc_table = build_vertical_proportion_table(build_vertical_proportion_curves([1, 2, 3], ["Sand", "Shale", "Sand"], layer_count=1))
    assert stats_table[0]["facies"]
    assert vpc_table[0]["samples"] == 3
