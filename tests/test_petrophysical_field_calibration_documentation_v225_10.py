from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def test_v225_10_build_metadata_and_trilingual_release_governance() -> None:
    assert (ROOT / "BUILD_VERSION").read_text(encoding="utf-8").strip() == "v225.10"
    assert (ROOT / "DEPLOYMENT_BUILD.txt").read_text(encoding="utf-8").strip() == "Gas Ratio Pro v225.10"
    for language in ("ru", "kk", "en"):
        status = (DOCS / f"PROJECT_STATUS.{language}.md").read_text(encoding="utf-8")
        roadmap = (DOCS / f"PROJECT_ROADMAP.{language}.md").read_text(encoding="utf-8")
        plan = (DOCS / "project" / f"PROJECT_PLAN.{language}.md").read_text(encoding="utf-8")
        changelog = (DOCS / f"CHANGELOG.{language}.md").read_text(encoding="utf-8")
        release = (DOCS / "archive" / "releases" / f"v225.10.{language}.md").read_text(encoding="utf-8")
        for text in (status, roadmap, plan, changelog, release):
            assert "v225.10" in text
        assert "Stage 5.1" in status
        assert "Stage 5.2" in roadmap


def test_manifest_registers_field_calibration_docs_in_three_languages() -> None:
    manifest = json.loads((DOCS / "documentation_manifest.json").read_text(encoding="utf-8"))
    by_id = {item["id"]: item for item in manifest["documents"]}
    for document_id in (
        "field_calibration_and_report_authorization",
        "field_calibration_authorization_architecture",
    ):
        item = by_id[document_id]
        assert item["revision"] == 1
        assert set(item["languages"]) == {"ru", "kk", "en"}
        for relative_path in item["languages"].values():
            assert (DOCS / relative_path).is_file()


def test_language_indexes_and_readmes_link_stage_5_1_contracts() -> None:
    for language in ("ru", "kk", "en"):
        user_index = (DOCS / "user" / language / "index.md").read_text(encoding="utf-8")
        developer_index = (DOCS / "developer" / language / "index.md").read_text(encoding="utf-8")
        readme = (ROOT / f"README.{language}.md").read_text(encoding="utf-8")
        assert "field_calibration_and_report_authorization.md" in user_index
        assert "field_calibration_authorization_architecture.md" in developer_index
        assert f"docs/user/{language}/field_calibration_and_report_authorization.md" in readme
        assert f"docs/developer/{language}/field_calibration_authorization_architecture.md" in readme


def test_calibration_docs_preserve_legal_and_report_policy() -> None:
    for language in ("ru", "kk", "en"):
        user_doc = (DOCS / "user" / language / "field_calibration_and_report_authorization.md").read_text(encoding="utf-8")
        developer_doc = (DOCS / "developer" / language / "field_calibration_authorization_architecture.md").read_text(encoding="utf-8")
        assert "project-owned" in user_doc
        assert "blocked_final_report" in user_doc
        assert "blocked_final_report" in developer_doc
        assert "petrophysical-report-authorization/v1" in developer_doc


def test_frozen_governance_sections_remain_explicit() -> None:
    for language in ("ru", "kk", "en"):
        roadmap = (DOCS / f"PROJECT_ROADMAP.{language}.md").read_text(encoding="utf-8")
        for term in (
            "Reservoir Intelligence / Interpretation 2.0",
            "Pixler rehabilitation",
            "Ternary rehabilitation",
            "Depth engineering panel",
            "Open Standards and Legal Research Governance",
        ):
            assert term in roadmap
