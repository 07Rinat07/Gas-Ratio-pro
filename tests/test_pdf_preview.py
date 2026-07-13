from __future__ import annotations

from io import BytesIO

import pytest

from reports.pdf_preview import build_pdf_preview, build_pdf_preview_signature


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
