from __future__ import annotations

import json
from pathlib import Path

from reports.presentation_export_contract import (
    EXPORT_CONTRACT_SCHEMA,
    PRESENTATION_BUNDLE_SCHEMA,
    validate_export_contract,
)
from scripts.release_export_qa import run_release_export_qa


def test_release_qa_validates_export_contract_schema(tmp_path) -> None:
    summary = run_release_export_qa(tmp_path)

    assert summary["ok"] is True
    contract = summary["contract"]
    assert contract["schema"] == EXPORT_CONTRACT_SCHEMA
    assert contract["ok"] is True
    assert contract["issue_count"] == 0
    assert contract["checked_contracts"]["bundle_manifest"] == PRESENTATION_BUNDLE_SCHEMA
    assert contract["checked_contracts"]["validation_report"] == "gas-ratio-pro/presentation/bundle-validation/v1"


def test_export_contract_reports_schema_drift(tmp_path) -> None:
    summary = run_release_export_qa(tmp_path)
    manifest_path = Path(summary["smoke"]["manifest"])
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["schema"] = "gas-ratio-pro/presentation/bundle-export/v0"
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    contract = validate_export_contract(manifest_path, validation_report_path=summary["validation"]["validation_report"])

    assert contract.ok is False
    assert contract.issue_count >= 1
    assert any(issue["kind"] == "schema_mismatch" for issue in contract.issues)


def test_export_contract_requires_visualization_asset_index_for_previews(tmp_path) -> None:
    summary = run_release_export_qa(tmp_path)
    manifest_path = Path(summary["smoke"]["manifest"])
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["visualization"]["preview_count"] = 1
    payload["visualization"].pop("asset_index", None)
    payload["files"].pop("visualization_asset_index", None)
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    contract = validate_export_contract(manifest_path, validation_report_path=summary["validation"]["validation_report"])

    assert contract.ok is False
    assert any(issue["kind"] == "missing_visualization_asset_index" for issue in contract.issues)
