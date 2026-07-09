from reports import presentation_pdf


def test_pdf_dependency_guard_is_exposed():
    assert hasattr(presentation_pdf, "REPORTLAB_AVAILABLE")
    assert hasattr(presentation_pdf, "ensure_reportlab_available")
