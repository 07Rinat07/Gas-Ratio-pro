from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def test_v225_9_build_and_stage_documents_are_synchronized() -> None:
    assert (ROOT / "BUILD_VERSION").read_text(encoding="utf-8").strip() == "v225.9"
    assert (ROOT / "DEPLOYMENT_BUILD.txt").read_text(encoding="utf-8").strip() == "Gas Ratio Pro v225.9"
    for suffix in ("ru", "kk", "en"):
        status = (DOCS / f"PROJECT_STATUS.{suffix}.md").read_text(encoding="utf-8")
        roadmap = (DOCS / f"PROJECT_ROADMAP.{suffix}.md").read_text(encoding="utf-8")
        plan = (DOCS / "project" / f"PROJECT_PLAN.{suffix}.md").read_text(encoding="utf-8")
        changelog = (DOCS / f"CHANGELOG.{suffix}.md").read_text(encoding="utf-8")
        assert "v225.9" in status
        assert "Petrophysical Engine Validation Foundation" in roadmap
        assert "v225.9" in plan
        assert "v225.9" in changelog


def test_manifest_registers_trilingual_user_and_developer_instructions() -> None:
    manifest = json.loads((DOCS / "documentation_manifest.json").read_text(encoding="utf-8"))
    by_id = {item["id"]: item for item in manifest["documents"]}
    for document_id in ("petrophysical_validation_gate", "petrophysical_validation_architecture"):
        item = by_id[document_id]
        assert set(item["languages"]) == {"ru", "kk", "en"}
        for relative in item["languages"].values():
            assert (DOCS / relative).is_file()


def test_readmes_link_validation_instructions_in_all_languages() -> None:
    for suffix in ("ru", "kk", "en"):
        readme = (ROOT / f"README.{suffix}.md").read_text(encoding="utf-8")
        assert "v225.9" in readme
        assert f"docs/user/{suffix}/petrophysical_validation_gate.md" in readme
        assert f"docs/developer/{suffix}/petrophysical_validation_architecture.md" in readme


def test_formula_audit_keeps_dual_water_blocked() -> None:
    registry = json.loads((ROOT / "config" / "petrophysical_method_registry_v225_9.json").read_text(encoding="utf-8"))
    method = next(item for item in registry["methods"] if item["method_id"] == "petrophysics.sw_dual_water_foundation")
    assert method["report_policy"] == "blocked_final_report"
    audit = (DOCS / "06_Calculation_Engine" / "FORMULA_SOURCE_AUDIT.md").read_text(encoding="utf-8")
    assert "blocked final report" in audit.lower()
