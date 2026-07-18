from __future__ import annotations

from pathlib import Path

import pytest

from reports.export_controller import ExportArtifact, ExportRequest
from services.presentation_export_runtime_application_service import PresentationExportRuntimeApplicationService

ROOT = Path(__file__).resolve().parents[1]


def request(*, methods=(), required=False) -> ExportRequest:
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
        source_signature="source-signature",
        calculation_revision=1,
        presentation_revision=1,
        figure_height=1000,
        petrophysical_method_ids=tuple(methods),
        require_final_report_authorization=required,
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


def test_export_runtime_attaches_authorization_evidence_before_final_report() -> None:
    service = PresentationExportRuntimeApplicationService(root=ROOT / "data/projects", application_root=ROOT, project_id="project-a")
    artifact, metrics = service.prepare(
        request(methods=("petrophysics.sw_archie",), required=True),
        frame=object(),
        build_model=lambda frame, req: object(),
        render_artifact=renderer,
    )
    assert artifact.authorization_id.startswith("auth-")
    assert len(artifact.authorization_gate_ids) == 2
    assert metrics["petrophysical_authorization_checked"] is True
    assert metrics["petrophysical_authorized"] is True


def test_export_runtime_blocks_report_before_model_or_renderer_for_disallowed_method() -> None:
    service = PresentationExportRuntimeApplicationService(root=ROOT / "data/projects", application_root=ROOT, project_id="project-a")
    calls = {"build": 0, "render": 0}

    def build(frame, req):
        calls["build"] += 1
        return object()

    def render(model, frame, req):
        calls["render"] += 1
        return renderer(model, frame, req)

    with pytest.raises(PermissionError):
        service.prepare(
            request(methods=("petrophysics.sw_dual_water_foundation",), required=True),
            frame=object(),
            build_model=build,
            render_artifact=render,
        )
    assert calls == {"build": 0, "render": 0}


def test_export_signature_isolated_by_authorized_method_set() -> None:
    archie = request(methods=("petrophysics.sw_archie",), required=True)
    simandoux = request(methods=("petrophysics.sw_simandoux",), required=True)
    assert archie.selection_signature != simandoux.selection_signature


def test_authorization_flag_requires_method_context() -> None:
    invalid = request(methods=(), required=True)
    with pytest.raises(ValueError, match="петрофизические методы"):
        invalid.validate()
