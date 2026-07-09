from __future__ import annotations

"""Formal schema contract checks for presentation export bundles.

The project already writes machine-readable manifests, visualization asset
indexes and validation reports.  This module centralizes their schema versions
and performs lightweight structural checks so release QA can detect accidental
contract drift before external tools or CI integrations consume a bundle.
"""

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

PRESENTATION_BUNDLE_SCHEMA = "gas-ratio-pro/presentation/bundle-export/v1"
VISUALIZATION_ASSET_INDEX_SCHEMA = "gas-ratio-pro/presentation/visualization-assets/v1"
BUNDLE_VALIDATION_REPORT_SCHEMA = "gas-ratio-pro/presentation/bundle-validation/v1"
EXPORT_CONTRACT_SCHEMA = "gas-ratio-pro/presentation/export-contract/v1"

REQUIRED_BUNDLE_FILES = (
    "html",
    "pdf",
    "docx",
    "html_manifest",
    "pdf_manifest",
    "docx_manifest",
)

REQUIRED_BUNDLE_CONSISTENCY = (
    "same_profile",
    "same_table_titles",
    "same_figure_count",
    "same_visualization_preview_count",
    "single_source_model",
)


@dataclass(frozen=True)
class ExportContractValidation:
    """Result of a filesystem-level export contract check."""

    ok: bool
    schema: str
    bundle_manifest: Path
    issues: tuple[dict[str, str], ...]
    checked_contracts: dict[str, str]

    @property
    def issue_count(self) -> int:
        return len(self.issues)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": EXPORT_CONTRACT_SCHEMA,
            "ok": self.ok,
            "status": "ok" if self.ok else "failed",
            "bundle_manifest": str(self.bundle_manifest),
            "checked_contracts": dict(self.checked_contracts),
            "issue_count": self.issue_count,
            "issues": list(self.issues),
        }


def _issue(kind: str, target: str, message: str) -> dict[str, str]:
    return {"severity": "error", "kind": kind, "target": target, "message": message}


def _load_json(path: Path) -> tuple[dict[str, Any], list[dict[str, str]]]:
    if not path.exists():
        return {}, [_issue("missing_contract_file", str(path), "Referenced contract file does not exist")]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {}, [_issue("invalid_json", str(path), f"JSON decoding failed: {exc.msg}")]
    if not isinstance(payload, dict):
        return {}, [_issue("invalid_json_root", str(path), "Contract root must be a JSON object")]
    return payload, []


def _require_schema(payload: dict[str, Any], *, expected: str, target: str) -> list[dict[str, str]]:
    actual = str(payload.get("schema") or "")
    if actual != expected:
        return [_issue("schema_mismatch", target, f"Expected {expected}, got {actual or '<missing>'}")]
    return []


def validate_export_contract(
    bundle_manifest_path: str | Path,
    *,
    validation_report_path: str | Path | None = None,
) -> ExportContractValidation:
    """Validate formal bundle, asset-index and validation-report contracts.

    The check is intentionally structural and deterministic. It does not render
    reports or recalculate LAS data; it verifies the already produced export
    artifacts and their declared schema versions.
    """

    manifest_path = Path(bundle_manifest_path)
    manifest, issues = _load_json(manifest_path)
    issues.extend(_require_schema(manifest, expected=PRESENTATION_BUNDLE_SCHEMA, target="bundle_manifest"))

    files = manifest.get("files", {}) if isinstance(manifest, dict) else {}
    if not isinstance(files, dict):
        files = {}
        issues.append(_issue("invalid_files_contract", "bundle_manifest.files", "files must be an object"))

    for key in REQUIRED_BUNDLE_FILES:
        value = files.get(key)
        if not isinstance(value, str) or not value.strip():
            issues.append(_issue("missing_required_file_reference", f"bundle_manifest.files.{key}", "Required file reference is absent"))

    consistency = manifest.get("consistency", {}) if isinstance(manifest, dict) else {}
    if not isinstance(consistency, dict):
        consistency = {}
        issues.append(_issue("invalid_consistency_contract", "bundle_manifest.consistency", "consistency must be an object"))
    for key in REQUIRED_BUNDLE_CONSISTENCY:
        if consistency.get(key) is not True:
            issues.append(_issue("failed_required_consistency", f"bundle_manifest.consistency.{key}", "Required consistency flag must be true"))

    checked_contracts: dict[str, str] = {"bundle_manifest": PRESENTATION_BUNDLE_SCHEMA}

    visualization = manifest.get("visualization", {}) if isinstance(manifest, dict) else {}
    if not isinstance(visualization, dict):
        visualization = {}
        issues.append(_issue("invalid_visualization_contract", "bundle_manifest.visualization", "visualization must be an object"))

    asset_index_name = str(files.get("visualization_asset_index") or visualization.get("asset_index") or "").strip()
    preview_count = int(visualization.get("preview_count") or 0)
    if preview_count > 0:
        if not asset_index_name:
            issues.append(_issue("missing_visualization_asset_index", "visualization.asset_index", "Visualization previews require an asset index"))
        else:
            index_path = manifest_path.parent / asset_index_name
            index, index_issues = _load_json(index_path)
            issues.extend(index_issues)
            issues.extend(_require_schema(index, expected=VISUALIZATION_ASSET_INDEX_SCHEMA, target="visualization_asset_index"))
            checked_contracts["visualization_asset_index"] = VISUALIZATION_ASSET_INDEX_SCHEMA
            if int(index.get("asset_count") or 0) != int(visualization.get("asset_count") or 0):
                issues.append(_issue("asset_count_mismatch", "visualization_asset_index.asset_count", "Asset index count must match bundle visualization asset count"))
            if bool(index.get("contains_raw_dataframe")):
                issues.append(_issue("raw_dataframe_leak", "visualization_asset_index.contains_raw_dataframe", "Visualization assets must not expose raw dataframes"))

    if validation_report_path is not None:
        report_path = Path(validation_report_path)
        report, report_issues = _load_json(report_path)
        issues.extend(report_issues)
        issues.extend(_require_schema(report, expected=BUNDLE_VALIDATION_REPORT_SCHEMA, target="validation_report"))
        checked_contracts["validation_report"] = BUNDLE_VALIDATION_REPORT_SCHEMA
        if report.get("ok") is not True:
            issues.append(_issue("failed_validation_report", "validation_report.ok", "Validation report must be successful"))

    return ExportContractValidation(
        ok=not issues,
        schema=EXPORT_CONTRACT_SCHEMA,
        bundle_manifest=manifest_path,
        issues=tuple(issues),
        checked_contracts=checked_contracts,
    )


__all__ = [
    "BUNDLE_VALIDATION_REPORT_SCHEMA",
    "EXPORT_CONTRACT_SCHEMA",
    "ExportContractValidation",
    "PRESENTATION_BUNDLE_SCHEMA",
    "VISUALIZATION_ASSET_INDEX_SCHEMA",
    "validate_export_contract",
]
