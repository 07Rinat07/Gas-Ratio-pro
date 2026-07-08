from pathlib import Path

from core.platform_health import run_platform_health
from core.streamlit_compatibility import scan_streamlit_deprecations


def test_no_deprecated_use_container_width_in_project() -> None:
    report = scan_streamlit_deprecations(Path(__file__).resolve().parents[1])

    assert report.ok, report.as_dict()


def test_platform_health_includes_streamlit_compatibility_check() -> None:
    report = run_platform_health(Path(__file__).resolve().parents[1])
    checks = {check.name: check for check in report.checks}

    assert "streamlit_compatibility" in checks
    assert checks["streamlit_compatibility"].status == "ok"
