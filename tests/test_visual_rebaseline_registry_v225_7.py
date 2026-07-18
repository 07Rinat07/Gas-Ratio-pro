from pathlib import Path

from services.visual_rebaseline_registry import VisualRebaselineRegistryService


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "config" / "visual_rebaseline_contracts_v225_7.json"


def test_all_13_visual_contracts_have_approved_semantic_rebaseline() -> None:
    registry = VisualRebaselineRegistryService().load(REGISTRY)
    assert registry.ok is True
    assert len(registry.contracts) == 13
    assert all(item.status == "approved" and item.semantic_sha256 for item in registry.contracts)


def test_visual_rebaseline_covers_the_legacy_visual_nodeids() -> None:
    import json

    legacy = json.loads((ROOT / "config" / "legacy_regression_contracts_v225_7.json").read_text(encoding="utf-8"))
    expected = {
        item["nodeid"]
        for item in legacy["contracts"]
        if item["category"] == "visual_contract_rebaseline"
    }
    registry = VisualRebaselineRegistryService().load(REGISTRY)
    assert {item.nodeid for item in registry.contracts} == expected
