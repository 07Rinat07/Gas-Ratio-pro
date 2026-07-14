from __future__ import annotations

from io import BytesIO

import pytest

from reports.pdf_preview import (
    bounded_pdf_preview_start_page,
    build_pdf_preview,
    build_pdf_preview_signature,
    shift_pdf_preview_window,
    validate_pdf_preview_page_jump,
)


def _sample_pdf(page_count: int = 3) -> bytes:
    reportlab = pytest.importorskip("reportlab")
    from reportlab.pdfgen import canvas

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)
    for page in range(page_count):
        pdf.drawString(72, 760, f"Preview page {page + 1}")
        pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def test_build_pdf_preview_is_bounded_and_returns_png_pages() -> None:
    result = build_pdf_preview(_sample_pdf(4), page_limit=2, dpi=90)

    assert result.rendered_pages == 2
    assert result.total_pages >= 2
    assert result.truncated is True
    assert [page.page_number for page in result.pages] == [1, 2]
    assert all(page.image_png.startswith(b"\x89PNG\r\n\x1a\n") for page in result.pages)
    assert all(page.width > 0 and page.height > 0 for page in result.pages)


def test_build_pdf_preview_reports_complete_document() -> None:
    result = build_pdf_preview(_sample_pdf(1), page_limit=5)

    assert result.rendered_pages == 1
    assert result.total_pages == 1
    assert result.truncated is False


def test_build_pdf_preview_rejects_non_pdf_payload() -> None:
    with pytest.raises(ValueError, match="valid PDF"):
        build_pdf_preview(b"not-a-pdf")


def test_build_pdf_preview_clamps_page_limit() -> None:
    result = build_pdf_preview(_sample_pdf(2), page_limit=0)
    assert result.rendered_pages == 1


def test_pdf_preview_signature_is_stable_and_parameter_bound() -> None:
    payload = _sample_pdf(2)
    first = build_pdf_preview_signature(
        payload, request_signature="request-a", page_limit=5, dpi=110
    )
    second = build_pdf_preview_signature(
        payload, request_signature="request-a", page_limit=5, dpi=110
    )

    assert first == second
    assert first != build_pdf_preview_signature(
        payload, request_signature="request-b", page_limit=5, dpi=110
    )
    assert first != build_pdf_preview_signature(
        payload, request_signature="request-a", page_limit=2, dpi=110
    )


def test_pdf_preview_signature_rejects_non_pdf_payload() -> None:
    with pytest.raises(ValueError, match="valid PDF"):
        build_pdf_preview_signature(b"not-a-pdf")


def test_build_pdf_preview_reports_runtime_metrics() -> None:
    payload = _sample_pdf(3)
    result = build_pdf_preview(payload, page_limit=2, dpi=90)

    assert result.render_duration_seconds >= 0.0
    assert result.source_size_bytes == len(payload)
    assert result.image_size_bytes == sum(len(page.image_png) for page in result.pages)
    assert result.average_page_size_bytes > 0


def test_build_pdf_preview_supports_selective_page_range() -> None:
    result = build_pdf_preview(_sample_pdf(6), start_page=3, page_limit=2, dpi=90)

    assert result.rendered_pages == 2
    assert [page.page_number for page in result.pages] == [3, 4]
    assert result.truncated is True


def test_build_pdf_preview_clamps_start_page_to_first_page() -> None:
    result = build_pdf_preview(_sample_pdf(2), start_page=0, page_limit=1)

    assert [page.page_number for page in result.pages] == [1]


def test_pdf_preview_signature_is_bound_to_start_page() -> None:
    payload = _sample_pdf(4)

    first = build_pdf_preview_signature(payload, start_page=1, page_limit=2)
    second = build_pdf_preview_signature(payload, start_page=2, page_limit=2)

    assert first != second


def test_pdf_preview_signature_is_bound_to_dpi() -> None:
    payload = _sample_pdf(2)
    assert build_pdf_preview_signature(payload, dpi=90) != build_pdf_preview_signature(payload, dpi=144)


def test_shift_pdf_preview_window_moves_by_bounded_page_group() -> None:
    assert shift_pdf_preview_window(1, direction=1, page_limit=5, total_pages=12) == 6
    assert shift_pdf_preview_window(6, direction=-1, page_limit=5, total_pages=12) == 1
    assert shift_pdf_preview_window(11, direction=1, page_limit=5, total_pages=12) == 11


def test_bounded_pdf_preview_start_page_clamps_to_last_window() -> None:
    assert bounded_pdf_preview_start_page(99, total_pages=12, page_limit=5) == 11
    assert bounded_pdf_preview_start_page(0, total_pages=12, page_limit=5) == 1


