from __future__ import annotations

from pathlib import Path

from core.application_service_container import application_service_container
from reports.export_history import EXPORT_HISTORY_SCHEMA, ExportHistoryEntry, ExportHistoryRepository
from services.calibration_package_trust_diagnostics import build_calibration_trust_diagnostics_view
from services.operator_calibration_package_application_service import OperatorCalibrationPackageApplicationService
from tests.calibration_package_trust_helpers import approve_and_promote_to_production, build_trust_fixture

ROOT = Path(__file__).resolve().parents[1]


def test_application_container_injects_strict_project_trust_boundary(tmp_path: Path) -> None:
    container = application_service_container({})
    trust = container.calibration_package_trust(
        projects_root=tmp_path / "projects",
        application_root=ROOT,
        project_id="project-a",
    )
    operator = container.operator_calibration_packages(
        projects_root=tmp_path / "projects",
        application_root=ROOT,
        project_id="project-a",
    )
    assert isinstance(operator, OperatorCalibrationPackageApplicationService)
    assert operator.require_production_trust is True
    assert operator.trust_service is trust


def test_trust_diagnostics_are_localized_and_show_production_readiness(tmp_path: Path) -> None:
    fixture = build_trust_fixture(tmp_path, ROOT)
    approve_and_promote_to_production(fixture)
    package = fixture["package"]
    packages = (fixture["operator"].get_package(package.package_fingerprint),)
    for locale, expected in (("ru", "production-ready"), ("kk", "production-ready"), ("en", "production-ready")):
        view = build_calibration_trust_diagnostics_view(
            packages,
            trust_service=fixture["trust"],
            locale=locale,
        )
        assert expected in view.summary
        assert view.rows[0].environment == "production"
        assert view.rows[0].trust_status
        assert view.disclaimer


def test_export_history_v6_preserves_trust_evidence(tmp_path: Path) -> None:
    store = ExportHistoryRepository(tmp_path / "history")
    entry = ExportHistoryEntry(
        project_id="project-a",
        file_name="report.pdf",
        format_id="pdf",
        format_label="PDF",
        profile_id="a3_landscape",
        depth_top=1000.0,
        depth_bottom=1200.0,
        size_bytes=1234,
        authorization_id="authp-1",
        authorization_package_id="papa-1",
        operator_calibration_fingerprint="a" * 64,
        trust_decision_id="trust-1",
        trust_registry_fingerprint="b" * 64,
        trust_signature_fingerprint="c" * 64,
        trust_promotion_id="prom-1",
        petrophysical_method_ids=("petrophysics.sw_archie",),
    )
    path = store.record(entry)
    assert EXPORT_HISTORY_SCHEMA.endswith("/v6")
    loaded = store.load("project-a")
    assert loaded[0].trust_decision_id == "trust-1"
    assert loaded[0].trust_registry_fingerprint == "b" * 64
    assert loaded[0].trust_signature_fingerprint == "c" * 64
    assert loaded[0].trust_promotion_id == "prom-1"
    assert path.is_file()
