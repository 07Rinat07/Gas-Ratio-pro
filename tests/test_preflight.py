from __future__ import annotations

import json
import shutil
from pathlib import Path

from core.preflight import run_preflight


def _copy_required_fixture_tree(tmp_path: Path) -> Path:
    source_root = Path(__file__).resolve().parents[1]
    root = tmp_path / "project"
    root.mkdir()

    for relative in (
        "app/streamlit_app.py",
        "config/palettes.json",
        "docs/project_plan.md",
        "docs/setup.md",
        "docs/user_guide.md",
        "docs/data_format.md",
        "docs/formulas.md",
        "docs/las_editor_plan.md",
        "docs/las_correlation_plan.md",
        "docs/mud_gas_analysis_literature.md",
        "docs/logging.md",
        "docs/palettes.md",
        "docs/troubleshooting.md",
        "examples/sample_gas_data.csv",
        "examples/sample_gas_data.las",
        "requirements.txt",
        "scripts/preflight.py",
    ):
        source = source_root / relative
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)

    return root


def test_preflight_passes_for_rule_based_fixture(tmp_path):
    root = _copy_required_fixture_tree(tmp_path)

    report = run_preflight(root)

    assert report.ok
    assert {check.name for check in report.checks} == {
        "python",
        "project_files",
        "dependencies",
        "static_export",
        "palette_config",
        "logs",
    }


def test_preflight_reports_missing_required_project_file(tmp_path):
    root = _copy_required_fixture_tree(tmp_path)
    (root / "docs" / "project_plan.md").unlink()

    report = run_preflight(root)
    files_check = next(check for check in report.checks if check.name == "project_files")

    assert not report.ok
    assert files_check.status == "error"
    assert "docs/project_plan.md" in files_check.message


def test_preflight_reports_invalid_palette_config(tmp_path):
    root = _copy_required_fixture_tree(tmp_path)
    (root / "config" / "palettes.json").write_text(
        json.dumps({"version": "bad", "pixler_zones": []}),
        encoding="utf-8",
    )

    report = run_preflight(root)
    palette_check = next(check for check in report.checks if check.name == "palette_config")

    assert not report.ok
    assert palette_check.status == "error"
    assert "palettes.json" in palette_check.message
