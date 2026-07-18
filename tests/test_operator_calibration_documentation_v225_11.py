from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def test_v225_11_build_metadata_and_trilingual_release_governance() -> None:
    assert (ROOT / "BUILD_VERSION").read_text(encoding="utf-8").strip() == "v225.11"
    assert (ROOT / "DEPLOYMENT_BUILD.txt").read_text(encoding="utf-8").strip() == "Gas Ratio Pro v225.11"
    for language in ("ru", "kk", "en"):
        status = (DOCS / f"PROJECT_STATUS.{language}.md").read_text(encoding="utf-8")
        roadmap = (DOCS / f"PROJECT_ROADMAP.{language}.md").read_text(encoding="utf-8")
        plan = (DOCS / "project" / f"PROJECT_PLAN.{language}.md").read_text(encoding="utf-8")
        changelog = (DOCS / f"CHANGELOG.{language}.md").read_text(encoding="utf-8")
        release = (DOCS / "archive" / "releases" / f"v225.11.{language}.md").read_text(encoding="utf-8")
        readme = (ROOT / f"README.{language}.md").read_text(encoding="utf-8")
        for text in (status, roadmap, plan, changelog, release, readme):
            assert "v225.11" in text
            assert "Stage 5.2" in text
        assert "Stage 5.3" in roadmap


def test_manifest_registers_operator_calibration_docs_in_three_languages() -> None:
    manifest = json.loads((DOCS / "documentation_manifest.json").read_text(encoding="utf-8"))
    by_id = {item["id"]: item for item in manifest["documents"]}
    for document_id in (
        "operator_calibration_packages",
        "operator_calibration_package_architecture",
    ):
        item = by_id[document_id]
        assert item["revision"] == 1
        assert set(item["languages"]) == {"ru", "kk", "en"}
        for relative_path in item["languages"].values():
            assert (DOCS / relative_path).is_file()


def test_indexes_and_readmes_link_operator_package_contracts() -> None:
    for language in ("ru", "kk", "en"):
        user_index = (DOCS / "user" / language / "index.md").read_text(encoding="utf-8")
        developer_index = (DOCS / "developer" / language / "index.md").read_text(encoding="utf-8")
        readme = (ROOT / f"README.{language}.md").read_text(encoding="utf-8")
        assert "operator_calibration_packages.md" in user_index
        assert "operator_calibration_package_architecture.md" in developer_index
        assert f"docs/user/{language}/operator_calibration_packages.md" in readme
        assert f"docs/developer/{language}/operator_calibration_package_architecture.md" in readme


def test_operator_package_docs_preserve_rights_immutability_and_formula_policy() -> None:
    required_terms = (
        "project",
        "SHA-256",
        "rights",
        "formula",
        "blocked_final_report",
    )
    for language in ("ru", "kk", "en"):
        user_doc = (DOCS / "user" / language / "operator_calibration_packages.md").read_text(encoding="utf-8")
        developer_doc = (DOCS / "developer" / language / "operator_calibration_package_architecture.md").read_text(encoding="utf-8")
        combined = user_doc + "\n" + developer_doc
        for term in required_terms:
            assert term.casefold() in combined.casefold()
        assert "gas-ratio-pro/operator-calibration-package/v1" in developer_doc


def test_stage_5_2_tools_evidence_and_release_archive_policy_exist() -> None:
    assert (ROOT / "scripts" / "build_operator_calibration_package.py").is_file()
    assert (ROOT / "scripts" / "run_petrophysical_stage_5_2_gate.py").is_file()
    assert (ROOT / "artifacts" / "validation" / "petrophysical_operator_calibration_v225_11.json").is_file()
    assert not (ROOT / ".github" / "workflows").exists()


def test_frozen_governance_sections_remain_explicit() -> None:
    for language in ("ru", "kk", "en"):
        roadmap = (DOCS / f"PROJECT_ROADMAP.{language}.md").read_text(encoding="utf-8")
        for term in (
            "Stabilization & Release Audit",
            "Reservoir Intelligence / Interpretation 2.0",
            "Pixler rehabilitation",
            "Ternary rehabilitation",
            "Depth engineering panel",
            "Definition of Done",
            "Open Standards and Legal Research Governance",
        ):
            assert term in roadmap


def test_release_documents_have_no_unresolved_regression_placeholder() -> None:
    paths = [
        ROOT / "README.md",
        ROOT / "README.ru.md",
        ROOT / "README.kk.md",
        ROOT / "README.en.md",
        DOCS / "AI_HANDOFF.md",
        DOCS / "PROJECT_STATUS.md",
        DOCS / "PROJECT_STATUS.ru.md",
        DOCS / "PROJECT_STATUS.kk.md",
        DOCS / "PROJECT_STATUS.en.md",
        DOCS / "project" / "PROJECT_PLAN.md",
        DOCS / "project" / "PROJECT_PLAN.ru.md",
        DOCS / "project" / "PROJECT_PLAN.kk.md",
        DOCS / "project" / "PROJECT_PLAN.en.md",
        DOCS / "CHANGELOG.md",
        DOCS / "CHANGELOG.ru.md",
        DOCS / "CHANGELOG.kk.md",
        DOCS / "CHANGELOG.en.md",
        DOCS / "archive" / "releases" / "v225.11.ru.md",
        DOCS / "archive" / "releases" / "v225.11.kk.md",
        DOCS / "archive" / "releases" / "v225.11.en.md",
    ]
    for path in paths:
        assert "__REGRESSION__" not in path.read_text(encoding="utf-8"), path
