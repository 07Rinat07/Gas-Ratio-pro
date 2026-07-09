from __future__ import annotations

from pathlib import Path

from core import preflight


def test_preflight_reports_professional_export_backend_status(tmp_path: Path) -> None:
    report = preflight.run_preflight(tmp_path)
    checks = {check.name: check for check in report.checks}

    assert "professional_export_backends" in checks
    assert checks["professional_export_backends"].status in {"ok", "warning"}


def test_preflight_reports_pdf_unicode_font_status(tmp_path: Path) -> None:
    report = preflight.run_preflight(tmp_path)
    checks = {check.name: check for check in report.checks}

    assert "pdf_unicode_font" in checks
    assert checks["pdf_unicode_font"].status in {"ok", "warning"}


def test_pdf_font_preflight_can_use_project_local_open_font(tmp_path: Path) -> None:
    font_path = tmp_path / "assets" / "fonts" / "NotoSans-Regular.ttf"
    font_path.parent.mkdir(parents=True)
    font_path.write_bytes(b"placeholder")

    check = preflight._check_pdf_unicode_font(tmp_path)

    assert check.name == "pdf_unicode_font"
    assert check.status == "ok"