def test_validate_pdf_preview_page_jump_accepts_valid_page() -> None:
    result = validate_pdf_preview_page_jump(6, total_pages=12, page_limit=5)

    assert result.adjusted is False
    assert result.code == "valid"
    assert result.normalized_page == 6


def test_validate_pdf_preview_page_jump_clamps_past_document_end() -> None:
    result = validate_pdf_preview_page_jump(99, total_pages=12, page_limit=5)

    assert result.adjusted is True
    assert result.code == "past_document_end"
    assert result.normalized_page == 11
    assert "12" in result.message


def test_validate_pdf_preview_page_jump_handles_invalid_lower_bound() -> None:
    result = validate_pdf_preview_page_jump(0, total_pages=12, page_limit=5)

    assert result.adjusted is True
    assert result.code == "below_minimum"
    assert result.normalized_page == 1


def test_pdf_preview_cache_keeps_bounded_recent_entries() -> None:
    from reports.pdf_preview import resolve_pdf_preview_cache, store_pdf_preview_cache

    first = build_pdf_preview(_sample_pdf(4), start_page=1, page_limit=1, dpi=72)
    second = build_pdf_preview(_sample_pdf(4), start_page=2, page_limit=1, dpi=72)
    third = build_pdf_preview(_sample_pdf(4), start_page=3, page_limit=1, dpi=72)

    cache = store_pdf_preview_cache(None, signature="one", result=first, max_entries=2)
    cache = store_pdf_preview_cache(cache, signature="two", result=second, max_entries=2)
    cache = store_pdf_preview_cache(cache, signature="three", result=third, max_entries=2)

    assert resolve_pdf_preview_cache(cache, signature="three") is third
    assert resolve_pdf_preview_cache(cache, signature="two") is second
    assert resolve_pdf_preview_cache(cache, signature="one") is None


def test_pdf_preview_cache_reads_legacy_single_entry_payload() -> None:
    from reports.pdf_preview import resolve_pdf_preview_cache

    result = build_pdf_preview(_sample_pdf(1), page_limit=1, dpi=72)
    assert resolve_pdf_preview_cache(
        {"signature": "legacy", "result": result}, signature="legacy"
    ) is result


def test_next_pdf_preview_start_page_is_bounded() -> None:
    from reports.pdf_preview import next_pdf_preview_start_page

    assert next_pdf_preview_start_page(1, total_pages=12, page_limit=5) == 6
    assert next_pdf_preview_start_page(6, total_pages=12, page_limit=5) == 11
    assert next_pdf_preview_start_page(11, total_pages=12, page_limit=5) is None
    assert next_pdf_preview_start_page(1, total_pages=0, page_limit=5) is None


def test_inspect_pdf_preview_cache_reports_multi_entry_hit_metadata() -> None:
    from reports.pdf_preview import inspect_pdf_preview_cache, store_pdf_preview_cache

    first = build_pdf_preview(_sample_pdf(3), start_page=1, page_limit=1, dpi=72)
    second = build_pdf_preview(_sample_pdf(3), start_page=2, page_limit=1, dpi=72)
    cache = store_pdf_preview_cache(None, signature="first", result=first)
    cache = store_pdf_preview_cache(cache, signature="second", result=second)

    lookup = inspect_pdf_preview_cache(cache, signature="first")

    assert lookup.hit is True
    assert lookup.result is first
    assert lookup.source == "entries"
    assert lookup.entry_index == 1


def test_inspect_pdf_preview_cache_reports_legacy_and_miss() -> None:
    from reports.pdf_preview import inspect_pdf_preview_cache

    result = build_pdf_preview(_sample_pdf(1), page_limit=1, dpi=72)
    legacy = inspect_pdf_preview_cache(
        {"signature": "legacy", "result": result}, signature="legacy"
    )
    missing = inspect_pdf_preview_cache({}, signature="missing")

    assert legacy.hit is True
    assert legacy.source == "legacy"
    assert legacy.entry_index == 0
    assert missing.hit is False
    assert missing.result is None
    assert missing.source == "miss"
    assert missing.entry_index is None


def test_large_pdf_adjacent_preview_cache_reuses_prefetched_window() -> None:
    from reports.pdf_preview import (
        build_pdf_preview_signature,
        inspect_pdf_preview_cache,
        next_pdf_preview_start_page,
        store_pdf_preview_cache,
    )

    payload = _sample_pdf(24)
    first = build_pdf_preview(payload, start_page=1, page_limit=5, dpi=72)
    adjacent_start = next_pdf_preview_start_page(
        1, total_pages=first.total_pages, page_limit=5
    )
    assert adjacent_start == 6
    signature = build_pdf_preview_signature(
        payload, start_page=adjacent_start, page_limit=5, dpi=72
    )
    prefetched = build_pdf_preview(
        payload, start_page=adjacent_start, page_limit=5, dpi=72
    )
    cache = store_pdf_preview_cache(None, signature=signature, result=prefetched)

    lookup = inspect_pdf_preview_cache(cache, signature=signature)

    assert lookup.hit is True
    assert lookup.result is prefetched
    assert tuple(page.page_number for page in lookup.result.pages) == (6, 7, 8, 9, 10)


