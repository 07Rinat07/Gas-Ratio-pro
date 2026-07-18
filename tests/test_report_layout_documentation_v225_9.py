from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def test_manifest_registers_adaptive_layout_documents_in_three_languages() -> None:
    manifest = json.loads((DOCS / "documentation_manifest.json").read_text(encoding="utf-8"))
    by_id = {item["id"]: item for item in manifest["documents"]}
    for document_id in ("adaptive_report_layout", "adaptive_report_layout_architecture"):
        item = by_id[document_id]
        assert item["revision"] == 1
        assert set(item["languages"]) == {"ru", "kk", "en"}
        for relative_path in item["languages"].values():
            assert (DOCS / relative_path).is_file()


def test_language_indexes_and_readmes_link_adaptive_layout_contract() -> None:
    for language in ("ru", "kk", "en"):
        user_index = (DOCS / "user" / language / "index.md").read_text(encoding="utf-8")
        developer_index = (DOCS / "developer" / language / "index.md").read_text(encoding="utf-8")
        readme = (ROOT / f"README.{language}.md").read_text(encoding="utf-8")
        assert "adaptive_report_layout.md" in user_index
        assert "adaptive_report_layout_architecture.md" in developer_index
        assert f"docs/user/{language}/adaptive_report_layout.md" in readme
        assert f"docs/developer/{language}/adaptive_report_layout_architecture.md" in readme


def test_release_governance_records_full_frame_landscape_policy() -> None:
    required_terms = ("v225.9", "A3 landscape", "frame")
    for language in ("ru", "kk", "en"):
        paths = (
            DOCS / f"PROJECT_STATUS.{language}.md",
            DOCS / f"PROJECT_ROADMAP.{language}.md",
            DOCS / "project" / f"PROJECT_PLAN.{language}.md",
            DOCS / f"CHANGELOG.{language}.md",
            DOCS / "archive" / "releases" / f"v225.9.{language}.md",
        )
        for path in paths:
            text = path.read_text(encoding="utf-8")
            for term in required_terms:
                assert term in text, f"{term!r} missing from {path}"


def test_readability_contract_and_visual_baseline_are_documented() -> None:
    for language in ("ru", "kk", "en"):
        user_doc = (DOCS / "user" / language / "adaptive_report_layout.md").read_text(encoding="utf-8")
        developer_doc = (DOCS / "developer" / language / "adaptive_report_layout_architecture.md").read_text(encoding="utf-8")
        assert "print-readability/v1.1" in user_doc
        assert "available-frame" in user_doc
        assert "print-readability/v1.1" in developer_doc
        assert "visual_rebaseline_contracts_v225_9.json" in developer_doc
