from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def test_mandatory_governance_documents_exist() -> None:
    required = (
        "OPEN_STANDARDS_POLICY.md",
        "LICENSE_POLICY.md",
        "RESEARCH_POLICY.md",
        "DEPENDENCY_EVALUATION_GUIDE.md",
    )
    for name in required:
        path = DOCS / name
        assert path.is_file()
        assert path.read_text(encoding="utf-8").strip()


def test_component_registry_is_machine_readable_and_requires_license_evidence() -> None:
    path = ROOT / "resources" / "governance" / "third_party_component_registry.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema"] == "gas-ratio-pro/third-party-component-registry/v1"
    required = set(payload["required_fields"])
    assert {"name", "license_spdx", "source_url", "review_status", "notices"} <= required
    assert "segy" in payload["candidate_domains"]
    assert "dlis-lis79" in payload["candidate_domains"]


def test_three_language_external_source_guidance_is_registered_and_present() -> None:
    manifest = json.loads((DOCS / "documentation_manifest.json").read_text(encoding="utf-8"))
    by_id = {item["id"]: item for item in manifest["documents"]}
    for doc_id in ("supported_formats_and_legal_sources", "external_standard_integration"):
        item = by_id[doc_id]
        assert item["revision"] == 1
        assert set(item["languages"]) == {"ru", "kk", "en"}
        for relative in item["languages"].values():
            path = DOCS / relative
            assert path.is_file()
            assert len(path.read_text(encoding="utf-8").strip()) > 100


def test_architecture_and_roadmap_reference_governance_contract() -> None:
    architecture = (DOCS / "ARCHITECTURE.md").read_text(encoding="utf-8")
    roadmap = (DOCS / "PROJECT_ROADMAP.md").read_text(encoding="utf-8")
    assert "External standards and dependency isolation" in architecture
    assert "Open Standards and Legal Research Governance" in roadmap
    assert "third-party component" in roadmap
