from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def test_v225_9_release_evidence_remains_available_after_later_releases() -> None:
    release = (DOCS / "archive" / "releases" / "v225.9.ru.md").read_text(encoding="utf-8")
    implementation = (DOCS / "15_Implementation_Plan" / "PETROPHYSICAL_ENGINE_VALIDATION_FOUNDATION_V225_9.ru.md").read_text(encoding="utf-8")
    acceptance = (DOCS / "16_Acceptance" / "PETROPHYSICAL_VALIDATION_GATE_V225_9.ru.md").read_text(encoding="utf-8")
    for text in (release, implementation, acceptance):
        assert "v225.9" in text
        assert "Dual Water" in text


def test_manifest_registers_trilingual_user_and_developer_instructions() -> None:
    manifest = json.loads((DOCS / "documentation_manifest.json").read_text(encoding="utf-8"))
    by_id = {item["id"]: item for item in manifest["documents"]}
    for document_id in ("petrophysical_validation_gate", "petrophysical_validation_architecture"):
        item = by_id[document_id]
        assert set(item["languages"]) == {"ru", "kk", "en"}
        for relative in item["languages"].values():
            assert (DOCS / relative).is_file()


def test_language_indexes_link_validation_instructions_and_readmes_stay_version_neutral() -> None:
    for suffix in ("ru", "kk", "en"):
        user_index = (DOCS / "user" / suffix / "index.md").read_text(encoding="utf-8")
        developer_index = (DOCS / "developer" / suffix / "index.md").read_text(encoding="utf-8")
        readme = (ROOT / f"README.{suffix}.md").read_text(encoding="utf-8")
        assert "petrophysical_validation_gate.md" in user_index
        assert "petrophysical_validation_architecture.md" in developer_index
        assert f"docs/user/{suffix}/index.md" in readme
        assert "v225.9" not in readme


def test_formula_audit_keeps_dual_water_blocked() -> None:
    registry = json.loads((ROOT / "config" / "petrophysical_method_registry_v225_9.json").read_text(encoding="utf-8"))
    method = next(item for item in registry["methods"] if item["method_id"] == "petrophysics.sw_dual_water_foundation")
    assert method["report_policy"] == "blocked_final_report"
    audit = (DOCS / "06_Calculation_Engine" / "FORMULA_SOURCE_AUDIT.md").read_text(encoding="utf-8")
    assert "blocked final report" in audit.lower()
