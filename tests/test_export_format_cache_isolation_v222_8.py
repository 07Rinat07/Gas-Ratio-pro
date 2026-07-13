from __future__ import annotations

from io import BytesIO
from zipfile import ZipFile

import pytest

from reports.export_controller import ExportArtifact, ExportController, ExportRequest


def _request(fmt: str) -> ExportRequest:
    meta = {
        "pdf": ("PDF", "pdf", "application/pdf"),
        "docx": ("DOCX", "docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    }[fmt]
    return ExportRequest(
        project_id="p", project_name="P", source_label="LAS", profile_id="engineering",
        format_id=fmt, format_label=meta[0], extension=meta[1], mime_type=meta[2],
        depth_top=1.0, depth_bottom=2.0, source_signature="sig",
        calculation_revision=1, presentation_revision=1, figure_height=800,
    )


def _docx_bytes() -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "<document/>")
    return buffer.getvalue()


def test_format_specific_renderer_receives_current_request_on_model_cache_hit() -> None:
    state: dict[str, object] = {}
    controller = ExportController(state)
    build_calls = 0

    def build_model(frame, request):
        nonlocal build_calls
        build_calls += 1
        return {"model": "shared"}

    def render(model, frame, request):
        content = b"%PDF-1.4\n%%EOF" if request.format_id == "pdf" else _docx_bytes()
        return ExportArtifact(
            content=content,
            file_name=f"report.{request.extension}",
            mime_type=request.mime_type,
            format_id=request.format_id,
            format_label=request.format_label,
            profile_id=request.profile_id,
        )

    pdf, _ = controller.prepare(_request("pdf"), frame=object(), build_model=build_model, render_artifact=render)
    docx, metrics = controller.prepare(_request("docx"), frame=object(), build_model=build_model, render_artifact=render)
    assert build_calls == 1
    assert metrics["model_cache_hit"] is True
    assert pdf.content.startswith(b"%PDF-")
    assert docx.content.startswith(b"PK\x03\x04")


def test_binary_signature_rejects_renamed_pdf_as_docx() -> None:
    request = _request("docx")
    artifact = ExportArtifact(
        content=b"%PDF-1.4\n%%EOF", file_name="report.docx", mime_type=request.mime_type,
        format_id="docx", format_label="DOCX", profile_id="engineering",
    )
    with pytest.raises(ValueError, match="другого формата"):
        ExportController._validate_artifact_contract(artifact, request)
