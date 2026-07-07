from projects.geological_model_workspace import (
    FaultDefinition,
    GeologicalModel,
    GridDefinition,
    HorizonDefinition,
    ModelLink,
    SurfaceDefinition,
    ZoneDefinition,
    build_geological_model_manifest,
    list_faults,
    list_geological_models,
    list_grids,
    list_horizons,
    list_model_links,
    list_surfaces,
    list_zones,
    render_geological_model_markdown,
    save_fault,
    save_geological_model,
    save_grid,
    save_horizon,
    save_model_link,
    save_surface,
    save_zone,
    seed_geological_model_workspace,
    validate_geological_model_workspace,
)


def test_seed_workspace_creates_model_grid_zone(tmp_path):
    seed_geological_model_workspace(tmp_path, "demo", author="Rinat", overwrite=True)
    assert len(list_geological_models(tmp_path, "demo")) == 1
    assert len(list_grids(tmp_path, "demo")) == 1
    assert len(list_horizons(tmp_path, "demo")) == 2
    assert len(list_zones(tmp_path, "demo")) == 1
    assert len(list_model_links(tmp_path, "demo")) == 2


def test_save_all_geological_model_objects(tmp_path):
    save_geological_model(tmp_path, "demo", GeologicalModel("m1", "Model 1", coordinate_reference_system="EPSG:4326"))
    save_grid(tmp_path, "demo", GridDefinition("g1", "Grid", ni=10, nj=20, nk=3))
    save_surface(tmp_path, "demo", SurfaceDefinition("s1", "Top", surface_type="horizon", min_z=-1200, max_z=-1100))
    save_horizon(tmp_path, "demo", HorizonDefinition("h1", "Top", 1, "s1"))
    save_horizon(tmp_path, "demo", HorizonDefinition("h2", "Base", 2))
    save_zone(tmp_path, "demo", ZoneDefinition("z1", "Zone", "h1", "h2", layer_count=5))
    save_fault(tmp_path, "demo", FaultDefinition("f1", "Fault", fault_type="normal", surface_id="s1"))
    save_model_link(tmp_path, "demo", ModelLink("l1", "property_cube", "POR", "POR", source_module="projects.property_modeling_workspace"))
    assert list_geological_models(tmp_path, "demo")[0].name == "Model 1"
    assert list_grids(tmp_path, "demo")[0].ni == 10
    assert list_zones(tmp_path, "demo")[0].layer_count == 5
    assert list_faults(tmp_path, "demo")[0].fault_type == "normal"


def test_validation_detects_missing_zone_horizon(tmp_path):
    save_zone(tmp_path, "demo", {"zone_id": "z1", "name": "Broken", "top_horizon_id": "missing_top", "base_horizon_id": "missing_base"})
    issues = validate_geological_model_workspace(tmp_path, "demo")
    assert len([issue for issue in issues if issue["severity"] == "error"]) == 2


def test_manifest_counts_and_warnings(tmp_path):
    seed_geological_model_workspace(tmp_path, "demo", overwrite=True)
    manifest = build_geological_model_manifest(tmp_path, "demo")
    assert manifest.model_count == 1
    assert manifest.grid_count == 1
    assert manifest.zone_count == 1
    assert manifest.warnings == ()


def test_markdown_report_contains_main_sections(tmp_path):
    seed_geological_model_workspace(tmp_path, "demo", overwrite=True)
    report = render_geological_model_markdown(tmp_path, "demo")
    assert "Geological Model Workspace Report" in report
    assert "## Grids" in report
    assert "Reservoir Zone" in report


def test_rejects_invalid_grid_type(tmp_path):
    try:
        save_grid(tmp_path, "demo", {"grid_id": "g1", "name": "Grid", "grid_type": "bad"})
    except ValueError as exc:
        assert "Тип грида" in str(exc)
    else:
        raise AssertionError("Expected invalid grid type error")
