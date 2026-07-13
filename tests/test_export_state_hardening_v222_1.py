from __future__ import annotations

from reports.export_controller import (
    ExportArtifact,
    ExportController,
    ExportRequest,
    normalize_export_form_state,
)


def _request(*, context_signature: str = "") -> ExportRequest:
    return ExportRequest(
        project_id="p1",
        project_name="Project",
        source_label="LAS",
        profile_id="engineering",
        format_id="pdf",
        format_label="PDF",
        extension="pdf",
        mime_type="application/pdf",
        depth_top=100.0,
        depth_bottom=200.0,
        source_signature="source",
        calculation_revision=1,
        presentation_revision=1,
        figure_height=1000,
        context_signature=context_signature,
    )


def test_export_form_state_clamps_stale_depth_values() -> None:
    state = {
        "presentation_report_profile_p1": "removed-profile",
        "presentation_export_format_p1": "removed-format",
        "presentation_print_depth_mode_p1": "Выбранный пласт",
        "presentation_print_top_p1": -500.0,
        "presentation_print_bottom_p1": 9999.0,
    }

    normalized = normalize_export_form_state(
        state,
        project_id="p1",
        profile_labels=("Для заказчика", "Инженерный"),
        format_labels=("PDF", "DOCX"),
        print_modes=("Текущий интервал графиков", "Выбрать отдельно"),
        depth_min=100.0,
        depth_max=200.0,
        default_top=120.0,
        default_bottom=180.0,
    )

    assert normalized["profile"] == "Для заказчика"
    assert normalized["format"] == "PDF"
    assert normalized["print_mode"] == "Текущий интервал графиков"
    assert normalized["top"] == 100.0
    assert normalized["bottom"] == 200.0


def test_export_form_state_recovers_non_numeric_and_non_finite_values() -> None:
    state = {
        "presentation_print_top_p1": "bad",
        "presentation_print_bottom_p1": float("nan"),
    }
    normalized = normalize_export_form_state(
        state,
        project_id="p1",
        profile_labels=("Инженерный",),
        format_labels=("PDF",),
        print_modes=("Текущий интервал графиков",),
        depth_min=100.0,
        depth_max=200.0,
        default_top=125.0,
        default_bottom=175.0,
    )
    assert normalized["top"] == 125.0
    assert normalized["bottom"] == 175.0


def test_export_context_signature_invalidates_model_cache() -> None:
    state = {}
    controller = ExportController(state)
    calls = {"model": 0}

    def build_model(frame, request):
        calls["model"] += 1
        return {"context": request.context_signature}

    def render(model, frame, request):
        return ExportArtifact(
            content=model["context"].encode() or b"empty",
            file_name="report.pdf",
            mime_type=request.mime_type,
            format_id=request.format_id,
            format_label=request.format_label,
            profile_id=request.profile_id,
        )

    controller.prepare(
        _request(context_signature="ranking-standard"),
        frame=[1],
        build_model=build_model,
        render_artifact=render,
    )
    artifact, metrics = controller.prepare(
        _request(context_signature="ranking-conservative"),
        frame=[1],
        build_model=build_model,
        render_artifact=render,
    )

    assert calls["model"] == 2
    assert metrics["model_cache_hit"] is False
    assert artifact.content == b"ranking-conservative"


def test_lru_eviction_removes_stale_registry_entries() -> None:
    state = {}
    controller = ExportController(state)

    def render(model, frame, request):
        return ExportArtifact(
            b"ok",
            f"{request.format_id}.bin",
            request.mime_type,
            request.format_id,
            request.format_label,
            request.profile_id,
        )

    for index in range(ExportController.ARTIFACT_CACHE_LIMIT + 8):
        request = ExportRequest(
            **{
                **{field: getattr(_request(), field) for field in _request().__dataclass_fields__},
                "format_id": f"fmt-{index}",
                "format_label": f"FMT {index}",
                "extension": "bin",
            }
        )
        controller.prepare(request, frame=[1], build_model=lambda *_: object(), render_artifact=render)

    registry = state["presentation_export_cache_registry_v222"]
    model_cache = state[ExportController.MODEL_CACHE_KEY]
    artifact_cache = state[ExportController.ARTIFACT_CACHE_KEY]
    assert set(registry) == set(model_cache) | set(artifact_cache)
