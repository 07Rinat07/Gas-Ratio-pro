from projects.structural_modeling_workspace import (
    StructuralZone,
    build_structural_fault_table,
    build_structural_horizon_table,
    build_structural_layer_table,
    build_structural_modeling_manifest,
    build_structural_zone_table,
    generate_layers_for_zone,
    list_structural_faults,
    list_structural_horizons,
    list_structural_layers,
    list_structural_zones,
    render_structural_modeling_markdown,
    save_structural_fault,
    save_structural_horizon,
    save_structural_layer,
    save_structural_surface,
    save_structural_zone,
    seed_structural_modeling_workspace,
    validate_structural_modeling_workspace,
)


def test_seed_workspace_creates_structural_objects(tmp_path):
    seed_structural_modeling_workspace("demo", tmp_path)

    assert len(list_structural_horizons("demo", tmp_path)) == 2
    assert len(list_structural_zones("demo", tmp_path)) == 1
    assert len(list_structural_layers("demo", tmp_path)) == 4
    assert len(list_structural_faults("demo", tmp_path)) == 1

    manifest = build_structural_modeling_manifest("demo", tmp_path)
    assert manifest.horizon_count == 2
    assert manifest.layer_count == 4
    assert manifest.error_count == 0


def test_generate_layers_for_zone_builds_equal_layers():
    zone = StructuralZone(
        zone_id="z1",
        name="Zone 1",
        top_horizon_id="h1",
        base_horizon_id="h2",
        layer_count=4,
    )

    layers = generate_layers_for_zone(zone, 1000, 1100)

    assert len(layers) == 4
    assert layers[0].top_depth == 1000
    assert layers[-1].base_depth == 1100
    assert all(layer.thickness_m == 25 for layer in layers)


def test_validation_reports_missing_zone_horizon(tmp_path):
    save_structural_horizon({"horizon_id": "top", "name": "Top", "order": 1}, "demo", tmp_path)
    save_structural_zone(
        {
            "zone_id": "z1",
            "name": "Broken Zone",
            "top_horizon_id": "top",
            "base_horizon_id": "missing",
            "layer_count": 2,
        },
        "demo",
        tmp_path,
    )

    issues = validate_structural_modeling_workspace("demo", tmp_path)

    assert any(issue.code == "MISSING_BASE_HORIZON" for issue in issues)
    assert build_structural_modeling_manifest("demo", tmp_path).error_count == 1


def test_fault_links_are_validated(tmp_path):
    save_structural_horizon({"horizon_id": "top", "name": "Top", "order": 1}, "demo", tmp_path)
    save_structural_fault(
        {
            "fault_id": "f1",
            "name": "Fault",
            "fault_type": "normal",
            "linked_horizon_ids": ["top", "missing"],
        },
        "demo",
        tmp_path,
    )

    issues = validate_structural_modeling_workspace("demo", tmp_path)

    assert any(issue.code == "MISSING_FAULT_HORIZON_LINK" for issue in issues)


def test_ui_tables_and_markdown_report(tmp_path):
    seed_structural_modeling_workspace("demo", tmp_path)

    assert build_structural_horizon_table("demo", tmp_path)
    assert build_structural_fault_table("demo", tmp_path)
    assert build_structural_zone_table("demo", tmp_path)
    assert build_structural_layer_table("demo", tmp_path)

    report = render_structural_modeling_markdown("demo", tmp_path)
    assert "Structural Modeling Workspace" in report
    assert "Top Reservoir" in report
    assert "Reservoir Zone" in report


def test_invalid_surface_depth_range_detected(tmp_path):
    save_structural_surface({"surface_id": "s1", "name": "Broken", "role": "horizon", "min_z": 2000, "max_z": 1000}, "demo", tmp_path)
    save_structural_horizon({"horizon_id": "h1", "name": "H1", "order": 1, "surface_id": "s1", "min_depth": 2000, "max_depth": 1000}, "demo", tmp_path)

    issues = validate_structural_modeling_workspace("demo", tmp_path)
    assert any(issue.code == "INVALID_HORIZON_DEPTH_RANGE" for issue in issues)


def test_save_generated_layers(tmp_path):
    save_structural_horizon({"horizon_id": "h1", "name": "Top", "order": 1}, "demo", tmp_path)
    save_structural_horizon({"horizon_id": "h2", "name": "Base", "order": 2}, "demo", tmp_path)
    zone = save_structural_zone({"zone_id": "z", "name": "Z", "top_horizon_id": "h1", "base_horizon_id": "h2", "layer_count": 3}, "demo", tmp_path)
    for layer in generate_layers_for_zone(zone, 0, 30):
        save_structural_layer(layer, "demo", tmp_path)

    layers = list_structural_layers("demo", tmp_path)
    assert len(layers) == 3
    assert layers[1].top_depth == 10
