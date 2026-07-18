from __future__ import annotations

from core.application_service_container import ApplicationServiceContainer, application_service_container
from core.runtime_service_registry import RuntimeServiceRegistry
from core.ui_behavior_contracts import PDF_PREVIEW_BEHAVIOR
from reports.pdf_preview import (
    PdfPreviewPage,
    PdfPreviewResult,
    PdfPreviewRuntimeCache,
    build_pdf_preview_signature,
    next_pdf_preview_start_page,
    shift_pdf_preview_window,
    store_pdf_preview_cache_with_diagnostics,
    validate_pdf_preview_page_jump,
)


def _preview_result(*, page_number: int = 1, size_bytes: int = 3) -> PdfPreviewResult:
    page = PdfPreviewPage(
        page_number=page_number,
        image_png=b"x" * max(1, size_bytes),
        width=10,
        height=20,
    )
    return PdfPreviewResult(
        pages=(page,),
        total_pages=max(page_number, 1),
        rendered_pages=1,
        backend="test",
        truncated=False,
        image_size_bytes=size_bytes,
    )


def test_professional_export_panel_exposes_pdf_preview_behavior_contract() -> None:
    import app.streamlit_app as streamlit_app

    assert streamlit_app.PDF_PREVIEW_BEHAVIOR is PDF_PREVIEW_BEHAVIOR
    assert PDF_PREVIEW_BEHAVIOR.expander_label == "Предпросмотр страниц PDF"
    assert PDF_PREVIEW_BEHAVIOR.create_action_label == "Создать предпросмотр"
    assert PDF_PREVIEW_BEHAVIOR.clear_cache_label == "Очистить кэш предпросмотра"

    first = build_pdf_preview_signature(
        b"%PDF-1.4\npreview",
        request_signature="request-a",
        page_limit=5,
        start_page=1,
        dpi=110,
    )
    second = build_pdf_preview_signature(
        b"%PDF-1.4\npreview",
        request_signature="request-a",
        page_limit=5,
        start_page=2,
        dpi=110,
    )
    assert first != second


def test_pdf_preview_navigation_and_dpi_are_bounded_by_behavior_contract() -> None:
    assert PDF_PREVIEW_BEHAVIOR.dpi_options == (72, 90, 110, 144, 180)
    assert PDF_PREVIEW_BEHAVIOR.layout_options == ("Одна колонка", "Две колонки")
    assert PDF_PREVIEW_BEHAVIOR.previous_label == "← Предыдущие"
    assert PDF_PREVIEW_BEHAVIOR.next_label == "Следующие →"

    assert shift_pdf_preview_window(1, direction=1, page_limit=5, total_pages=12) == 6
    assert shift_pdf_preview_window(6, direction=-1, page_limit=5, total_pages=12) == 1
    assert shift_pdf_preview_window(11, direction=1, page_limit=5, total_pages=12) == 11


def test_pdf_preview_direct_page_jump_returns_validation_feedback() -> None:
    below = validate_pdf_preview_page_jump(0, total_pages=12, page_limit=5)
    past_end = validate_pdf_preview_page_jump(99, total_pages=12, page_limit=5)
    valid = validate_pdf_preview_page_jump(6, total_pages=12, page_limit=5)

    assert below.adjusted is True
    assert below.code == "below_minimum"
    assert below.normalized_page == 1
    assert past_end.adjusted is True
    assert past_end.code == "past_document_end"
    assert past_end.normalized_page == 11
    assert "12" in past_end.message
    assert valid.adjusted is False
    assert valid.code == "valid"


def test_pdf_preview_prefetch_is_opt_in_and_uses_container_owned_metrics(tmp_path) -> None:
    assert PDF_PREVIEW_BEHAVIOR.prefetch_is_opt_in is True
    assert PDF_PREVIEW_BEHAVIOR.prefetch_label
    assert next_pdf_preview_start_page(1, total_pages=8, page_limit=3) == 4
    assert next_pdf_preview_start_page(7, total_pages=8, page_limit=3) is None

    registry = RuntimeServiceRegistry()
    container = ApplicationServiceContainer(registry, {})
    metrics = container.cache_metrics_registry()
    service = container.pdf_preview(project_id="project-a", root=tmp_path)

    assert service.inspect("adjacent").hit is False
    service.store("adjacent", _preview_result(page_number=4))
    assert service.inspect("adjacent").hit is True

    snapshot = {item.name: item for item in metrics.snapshots()}["pdf_preview_runtime"]
    assert snapshot.misses == 1
    assert snapshot.hits == 1
    assert snapshot.entries == 1


def test_pdf_preview_cache_exposes_payload_free_hit_miss_telemetry() -> None:
    cache = PdfPreviewRuntimeCache(max_entries=2, max_bytes=32)

    assert cache.inspect("missing").hit is False
    cache.store("page-1", _preview_result(page_number=1, size_bytes=4))
    assert cache.inspect("page-1").hit is True

    snapshot = cache.snapshot()
    assert snapshot.hits == 1
    assert snapshot.misses == 1
    assert snapshot.entry_count == 1
    assert snapshot.image_size_bytes == 4
    assert "image_png" not in snapshot.to_dict()


def test_pdf_preview_memory_budget_reports_eviction() -> None:
    first = store_pdf_preview_cache_with_diagnostics(
        {},
        signature="first",
        result=_preview_result(page_number=1, size_bytes=8),
        max_entries=3,
        max_bytes=12,
    )
    second = store_pdf_preview_cache_with_diagnostics(
        first.payload,
        signature="second",
        result=_preview_result(page_number=2, size_bytes=8),
        max_entries=3,
        max_bytes=12,
    )

    assert PDF_PREVIEW_BEHAVIOR.memory_budget_mib == (8, 16, 24, 48)
    assert second.eviction_count == 1
    assert second.evicted_signatures == ("first",)
    assert second.evicted_bytes == 8
    assert second.retained_bytes == 8


def test_pdf_preview_heavy_payload_is_kept_out_of_session_state(tmp_path) -> None:
    state: dict[str, object] = {}
    container = application_service_container(state)
    service = container.pdf_preview(project_id="project-a", root=tmp_path)
    service.store("page-1", _preview_result(page_number=1, size_bytes=16))

    assert PDF_PREVIEW_BEHAVIOR.heavy_payload_in_session_state is False
    assert all(not isinstance(value, (bytes, bytearray, PdfPreviewResult)) for value in state.values())
    assert not any("pdf_preview" in str(key) for key in state)
    assert service.snapshot().entry_count == 1
