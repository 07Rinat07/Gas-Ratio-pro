from pathlib import Path

from core.integration_audit import audit_streamlit_app
from services.well_manager_service import DEFAULT_WELLS_STORAGE_ROOT


def test_streamlit_shell_uses_service_layer_for_well_storage_root() -> None:
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")

    assert "from wells.repository import DEFAULT_WELLS_ROOT" not in source
    assert "DEFAULT_WELLS_STORAGE_ROOT" in source
    assert str(DEFAULT_WELLS_STORAGE_ROOT).replace("\\", "/") == "data/wells"


def test_streamlit_shell_has_no_direct_repository_import_warnings() -> None:
    report = audit_streamlit_app(Path("."))

    direct_repository_findings = tuple(
        finding for finding in report.findings if finding.detail.startswith("direct repository import")
    )
    assert direct_repository_findings == ()
