from projects.geological_model_integration_workspace import (
    save_integrated_model_object,
    save_model_dependency,
    seed_geological_model_integration_workspace,
)
from projects.model_validation_audit_workspace import (
    build_model_audit_check_table,
    build_model_audit_coverage_table,
    build_model_audit_issue_table,
    build_model_validation_audit_manifest,
    render_model_validation_audit_markdown,
    run_model_validation_audit,
    save_model_validation_audit,
)


def test_audit_seeded_integration_model_has_no_errors(tmp_path):
    seed_geological_model_integration_workspace("demo", tmp_path)

    manifest = build_model_validation_audit_manifest("demo", tmp_path)

    assert manifest.error_count == 0
    assert manifest.object_count == 6
    assert manifest.readiness_score > 0
    assert manifest.type_coverage["geological_model"] is True


def test_audit_detects_missing_required_components(tmp_path):
    save_integrated_model_object({"object_id": "gm", "object_type": "geological_model", "name": "Model", "source_module": "manual"}, "demo", tmp_path)

    issues = run_model_validation_audit("demo", tmp_path)

    assert any(issue.code == "MISSING_REQUIRED_COMPONENT" and issue.object_type == "structural_model" for issue in issues)
    assert build_model_validation_audit_manifest("demo", tmp_path).error_count > 0


def test_audit_detects_broken_dependency(tmp_path):
    save_integrated_model_object({"object_id": "gm", "object_type": "geological_model", "name": "Model", "source_module": "manual"}, "demo", tmp_path)
    save_model_dependency({"dependency_id": "broken", "from_object_id": "missing", "to_object_id": "gm", "role": "input"}, "demo", tmp_path)

    issues = run_model_validation_audit("demo", tmp_path)

    assert any(issue.code == "INTEGRATION_MISSING_FROM_OBJECT" for issue in issues)
    assert build_model_validation_audit_manifest("demo", tmp_path).broken_dependency_count == 1


def test_audit_metadata_warnings_are_reported(tmp_path):
    save_integrated_model_object({"object_id": "gm", "object_type": "geological_model", "name": "Model"}, "demo", tmp_path)

    issues = run_model_validation_audit("demo", tmp_path)

    assert any(issue.code == "MISSING_SOURCE_MODULE" and issue.object_id == "gm" for issue in issues)
    assert any(issue.code == "DRAFT_OBJECT" and issue.object_id == "gm" for issue in issues)


def test_audit_tables_markdown_and_saved_record(tmp_path):
    seed_geological_model_integration_workspace("demo", tmp_path)

    checks = build_model_audit_check_table("demo", tmp_path)
    coverage = build_model_audit_coverage_table("demo", tmp_path)
    issues = build_model_audit_issue_table("demo", tmp_path)
    record = save_model_validation_audit("demo", tmp_path)
    report = render_model_validation_audit_markdown("demo", tmp_path)

    assert checks
    assert coverage
    assert isinstance(issues, list)
    assert record["manifest"]["project_id"] == "demo"
    assert "Model Validation & Audit Workspace" in report
    assert "Readiness" in report
