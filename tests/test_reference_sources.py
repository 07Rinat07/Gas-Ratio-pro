from __future__ import annotations

from pathlib import Path

from projects.reference_sources import (
    ReferenceSource,
    add_pdf_reference_source,
    build_reference_source_table,
    build_reference_validation_table,
    build_sources_markdown,
    list_reference_sources,
    save_reference_registry,
    summarize_reference_sources,
    validate_reference_sources,
)


def _minimal_pdf(path: Path) -> None:
    path.write_bytes(
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Count 0>>endobj\n"
        b"trailer<</Root 1 0 R>>\n%%EOF\n"
    )


def test_add_pdf_reference_source_copies_file_and_registers_relative_path(tmp_path: Path) -> None:
    source_pdf = tmp_path / "input.pdf"
    _minimal_pdf(source_pdf)

    source = add_pdf_reference_source(
        tmp_path,
        "demo-project",
        source_pdf,
        title="Test PDF Source",
        authors=("Author A",),
        year="2026",
        used_for=("unit test",),
    )

    assert source.relative_path == "sources/test-pdf-source.pdf"
    assert (tmp_path / "demo-project" / source.relative_path).exists()
    assert source.sha256
    assert list_reference_sources(tmp_path, "demo-project")[0].title == "Test PDF Source"


def test_reference_source_validation_detects_missing_file_and_local_path(tmp_path: Path) -> None:
    save_reference_registry(
        tmp_path,
        "Demo",
        [
            ReferenceSource(
                id="bad-source",
                title="Bad Source",
                relative_path="C:\\Users\\SRR07\\Downloads\\bad.pdf",
                original_file_name="bad.pdf",
            )
        ],
    )

    issues = validate_reference_sources(tmp_path, "Demo")
    codes = {issue.code for issue in issues}

    assert "missing_file" in codes
    assert "local_windows_path" in codes


def test_reference_source_tables_summary_and_markdown(tmp_path: Path) -> None:
    source_pdf = tmp_path / "manual.pdf"
    _minimal_pdf(source_pdf)
    add_pdf_reference_source(tmp_path, "Demo", source_pdf, title="Manual", used_for=("docs",))

    table = build_reference_source_table(tmp_path, "Demo")
    validation_table = build_reference_validation_table(tmp_path, "Demo")
    summary = summarize_reference_sources(tmp_path, "Demo")
    markdown = build_sources_markdown(tmp_path, "Demo")

    assert table[0]["Название"] == "Manual"
    assert validation_table == []
    assert summary.total == 1
    assert summary.pdf == 1
    assert "Manual" in markdown
    assert "sources/manual.pdf" in markdown
