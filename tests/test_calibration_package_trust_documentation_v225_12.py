from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def test_v225_12_build_metadata_and_trilingual_release_governance() -> None:
    assert (ROOT / "BUILD_VERSION").read_text(encoding="utf-8").strip() == "v225.12"
    assert (ROOT / "DEPLOYMENT_BUILD.txt").read_text(encoding="utf-8").strip() == "Gas Ratio Pro v225.12"
    for language in ("ru", "kk", "en"):
        documents = (
            DOCS / f"PROJECT_STATUS.{language}.md",
            DOCS / f"PROJECT_ROADMAP.{language}.md",
            DOCS / "project" / f"PROJECT_PLAN.{language}.md",
            DOCS / f"CHANGELOG.{language}.md",
            DOCS / "15_Implementation_Plan" / f"CALIBRATION_PACKAGE_TRUST_REVIEW_V225_12.{language}.md",
            DOCS / "16_Acceptance" / f"CALIBRATION_PACKAGE_TRUST_REVIEW_V225_12.{language}.md",
            DOCS / "archive" / "releases" / f"v225.12.{language}.md",
        )
        for path in documents:
            text = path.read_text(encoding="utf-8")
            assert "v225.12" in text, path
            assert "Stage 5.3" in text or "Calibration Package Trust & Review Workflow" in text, path


def test_manifest_and_indexes_register_trust_docs_in_three_languages() -> None:
    manifest = json.loads((DOCS / "documentation_manifest.json").read_text(encoding="utf-8"))
    by_id = {item["id"]: item for item in manifest["documents"]}
    expected = {
        "calibration_package_trust_workflow": "user",
        "calibration_package_trust_architecture": "developer",
    }
    for document_id, audience in expected.items():
        item = by_id[document_id]
        assert item["revision"] == 1
        assert item["audience"] == audience
        assert set(item["languages"]) == {"ru", "kk", "en"}
        for relative_path in item["languages"].values():
            assert (DOCS / relative_path).is_file()
    for language in ("ru", "kk", "en"):
        assert "calibration_package_trust_workflow.md" in (
            DOCS / "user" / language / "index.md"
        ).read_text(encoding="utf-8")
        assert "calibration_package_trust_architecture.md" in (
            DOCS / "developer" / language / "index.md"
        ).read_text(encoding="utf-8")


def test_trust_docs_preserve_cryptographic_review_promotion_and_security_contracts() -> None:
    required_terms = (
        "Ed25519",
        "trust registry",
        "technical_reviewer",
        "data_governance_reviewer",
        "development",
        "validation",
        "production",
        "revocation",
        "expiry",
        "lineage",
        "private key",
        "blocked_final_report",
        "Export History v6",
    )
    for language in ("ru", "kk", "en"):
        user_doc = (DOCS / "user" / language / "calibration_package_trust_workflow.md").read_text(encoding="utf-8")
        developer_doc = (DOCS / "developer" / language / "calibration_package_trust_architecture.md").read_text(encoding="utf-8")
        combined = user_doc + "\n" + developer_doc
        for term in required_terms:
            assert term.casefold() in combined.casefold(), (language, term)


def test_stage_5_3_tools_registry_and_evidence_contract_exist() -> None:
    for relative_path in (
        "core/calibration_package_trust_contract.py",
        "services/calibration_package_trust_application_service.py",
        "services/calibration_package_trust_diagnostics.py",
        "config/calibration_trust_registry_v225_12.json",
        "scripts/generate_calibration_signing_key.py",
        "scripts/sign_operator_calibration_package.py",
        "scripts/run_petrophysical_stage_5_3_gate.py",
    ):
        assert (ROOT / relative_path).is_file(), relative_path
    registry = json.loads((ROOT / "config/calibration_trust_registry_v225_12.json").read_text(encoding="utf-8"))
    assert registry["keys"] == []
    assert registry["registry_fingerprint"]


def test_private_keys_and_ci_workflows_are_absent_from_user_distribution_tree() -> None:
    forbidden_suffixes = {".pem", ".key", ".p12", ".pfx"}
    forbidden = [
        path
        for path in ROOT.rglob("*")
        if path.is_file() and path.suffix.casefold() in forbidden_suffixes
    ]
    assert forbidden == []
    assert not (ROOT / ".github" / "workflows").exists()


def test_root_readmes_remain_current_overviews_without_release_history() -> None:
    forbidden = (
        "Stable-релиз v225",
        "Предыдущий stable-релиз",
        "Stable release v225",
        "Previous stable release",
        "Stage 5.2 gate:",
        "2915 passed",
    )
    for name in ("README.md", "README.ru.md", "README.kk.md", "README.en.md"):
        text = (ROOT / name).read_text(encoding="utf-8")
        for fragment in forbidden:
            assert fragment not in text, (name, fragment)


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
