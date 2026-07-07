from __future__ import annotations

import json
from pathlib import Path

from projects.documentation_evidence import (
    build_documentation_evidence_issue_table,
    build_documentation_evidence_manifest,
    build_documentation_evidence_markdown,
    build_documentation_evidence_reference_table,
    build_documentation_evidence_source_table,
    find_documentation_source_references,
    load_documentation_evidence_sources,
    summarize_documentation_evidence,
    validate_documentation_evidence,
)


def _minimal_pdf(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Count 0>>endobj\n"
        b"trailer<</Root 1 0 R>>\n%%EOF\n"
    )


def _write_registry(root: Path, entries: list[dict]) -> None:
    registry = root / "docs" / "sources" / "source_registry.json"
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


def test_documentation_evidence_loads_registry_and_finds_references(tmp_path: Path) -> None:
    pdf = tmp_path / "docs" / "sources" / "manual.pdf"
    _minimal_pdf(pdf)
    _write_registry(
        tmp_path,
        [
            {
                "id": "manual",
                "title": "Manual Source",
                "relative_path": "docs/sources/manual.pdf",
                "used_for": ["docs"],
            }
        ],
    )
    doc = tmp_path / "docs" / "spec.md"
    doc.write_text("Источник: docs/sources/manual.pdf\n", encoding="utf-8")

    sources = load_documentation_evidence_sources(tmp_path)
    references = find_documentation_source_references(tmp_path)
    issues = validate_documentation_evidence(tmp_path)

    assert sources[0].title == "Manual Source"
    assert references[0].document_path == "docs/spec.md"
    assert references[0].source_path == "docs/sources/manual.pdf"
    assert issues == ()


def test_documentation_evidence_detects_missing_unregistered_and_local_paths(tmp_path: Path) -> None:
    _write_registry(
        tmp_path,
        [
            {
                "id": "missing",
                "title": "Missing Source",
                "relative_path": "docs/sources/missing.pdf",
            }
        ],
    )
    doc = tmp_path / "docs" / "spec.md"
    doc.write_text(
        "Локальный файл: C:\\Users\\SRR07\\Downloads\\manual.pdf\n"
        "Источник: docs/sources/extra.pdf\n",
        encoding="utf-8",
    )

    issues = validate_documentation_evidence(tmp_path)
    codes = {issue.code for issue in issues}

    assert "registered_source_missing" in codes
    assert "referenced_source_missing" in codes
    assert "unregistered_source_reference" in codes
    assert "local_path_in_documentation" in codes


def test_documentation_evidence_tables_manifest_and_markdown(tmp_path: Path) -> None:
    pdf = tmp_path / "docs" / "sources" / "manual.pdf"
    _minimal_pdf(pdf)
    _write_registry(
        tmp_path,
        [
            {
                "id": "manual",
                "title": "Manual Source",
                "relative_path": "docs/sources/manual.pdf",
                "used_for": ["LAS Platform"],
            }
        ],
    )
    (tmp_path / "docs" / "spec.md").write_text("Источник: docs/sources/manual.pdf\n", encoding="utf-8")

    source_table = build_documentation_evidence_source_table(tmp_path)
    reference_table = build_documentation_evidence_reference_table(tmp_path)
    issue_table = build_documentation_evidence_issue_table(tmp_path)
    manifest = build_documentation_evidence_manifest(tmp_path)
    summary = summarize_documentation_evidence(tmp_path)
    markdown = build_documentation_evidence_markdown(tmp_path)

    assert source_table[0]["Название"] == "Manual Source"
    assert reference_table[0]["Источник"] == "docs/sources/manual.pdf"
    assert issue_table == []
    assert manifest["summary"]["registered_sources"] == 1
    assert summary.errors == 0
    assert "Documentation Evidence Audit" in markdown
