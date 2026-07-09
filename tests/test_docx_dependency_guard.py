from reports import presentation_docx


def test_docx_dependency_guard_is_exposed():
    assert hasattr(presentation_docx, "DOCX_AVAILABLE")
    assert hasattr(presentation_docx, "ensure_docx_available")
