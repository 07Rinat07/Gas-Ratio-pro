import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_evaluated_components_are_registered_with_license_and_status() -> None:
    payload = json.loads((ROOT / "resources/governance/third_party_component_registry.json").read_text(encoding="utf-8"))
    by_name = {item["name"]: item for item in payload["components"]}
    assert by_name["dlisio"]["license_spdx"] == "LGPL-3.0-or-later"
    assert by_name["segyio"]["integration_type"] == "lazy-optional-runtime-adapter"
    assert by_name["SEG-Y Revision 2.1"]["review_status"] == "approved-reference-only"


def test_research_decisions_are_documented() -> None:
    assert (ROOT / "docs/research/DLIS_LIS79_ADAPTER_EVALUATION.md").is_file()
    assert (ROOT / "docs/research/SEGY_ADAPTER_EVALUATION.md").is_file()
