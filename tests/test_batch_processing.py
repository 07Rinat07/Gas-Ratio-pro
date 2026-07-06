from pathlib import Path

from projects.batch_processing import (
    BatchOperation,
    add_batch_task,
    add_batch_tasks_from_paths,
    append_batch_run_log,
    build_batch_operation_table,
    build_batch_task_table,
    default_petrophysics_batch_operations,
    discover_las_files,
    list_batch_run_logs,
    list_batch_tasks,
    next_runnable_batch_task,
    pause_batch_queue,
    plan_batch_exports,
    reorder_batch_tasks,
    resume_batch_queue,
    retry_failed_batch_tasks,
    save_batch_preset,
    summarize_batch_queue,
    update_batch_task_status,
    validate_batch_queue,
)


def test_batch_queue_lifecycle(tmp_path):
    root = tmp_path / "projects"
    task = add_batch_task(
        root,
        "demo",
        tmp_path / "well-01.las",
        operations=[{"type": "validate_las"}, {"type": "resample", "parameters": {"step": 0.1}}],
    )

    assert task.status == "queued"
    assert len(task.operations) == 2
    updated = update_batch_task_status(root, "demo", task.id, "running", progress=35)
    assert updated.progress == 35
    done = update_batch_task_status(root, "demo", task.id, "done")
    assert done.progress == 100

    tasks = list_batch_tasks(root, "demo")
    summary = summarize_batch_queue(tasks)
    assert summary.tasks == 1
    assert summary.done == 1
    assert summary.progress == 100
    assert build_batch_task_table(tasks)[0]["Статус"] == "done"


def test_batch_discovery_presets_validation_and_exports(tmp_path):
    las_a = tmp_path / "a.las"
    las_b = tmp_path / "folder" / "b.LAS"
    las_b.parent.mkdir()
    las_a.write_text("~Version", encoding="utf-8")
    las_b.write_text("~Version", encoding="utf-8")

    discovered = discover_las_files([tmp_path])
    assert str(las_a) in discovered
    assert str(las_b) in discovered

    root = tmp_path / "projects"
    operations = default_petrophysics_batch_operations()
    preset = save_batch_preset(root, "demo", "Full interpretation", operations)
    assert preset.name == "Full interpretation"
    assert build_batch_operation_table(preset.operations)

    tasks = add_batch_tasks_from_paths(root, "demo", discovered, operations=[BatchOperation("resample", {"step": 0.0})])
    issues = validate_batch_queue(tasks)
    assert any(issue.code == "INVALID_RESAMPLE_STEP" for issue in issues)
    exports = plan_batch_exports(tasks[0], ["las", "json"], output_dir=tmp_path / "out")
    assert exports[0].endswith("_batch.las")
    assert exports[1].endswith("_batch.json")


def test_batch_controls_logs_retry_and_order(tmp_path):
    root = tmp_path / "projects"
    first = add_batch_task(root, "demo", tmp_path / "first.las", name="first", priority=20)
    second = add_batch_task(root, "demo", tmp_path / "second.las", name="second", priority=10)

    assert next_runnable_batch_task(list_batch_tasks(root, "demo")).id == second.id
    reordered = reorder_batch_tasks(root, "demo", [first.id, second.id])
    assert reordered[0].id == first.id

    paused = pause_batch_queue(root, "demo")
    assert {task.status for task in paused} == {"paused"}
    resumed = resume_batch_queue(root, "demo")
    assert {task.status for task in resumed} == {"queued"}

    failed = update_batch_task_status(root, "demo", first.id, "failed", error="bad curve")
    assert failed.status == "failed"
    retried = retry_failed_batch_tasks(root, "demo")
    assert retried[0].status == "queued"

    log = append_batch_run_log(root, "demo", first.id, "validate_las", "done", message="ok", duration_seconds=0.25)
    assert log.operation_type == "validate_las"
    assert list_batch_run_logs(root, "demo", task_id=first.id)[0].message == "ok"
