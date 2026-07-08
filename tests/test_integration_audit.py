from __future__ import annotations

from pathlib import Path

from core.integration_audit import (
    audit_service_files,
    audit_streamlit_app,
    run_integration_audit,
    scan_destructive_filesystem_calls,
)


def test_destructive_filesystem_scanner_detects_delete_calls(tmp_path: Path) -> None:
    source = tmp_path / "sample.py"
    source.write_text(
        "from pathlib import Path\n"
        "import shutil\n"
        "shutil.rmtree('x')\n"
        "Path('x').unlink()\n",
        encoding="utf-8",
    )

    findings = scan_destructive_filesystem_calls(source, tmp_path)

    assert len(findings) == 2
    assert all(finding.kind == "error" for finding in findings)


def test_streamlit_app_has_no_direct_destructive_filesystem_calls() -> None:
    report = audit_streamlit_app(Path.cwd())

    assert not report.errors


def test_service_files_have_no_direct_destructive_filesystem_calls() -> None:
    report = audit_service_files(Path.cwd())

    assert not report.errors


def test_integration_audit_report_is_serializable() -> None:
    report = run_integration_audit(Path.cwd())
    payload = report.as_dict()

    assert "ok" in payload
    assert "findings" in payload
