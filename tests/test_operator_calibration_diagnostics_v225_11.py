from __future__ import annotations

from pathlib import Path

from services.operator_calibration_diagnostics import build_operator_calibration_diagnostics_view
from services.operator_calibration_package_application_service import OperatorCalibrationPackageApplicationService
from tests.operator_calibration_package_helpers import build_operator_package_bytes

ROOT = Path(__file__).resolve().parents[1]


def test_operator_calibration_diagnostics_are_localized(tmp_path: Path) -> None:
    service = OperatorCalibrationPackageApplicationService(
        projects_root=tmp_path / "projects",
        application_root=ROOT,
        project_id="project-a",
    )
    imported = service.import_package(build_operator_package_bytes(ROOT, project_id="project-a"))
    service.activate_package(imported.package_fingerprint)
    packages = service.list_packages()
    for locale, title in (
        ("ru", "Операторские"),
        ("kk", "Операторлық"),
        ("en", "Operator"),
    ):
        view = build_operator_calibration_diagnostics_view(packages, locale=locale)
        assert title in view.title
        assert len(view.rows) == 1
        assert view.rows[0].active_status
        assert view.labels["fingerprint"]
        assert view.disclaimer
