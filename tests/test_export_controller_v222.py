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


def test_export_controller_validates_request_before_build() -> None:
    controller = ExportController({})
    request = _request()
    invalid = ExportRequest(**{**request.__dict__, "source_signature": ""}) if hasattr(request, "__dict__") else ExportRequest(
        project_id=request.project_id,
        project_name=request.project_name,
        source_label=request.source_label,
        profile_id=request.profile_id,
        format_id=request.format_id,
        format_label=request.format_label,
        extension=request.extension,
        mime_type=request.mime_type,
        depth_top=request.depth_top,
        depth_bottom=request.depth_bottom,
        source_signature="",
        calculation_revision=request.calculation_revision,
        presentation_revision=request.presentation_revision,
        figure_height=request.figure_height,
    )
    called = False

    def build_model(frame, export_request):
        nonlocal called
        called = True
        return object()

    try:
        controller.prepare(invalid, frame=[1], build_model=build_model, render_artifact=lambda *_: None)
    except ExportControllerError as exc:
        assert exc.failure.stage == "validate_request"
        assert called is False
    else:
        raise AssertionError("ExportControllerError expected")


def test_export_controller_rejects_empty_artifact() -> None:
    controller = ExportController({})

    def render(model, frame, request):
        return ExportArtifact(b"", "x.pdf", request.mime_type, request.format_id, request.format_label, request.profile_id)

    try:
        controller.prepare(_request(), frame=[1], build_model=lambda *_: object(), render_artifact=render)
    except ExportControllerError as exc:
        assert exc.failure.stage == "render_pdf"
    else:
        raise AssertionError("ExportControllerError expected")


def test_export_controller_uses_bounded_lru_caches() -> None:
    state = {}
    controller = ExportController(state)

    def render(model, frame, request):
        return ExportArtifact(b"ok", f"x.{request.extension}", request.mime_type, request.format_id, request.format_label, request.profile_id)

    for index in range(ExportController.ARTIFACT_CACHE_LIMIT + 5):
        base = _request(f"fmt{index}")
        controller.prepare(base, frame=[1], build_model=lambda *_: object(), render_artifact=render)

    model_size, artifact_size = controller.cache_sizes()
    assert model_size <= ExportController.MODEL_CACHE_LIMIT
    assert artifact_size == ExportController.ARTIFACT_CACHE_LIMIT


def test_export_controller_clears_only_requested_project() -> None:
    state = {}
    controller = ExportController(state)

    def render(model, frame, request):
        return ExportArtifact(b"ok", f"x.{request.extension}", request.mime_type, request.format_id, request.format_label, request.profile_id)

    p1 = _request("pdf")
    p2 = ExportRequest(
        project_id="p2", project_name=p1.project_name, source_label=p1.source_label,
        profile_id=p1.profile_id, format_id="docx", format_label="DOCX", extension="docx",
        mime_type=p1.mime_type, depth_top=p1.depth_top, depth_bottom=p1.depth_bottom,
        source_signature="def", calculation_revision=2, presentation_revision=3, figure_height=1000,
    )
    controller.prepare(p1, frame=[1], build_model=lambda *_: object(), render_artifact=render)
    controller.prepare(p2, frame=[1], build_model=lambda *_: object(), render_artifact=render)
    controller.clear_project_cache("p1")
    registry = state["presentation_export_cache_registry_v222"]
    assert "p1" not in registry.values()
    assert "p2" in registry.values()


def test_export_controller_bounds_artifact_cache_by_bytes(monkeypatch) -> None:
    state = {}
    controller = ExportController(state)
    monkeypatch.setattr(ExportController, "ARTIFACT_CACHE_MAX_BYTES", 10)

    def render(model, frame, request):
        return ExportArtifact(
            b"12345678",
            f"x.{request.extension}",
            request.mime_type,
            request.format_id,
            request.format_label,
            request.profile_id,
        )

    controller.prepare(_request("fmt1"), frame=[1], build_model=lambda *_: object(), render_artifact=render)
    controller.prepare(_request("fmt2"), frame=[1], build_model=lambda *_: object(), render_artifact=render)

    metrics = controller.cache_metrics()
    assert metrics["artifact_entries"] == 1
    assert metrics["artifact_bytes"] == 8
    assert metrics["artifact_max_bytes"] == 10


def test_export_controller_rejects_oversize_artifact_from_cache(monkeypatch) -> None:
    state = {}
    controller = ExportController(state)
    monkeypatch.setattr(ExportController, "ARTIFACT_CACHE_MAX_BYTES", 4)
    calls = {"render": 0}

    def render(model, frame, request):
        calls["render"] += 1
        return ExportArtifact(
            b"12345678",
            f"x.{request.extension}",
            request.mime_type,
            request.format_id,
            request.format_label,
            request.profile_id,
        )

    first, _ = controller.prepare(_request("fmt1"), frame=[1], build_model=lambda *_: object(), render_artifact=render)
    second, metrics = controller.prepare(_request("fmt1"), frame=[1], build_model=lambda *_: object(), render_artifact=render)

    assert first.content == second.content
    assert calls["render"] == 2
    assert metrics["artifact_cache_hit"] is False
    assert controller.cache_metrics()["artifact_entries"] == 0
