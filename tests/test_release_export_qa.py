from __future__ import annotations

import json
import subprocess
import sys

from reports.presentation_export import validate_presentation_bundle_export
from scripts.release_export_qa import run_release_export_qa


def test_validate_presentation_bundle_export_confirms_smoke_bundle(tmp_path) -> None:
    summary = run_release_export_qa(tmp_path)

    assert summary["ok"] is True
    validation = summary["validation"]
    assert validation["ok"] is True
    assert validation["issue_count"] == 0
    assert len(validation["files_checked"]) == 6
    assert validation["missing_files"] == []
    assert validation["empty_files"] == []
    assert validation["consistency"]["single_source_model"] is True


def test_validate_presentation_bundle_export_reports_missing_artifact(tmp_path) -> None:
    summary = run_release_export_qa(tmp_path)
    manifest_path = summary["smoke"]["manifest"]
    payload = json.loads(__import__("pathlib").Path(manifest_path).read_text(encoding="utf-8"))
    missing_pdf = __import__("pathlib").Path(manifest_path).parent / payload["files"]["pdf"]
    missing_pdf.unlink()

    validation = validate_presentation_bundle_export(manifest_path)

    assert validation.ok is False
    assert payload["files"]["pdf"] in validation.missing_files
    assert validation.issue_count == 1


def test_release_export_qa_script_prints_json(tmp_path) -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/release_export_qa.py", "--output-dir", str(tmp_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["ok"] is True
    assert payload["validation"]["ok"] is True


def test_release_export_qa_writes_machine_readable_validation_report(tmp_path) -> None:
    summary = run_release_export_qa(tmp_path)
    report_path = __import__("pathlib").Path(summary["validation"]["validation_report"])

    assert report_path.exists()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["schema"] == "gas-ratio-pro/presentation/bundle-validation/v1"
    assert report["ok"] is True
    assert report["status"] == "ok"
    assert report["issue_count"] == 0
    assert report["manifest"] == summary["validation"]["manifest"]
    assert report["file_count"] == len(report["files_checked"])
    assert all(item["exists"] is True for item in report["files_checked"])
    assert all(item["size_bytes"] > 0 for item in report["files_checked"])
