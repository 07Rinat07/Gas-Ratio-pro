from __future__ import annotations

from pathlib import Path

from core.platform_health import (
    REQUIRED_SERVICE_CONTRACTS,
    check_service_contracts,
    check_ui_storage_boundaries,
    find_destructive_ui_calls,
    run_platform_health,
)


def test_service_contracts_are_stable() -> None:
    result = check_service_contracts(REQUIRED_SERVICE_CONTRACTS)
    assert result.status == "ok", result.message


def test_streamlit_app_has_no_direct_destructive_storage_calls() -> None:
    root = Path(__file__).resolve().parents[1]
    result = check_ui_storage_boundaries(root)
    assert result.status == "ok", result.message


def test_direct_destructive_call_detector_catches_path_unlink(tmp_path: Path) -> None:
    sample = tmp_path / "sample.py"
    sample.write_text("from pathlib import Path\nPath('x').unlink()\n", encoding="utf-8")
    findings = find_destructive_ui_calls(sample)
    assert findings == ((2, "*.unlink"),)


def test_platform_health_report_is_serializable() -> None:
    root = Path(__file__).resolve().parents[1]
    report = run_platform_health(root)
    payload = report.as_dict()
    assert "ok" in payload
    assert isinstance(payload["checks"], list)
