from __future__ import annotations

from reports.export_controller import ExportArtifact, ExportController, ExportControllerError, ExportRequest


def _request(fmt: str = "pdf") -> ExportRequest:
    return ExportRequest(
        project_id="p1",
        project_name="Project",
        source_label="LAS",
        profile_id="engineering",
        format_id=fmt,
        format_label=fmt.upper(),
        extension=fmt,
        mime_type="application/octet-stream",
        depth_top=100.0,
        depth_bottom=200.0,
        source_signature="abc",
        calculation_revision=2,
        presentation_revision=3,
        figure_height=1000,
    )


def test_export_controller_reuses_model_across_formats() -> None:
    state = {}
    controller = ExportController(state)
    calls = {"model": 0, "render": 0}

    def build_model(frame, request):
        calls["model"] += 1
        return {"profile": request.profile_id, "rows": len(frame)}

    def render(model, frame, request):
        calls["render"] += 1
        return ExportArtifact(b"ok", f"x.{request.extension}", request.mime_type, request.format_id, request.format_label, request.profile_id)

    first, first_metrics = controller.prepare(_request("pdf"), frame=[1, 2], build_model=build_model, render_artifact=render)
    second, second_metrics = controller.prepare(_request("docx"), frame=[1, 2], build_model=build_model, render_artifact=render)

    assert first.content == b"ok"
    assert second.content == b"ok"
    assert calls == {"model": 1, "render": 2}
    assert first_metrics["model_cache_hit"] is False
    assert second_metrics["model_cache_hit"] is True


def test_export_controller_reuses_same_artifact() -> None:
    state = {}
    controller = ExportController(state)
    calls = {"model": 0, "render": 0}

    def build_model(frame, request):
        calls["model"] += 1
        return object()

    def render(model, frame, request):
        calls["render"] += 1
        return ExportArtifact(b"cached", "x.pdf", request.mime_type, request.format_id, request.format_label, request.profile_id)

    controller.prepare(_request(), frame=[1], build_model=build_model, render_artifact=render)
    artifact, metrics = controller.prepare(_request(), frame=[1], build_model=build_model, render_artifact=render)

    assert artifact.cache_hit is True
    assert metrics["artifact_cache_hit"] is True
    assert calls == {"model": 1, "render": 1}


def test_export_controller_reports_failure_stage() -> None:
    controller = ExportController({})

    def build_model(frame, request):
        raise ValueError("bad model")

    def render(model, frame, request):
        raise AssertionError("must not render")

    try:
        controller.prepare(_request(), frame=[1], build_model=build_model, render_artifact=render)
    except ExportControllerError as exc:
        assert exc.failure.stage == "build_model"
        assert exc.failure.exception_type == "ValueError"
        assert exc.failure.error_id.startswith("export-")
    else:
        raise AssertionError("ExportControllerError expected")
