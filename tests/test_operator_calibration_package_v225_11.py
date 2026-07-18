from __future__ import annotations

from io import BytesIO
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from core.operator_calibration_package_contract import (
    PACKAGE_MANIFEST_NAME,
    operator_package_fingerprint,
)
from services.operator_calibration_package_application_service import (
    OperatorCalibrationPackageApplicationService,
    OperatorCalibrationPackageError,
    OperatorCalibrationVersionConflict,
)
from tests.operator_calibration_package_helpers import build_operator_package_bytes

ROOT = Path(__file__).resolve().parents[1]


def service(tmp_path: Path, project_id: str = "project-a") -> OperatorCalibrationPackageApplicationService:
    return OperatorCalibrationPackageApplicationService(
        projects_root=tmp_path / "projects",
        application_root=ROOT,
        project_id=project_id,
    )


def test_operator_package_import_is_immutable_project_scoped_and_idempotent(tmp_path: Path) -> None:
    app = service(tmp_path)
    payload = build_operator_package_bytes(ROOT, project_id="project-a")
    imported = app.import_package(payload)
    assert imported.package_id == "operator-clastic-calibration"
    assert imported.project_id == "project-a"
    assert imported.final_report_use_allowed is True
    assert imported.redistribution_allowed is False
    assert len(imported.method_ids) == 10
    assert len(imported.package_fingerprint) == 64
    assert (app.project_root / imported.storage_path / "source_package.zip").exists()
    repeated = app.import_package(payload)
    assert repeated.package_fingerprint == imported.package_fingerprint
    assert len(app.list_packages()) == 1


def test_idempotent_reimport_repairs_missing_project_index(tmp_path: Path) -> None:
    app = service(tmp_path)
    payload = build_operator_package_bytes(ROOT, project_id="project-a")
    imported = app.import_package(payload)
    app.index_path.unlink()
    assert app.list_packages() == ()

    repaired = app.import_package(payload)
    assert repaired.package_fingerprint == imported.package_fingerprint
    assert len(app.list_packages()) == 1


def test_same_package_version_with_different_fingerprint_is_rejected(tmp_path: Path) -> None:
    app = service(tmp_path)
    app.import_package(build_operator_package_bytes(ROOT, project_id="project-a", observed_shift=0.0))
    changed = build_operator_package_bytes(ROOT, project_id="project-a", observed_shift=0.001)
    with pytest.raises(OperatorCalibrationVersionConflict):
        app.import_package(changed)


def test_rights_and_project_scope_are_blocking(tmp_path: Path) -> None:
    app = service(tmp_path)
    wrong_project = build_operator_package_bytes(ROOT, project_id="other-project")
    with pytest.raises(OperatorCalibrationPackageError, match="not scoped"):
        app.import_package(wrong_project)

    def remove_processing(manifest: dict) -> None:
        manifest["rights"]["processing_allowed"] = False
        manifest["package_fingerprint"] = operator_package_fingerprint(manifest)

    blocked = build_operator_package_bytes(ROOT, project_id="project-a", manifest_mutator=remove_processing)
    with pytest.raises(OperatorCalibrationPackageError, match="processing_allowed"):
        app.import_package(blocked)


def test_checksum_tampering_is_rejected_before_calibration(tmp_path: Path) -> None:
    app = service(tmp_path)
    payload = build_operator_package_bytes(ROOT, project_id="project-a")
    source = BytesIO(payload)
    output = BytesIO()
    with ZipFile(source, "r") as original, ZipFile(output, "w", compression=ZIP_DEFLATED) as changed:
        for info in original.infolist():
            data = original.read(info.filename)
            if info.filename == "calibration_dataset.json":
                data += b" "
            changed.writestr(info.filename, data)
    with pytest.raises(OperatorCalibrationPackageError, match="checksum mismatch"):
        app.import_package(output.getvalue())


def test_malformed_declared_size_is_reported_as_package_error(tmp_path: Path) -> None:
    app = service(tmp_path)

    def corrupt_size(manifest: dict) -> None:
        manifest["files"]["calibration_dataset.json"]["size_bytes"] = "not-an-integer"
        manifest["package_fingerprint"] = operator_package_fingerprint(manifest)

    payload = build_operator_package_bytes(
        ROOT,
        project_id="project-a",
        manifest_mutator=corrupt_size,
    )
    with pytest.raises(OperatorCalibrationPackageError, match="invalid declared size"):
        app.import_package(payload)


def test_activation_comparison_and_versioned_authorization_package(tmp_path: Path) -> None:
    app = service(tmp_path)
    first = app.import_package(build_operator_package_bytes(ROOT, project_id="project-a", version="1.0.0"))
    app.activate_package(first.package_fingerprint)
    assert app.active_package() is not None
    assert app.active_package().active
    comparison = app.compare(first.package_fingerprint)
    assert comparison.passed
    assert comparison.comparison_id.startswith("cmp-")
    assert len(comparison.methods) == 10
    assert {item.status for item in comparison.methods} <= {"equivalent", "improved", "degraded"}

    authorization = app.issue_authorization_package(
        ("petrophysics.sw_archie", "petrophysics.net_pay_cutoff_flags")
    )
    assert authorization.passed
    assert authorization.authorization_id.startswith("authp-")
    assert authorization.authorization_package_id.startswith("papa-")
    assert authorization.operator_package_fingerprint == first.package_fingerprint
    assert len(authorization.authorization_gate_ids) == 5
    authorization.assert_authorized()
    path = app.authorizations_root / first.package_id / first.version / f"{authorization.authorization_package_id}.json"
    stored = json.loads(path.read_text(encoding="utf-8"))
    assert stored["project_id"] == "project-a"
    assert stored["operator_package_fingerprint"] == first.package_fingerprint


def test_operator_rights_can_allow_diagnostics_but_block_final_report(tmp_path: Path) -> None:
    app = service(tmp_path)
    imported = app.import_package(
        build_operator_package_bytes(
            ROOT,
            project_id="project-a",
            final_report_use_allowed=False,
        )
    )
    app.activate_package(imported.package_fingerprint)
    diagnostics = app.issue_authorization_package(("petrophysics.sw_archie",), final_report=False)
    assert diagnostics.passed
    final = app.issue_authorization_package(("petrophysics.sw_archie",), final_report=True)
    assert not final.passed
    assert final.methods[0].reasons == ("operator_data_rights_block_final_report",)
    with pytest.raises(PermissionError):
        final.assert_authorized()


def test_stored_package_tampering_is_detected_before_use(tmp_path: Path) -> None:
    app = service(tmp_path)
    imported = app.import_package(build_operator_package_bytes(ROOT, project_id="project-a"))
    dataset_path = app.project_root / imported.storage_path / "calibration_dataset.json"
    dataset_path.write_bytes(dataset_path.read_bytes() + b" ")
    with pytest.raises(OperatorCalibrationPackageError, match="content was modified"):
        app.get_package(imported.package_fingerprint)
