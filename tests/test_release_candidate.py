from __future__ import annotations

from pathlib import Path

from projects.release_candidate import (
    RELEASE_SCHEMA,
    build_release_check_table,
    build_release_file_inventory,
    build_release_manifest,
    check_python_compile,
    check_required_files,
    load_release_manifest,
    run_release_candidate_audit,
    save_release_manifest,
    summarize_release_checks,
    validate_release_manifest,
)
from projects.repository import create_project


def _create_minimal_app(root: Path) -> None:
    for relative in (
        "README.md",
        "CHANGELOG.md",
        "requirements.txt",
        "app/streamlit_app.py",
        "docs/project_plan.md",
        "docs/setup.md",
        "docs/user_guide.md",
        "docs/troubleshooting.md",
        "tests/test_sample.py",
        "projects/sample.py",
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if relative.endswith(".py"):
            path.write_text("VALUE = 1\n", encoding="utf-8")
        elif relative == "CHANGELOG.md":
            path.write_text("# Changelog\n\n" + "Release notes.\n" * 30, encoding="utf-8")
        else:
            path.write_text(f"# {relative}\n", encoding="utf-8")


def test_required_files_and_compile_checks(tmp_path):
    _create_minimal_app(tmp_path)

    checks = check_required_files(tmp_path)
    assert all(check.status == "ok" for check in checks)

    compile_check = check_python_compile(tmp_path, compile_dirs=("projects", "app"))
    assert compile_check.status == "ok"
    assert compile_check.details["files_checked"] == 2


def test_audit_manifest_and_validation(tmp_path):
    _create_minimal_app(tmp_path)

    checks = run_release_candidate_audit(tmp_path)
    summary = summarize_release_checks(checks)
    assert summary.required_errors == 0
    assert summary.release_ready is True

    manifest = build_release_manifest(tmp_path, version="RC-136", checks=checks)
    assert manifest["schema"] == RELEASE_SCHEMA
    assert manifest["status"] == "release-ready"
    assert manifest["summary"]["checks"] == len(checks)
    assert manifest["file_inventory"]["files"] >= 9

    validation = validate_release_manifest(manifest)
    assert all(check.status == "ok" for check in validation)


def test_manifest_detects_missing_required_file(tmp_path):
    _create_minimal_app(tmp_path)
    (tmp_path / "README.md").unlink()

    manifest = build_release_manifest(tmp_path, version="RC-blocked", include_file_inventory=False)
    assert manifest["status"] == "blocked"
    assert manifest["summary"]["required_errors"] >= 1

    table = build_release_check_table(manifest["checks"])
    assert any(row["Статус"] == "error" for row in table)


def test_save_and_load_release_manifest(tmp_path):
    _create_minimal_app(tmp_path)
    project = create_project(tmp_path, "Release Project")
    manifest = build_release_manifest(tmp_path, version="RC-save", include_file_inventory=False)

    saved = save_release_manifest(tmp_path, project.id, manifest)
    loaded = load_release_manifest(tmp_path, project.id)

    assert saved["version"] == "RC-save"
    assert loaded["schema"] == RELEASE_SCHEMA
    assert loaded["version"] == "RC-save"


def test_file_inventory_is_deterministic(tmp_path):
    _create_minimal_app(tmp_path)

    first = build_release_file_inventory(tmp_path)
    second = build_release_file_inventory(tmp_path)

    assert first["fingerprint"] == second["fingerprint"]
    assert first["total_size_bytes"] == second["total_size_bytes"]
