from projects.geological_model_integration_workspace import (
    build_dependency_graph,
    build_dependency_table,
    build_geological_model_integration_manifest,
    build_integration_issue_table,
    build_integration_object_table,
    build_integration_view_table,
    list_integrated_model_objects,
    list_model_dependencies,
    render_geological_model_integration_markdown,
    save_integrated_model_object,
    save_integration_view,
    save_model_dependency,
    seed_geological_model_integration_workspace,
    validate_geological_model_integration_workspace,
)


def test_seed_integration_workspace_builds_main_graph(tmp_path):
    seed_geological_model_integration_workspace("demo", tmp_path)

    objects = list_integrated_model_objects("demo", tmp_path)
    deps = list_model_dependencies("demo", tmp_path)
    manifest = build_geological_model_integration_manifest("demo", tmp_path)

    assert len(objects) == 6
    assert len(deps) == 5
    assert manifest.object_type_counts["geological_model"] == 1
    assert manifest.error_count == 0


def test_dependency_graph_contains_nodes_and_edges(tmp_path):
    seed_geological_model_integration_workspace("demo", tmp_path)

    graph = build_dependency_graph("demo", tmp_path)

    assert len(graph["nodes"]) == 6
    assert any(edge["from"] == "struct-main" and edge["to"] == "gm-main" for edge in graph["edges"])


def test_validation_detects_missing_dependency_target(tmp_path):
    save_integrated_model_object({"object_id": "gm", "object_type": "geological_model", "name": "Model"}, "demo", tmp_path)
    save_model_dependency(
        {"dependency_id": "broken", "from_object_id": "gm", "to_object_id": "missing", "role": "input", "required": True},
        "demo",
        tmp_path,
    )

    issues = validate_geological_model_integration_workspace("demo", tmp_path)

    assert any(issue.code == "MISSING_TO_OBJECT" and issue.severity == "error" for issue in issues)
    assert build_geological_model_integration_manifest("demo", tmp_path).error_count == 1


def test_validation_detects_orphan_objects(tmp_path):
    save_integrated_model_object({"object_id": "gm", "object_type": "geological_model", "name": "Model"}, "demo", tmp_path)
    save_integrated_model_object({"object_id": "cube", "object_type": "property_cube", "name": "POR"}, "demo", tmp_path)

    issues = validate_geological_model_integration_workspace("demo", tmp_path)

    assert any(issue.code == "ORPHAN_OBJECT" and issue.object_id == "cube" for issue in issues)


def test_view_missing_object_is_reported(tmp_path):
    save_integrated_model_object({"object_id": "gm", "object_type": "geological_model", "name": "Model"}, "demo", tmp_path)
    save_integration_view({"view_id": "v", "name": "View", "object_ids": ["gm", "missing"]}, "demo", tmp_path)

    issues = validate_geological_model_integration_workspace("demo", tmp_path)

    assert any(issue.code == "VIEW_MISSING_OBJECT" for issue in issues)


def test_ui_tables_and_markdown_report(tmp_path):
    seed_geological_model_integration_workspace("demo", tmp_path)

    assert build_integration_object_table("demo", tmp_path)
    assert build_dependency_table("demo", tmp_path)
    assert build_integration_view_table("demo", tmp_path)
    assert isinstance(build_integration_issue_table("demo", tmp_path), list)

    report = render_geological_model_integration_markdown("demo", tmp_path)
    assert "Geological Model Integration Workspace" in report
    assert "Integrated Geological Model" in report
    assert "dep-struct-to-gm" in report


def test_filter_objects_by_type(tmp_path):
    seed_geological_model_integration_workspace("demo", tmp_path)

    props = list_integrated_model_objects("demo", tmp_path, object_type="property_cube")

    assert len(props) == 1
    assert props[0].object_id == "props-main"
