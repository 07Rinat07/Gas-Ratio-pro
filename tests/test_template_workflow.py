from projects.template_workflow import (
    build_workflow_issue_table,
    build_workflow_run_table,
    build_workflow_step_table,
    build_workflow_template_table,
    builtin_workflow_templates,
    clone_workflow_template,
    create_workflow_template,
    default_las_cleanup_steps,
    export_workflow_template,
    import_workflow_template,
    list_workflow_runs,
    list_workflow_templates,
    set_workflow_favorite,
    simulate_workflow_execution,
    start_workflow_run,
    summarize_workflows,
    update_workflow_run,
    validate_workflow_template,
    workflow_to_batch_operations,
)


def test_workflow_template_lifecycle_and_tables(tmp_path):
    root = tmp_path / "projects"
    template = create_workflow_template(
        root,
        "demo",
        "Depth Cleanup",
        category="depth",
        steps=[
            {"type": "validate_las", "name": "QC", "order": 10},
            {"type": "resample", "name": "Resample", "parameters": {"step": 0.1}, "order": 20},
            {"type": "export_las", "parameters": {"output_dir": str(tmp_path / "out")}, "order": 30},
        ],
        favorite=True,
    )

    templates = list_workflow_templates(root, "demo", include_builtin=False)
    assert templates[0].name == "Depth Cleanup"
    assert templates[0].category == "depth"
    assert build_workflow_template_table(templates)[0]["Шагов"] == 3
    assert build_workflow_step_table(template.steps)[0]["Тип"] == "validate_las"

    summary = summarize_workflows(templates)
    assert summary.templates == 1
    assert summary.favorites == 1


def test_workflow_validation_export_import_and_batch_mapping(tmp_path):
    root = tmp_path / "projects"
    template = create_workflow_template(
        root,
        "demo",
        "Bad Resample",
        steps=[{"type": "resample", "parameters": {"step": 0}}, {"type": "calculate_vsh"}],
    )

    issues = validate_workflow_template(template)
    codes = {issue.code for issue in issues}
    assert "INVALID_RESAMPLE_STEP" in codes
    assert "MISSING_PRE_VALIDATION" in codes
    assert build_workflow_issue_table(issues)

    exported = export_workflow_template(template)
    imported = import_workflow_template(root, "demo", exported)
    assert imported.name == template.name
    assert workflow_to_batch_operations(template)[0]["type"] == "resample"


def test_workflow_run_controls_and_builtin_clone(tmp_path):
    root = tmp_path / "projects"
    builtin = builtin_workflow_templates()[0]
    clone = clone_workflow_template(root, "demo", builtin.id, new_name="Custom cleanup")
    favorite = set_workflow_favorite(root, "demo", clone.id, False)
    assert favorite.favorite is False

    run = start_workflow_run(root, "demo", clone.id)
    assert run.status == "queued"
    updated = update_workflow_run(root, "demo", run.id, "running", completed_steps=1)
    assert updated.progress > 0

    final = simulate_workflow_execution(root, "demo", clone.id)
    assert final.status == "done"
    runs = list_workflow_runs(root, "demo", template_id=clone.id)
    assert build_workflow_run_table(runs)[0]["Статус"] in {"done", "running"}


def test_default_templates_are_available_without_project_file(tmp_path):
    templates = list_workflow_templates(tmp_path / "projects", "demo")
    names = {template.name for template in templates}
    assert "Standard LAS Cleanup" in names
    assert "Complete Petrophysical Interpretation" in names
    assert len(default_las_cleanup_steps()) >= 3
