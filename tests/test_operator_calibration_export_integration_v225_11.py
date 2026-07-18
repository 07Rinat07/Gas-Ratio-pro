from __future__ import annotations

from pathlib import Path

from reports.export_controller import ExportArtifact, ExportRequest
from services.operator_calibration_package_application_service import OperatorCalibrationPackageApplicationService
from services.presentation_export_runtime_application_service import PresentationExportRuntimeApplicationService
from tests.operator_calibration_package_helpers import build_operator_package_bytes

ROOT = Path(__file__).resolve().parents[1]


def request() -> ExportRequest:
    return ExportRequest(
        project_id="project-a",
        project_name="Project A",
        source_label="source",
        profile_id="engineering",
        format_id="pdf",
        format_label="PDF",
        extension="pdf",
        mime_type="application/pdf",
        depth_top=1000.0,
        depth_bottom=1010.0,
        source_signature="operator-source-signature",
        calculation_revision=1,
        presentation_revision=1,
        figure_height=1000,
        petrophysical_method_ids=("petrophysics.sw_archie",),
        require_final_report_authorization=True,
    )


def renderer(_model, _frame, req: ExportRequest) -> ExportArtifact:
    return ExportArtifact(
        content=b"%PDF-1.4\n%%EOF",
        file_name="report.pdf",
        mime_type=req.mime_type,
        format_id=req.format_id,
        format_label=req.format_label,
        profile_id=req.profile_id,
    )


def test_export_uses_active_project_authorization_package(tmp_path: Path) -> None:
    projects_root = tmp_path / "projects"
    operator = OperatorCalibrationPackageApplicationService(
        projects_root=projects_root,
        application_root=ROOT,
        project_id="project-a",
    )
    imported = operator.import_package(build_operator_package_bytes(ROOT, project_id="project-a"))
    operator.activate_package(imported.package_fingerprint)
    runtime = PresentationExportRuntimeApplicationService(
        root=projects_root,
        application_root=ROOT,
        project_id="project-a",
        operator_calibration_service=operator,
    )
    artifact, metrics = runtime.prepare(
        request(),
        frame=object(),
        build_model=lambda frame, req: object(),
        render_artifact=renderer,
    )
    assert metrics["petrophysical_authorized"] is True
    assert artifact.authorization_id.startswith("authp-")
    assert artifact.authorization_package_id.startswith("papa-")
    assert artifact.operator_calibration_fingerprint == imported.package_fingerprint
    assert len(artifact.authorization_gate_ids) == 5


def test_export_cache_is_invalidated_when_active_operator_package_changes(tmp_path: Path) -> None:
    projects_root = tmp_path / "projects"
    operator = OperatorCalibrationPackageApplicationService(
        projects_root=projects_root,
        application_root=ROOT,
        project_id="project-a",
    )
    first = operator.import_package(
        build_operator_package_bytes(ROOT, project_id="project-a", version="1.0.0")
    )
    second = operator.import_package(
        build_operator_package_bytes(ROOT, project_id="project-a", version="1.1.0", observed_shift=0.001)
    )
    runtime = PresentationExportRuntimeApplicationService(
        root=projects_root,
        application_root=ROOT,
        project_id="project-a",
        operator_calibration_service=operator,
    )
    calls = {"build": 0, "render": 0}

    def build(frame, req):
        calls["build"] += 1
        return object()

    def render(model, frame, req):
        calls["render"] += 1
        return renderer(model, frame, req)

    operator.activate_package(first.package_fingerprint)
    artifact_one, _ = runtime.prepare(request(), frame=object(), build_model=build, render_artifact=render)
    operator.activate_package(second.package_fingerprint)
    artifact_two, _ = runtime.prepare(request(), frame=object(), build_model=build, render_artifact=render)
    assert calls == {"build": 2, "render": 2}
    assert artifact_one.operator_calibration_fingerprint == first.package_fingerprint
    assert artifact_two.operator_calibration_fingerprint == second.package_fingerprint