def test_summarize_pdf_preview_cache_reports_memory_pressure() -> None:
    from reports.pdf_preview import PdfPreviewPage, PdfPreviewResult, summarize_pdf_preview_cache

    first = PdfPreviewResult(
        pages=(PdfPreviewPage(1, b"x" * 400, 10, 10),),
        total_pages=2,
        rendered_pages=1,
        backend="test",
        truncated=True,
        image_size_bytes=400,
    )
    second = PdfPreviewResult(
        pages=(PdfPreviewPage(2, b"y" * 700, 10, 10),),
        total_pages=2,
        rendered_pages=1,
        backend="test",
        truncated=True,
        image_size_bytes=700,
    )
    cache = {
        "entries": [
            {"signature": "two", "result": second},
            {"signature": "one", "result": first},
        ]
    }

    stats = summarize_pdf_preview_cache(
        cache,
        warning_threshold_bytes=1_000,
        critical_threshold_bytes=2_000,
    )

    assert stats.entry_count == 2
    assert stats.rendered_pages == 2
    assert stats.image_size_bytes == 1_100
    assert stats.largest_entry_bytes == 700
    assert stats.average_entry_bytes == 550
    assert stats.status == "warning"
    assert stats.pressure_ratio == pytest.approx(0.55)


def test_summarize_pdf_preview_cache_supports_empty_legacy_and_critical() -> None:
    from reports.pdf_preview import PdfPreviewResult, summarize_pdf_preview_cache

    empty = summarize_pdf_preview_cache(None)
    legacy_result = PdfPreviewResult(
        pages=(),
        total_pages=1,
        rendered_pages=3,
        backend="test",
        truncated=False,
        image_size_bytes=2_500,
    )
    critical = summarize_pdf_preview_cache(
        {"signature": "legacy", "result": legacy_result},
        warning_threshold_bytes=1_000,
        critical_threshold_bytes=2_000,
    )

    assert empty.status == "empty"
    assert empty.entry_count == 0
    assert critical.status == "critical"
    assert critical.entry_count == 1
    assert critical.image_size_bytes == 2_500


def test_pdf_preview_cache_memory_budget_evicts_oldest_ranges() -> None:
    from reports.pdf_preview import (
        PdfPreviewPage,
        PdfPreviewResult,
        inspect_pdf_preview_cache,
        store_pdf_preview_cache_with_diagnostics,
    )

    def result(page: int, size: int) -> PdfPreviewResult:
        return PdfPreviewResult(
            pages=(PdfPreviewPage(page, b"x" * size, 10, 10),),
            total_pages=3,
            rendered_pages=1,
            backend="test",
            truncated=True,
            image_size_bytes=size,
        )

    first = store_pdf_preview_cache_with_diagnostics(
        None, signature="one", result=result(1, 700), max_entries=3, max_bytes=1_500
    )
    second = store_pdf_preview_cache_with_diagnostics(
        first.payload, signature="two", result=result(2, 700), max_entries=3, max_bytes=1_500
    )
    third = store_pdf_preview_cache_with_diagnostics(
        second.payload, signature="three", result=result(3, 700), max_entries=3, max_bytes=1_500
    )

    assert third.eviction_count == 1
    assert third.evicted_signatures == ("one",)
    assert third.evicted_bytes == 700
    assert third.retained_bytes == 1_400
    assert inspect_pdf_preview_cache(third.payload, signature="three").hit is True
    assert inspect_pdf_preview_cache(third.payload, signature="two").hit is True
    assert inspect_pdf_preview_cache(third.payload, signature="one").hit is False


def test_pdf_preview_cache_keeps_newest_entry_when_it_exceeds_budget() -> None:
    from reports.pdf_preview import PdfPreviewPage, PdfPreviewResult, store_pdf_preview_cache_with_diagnostics

    oversized = PdfPreviewResult(
        pages=(PdfPreviewPage(1, b"x" * 2_000, 10, 10),),
        total_pages=1,
        rendered_pages=1,
        backend="test",
        truncated=False,
        image_size_bytes=2_000,
    )

    stored = store_pdf_preview_cache_with_diagnostics(
        None,
        signature="oversized",
        result=oversized,
        max_entries=3,
        max_bytes=1_000,
    )

    assert stored.eviction_count == 0
    assert stored.retained_bytes == 2_000
    assert stored.budget_bytes == 1_000
    assert len(stored.payload["entries"]) == 1
