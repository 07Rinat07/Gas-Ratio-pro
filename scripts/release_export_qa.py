from __future__ import annotations

"""Release QA entry point for professional presentation exports.

The command runs the production multilingual smoke bundle and validates the
bundle manifest after files are written. It is designed for release checks: one
command proves that HTML, PDF and DOCX exporters are importable, Unicode-capable
and produce an auditable bundle manifest.
"""

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from reports.presentation_export import validate_presentation_bundle_export, write_presentation_bundle_validation_report
from reports.presentation_export_contract import validate_export_contract
from scripts.export_smoke import run_export_smoke


def _read_visualization_asset_summary(manifest_path: str | Path) -> dict[str, object]:
    """Return a compact release QA summary for visualization bundle assets."""

    manifest = Path(manifest_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    visualization = payload.get("visualization", {}) if isinstance(payload, dict) else {}
    if not isinstance(visualization, dict):
        visualization = {}
    index_name = str(visualization.get("asset_index") or "").strip()
    summary: dict[str, object] = {
        "preview_count": int(visualization.get("preview_count") or 0),
        "asset_count": int(visualization.get("asset_count") or 0),
        "asset_index": index_name,
        "asset_index_ready": False,
    }
    if not index_name:
        return summary
    index_path = manifest.parent / index_name
    if not index_path.exists():
        return summary
    index = json.loads(index_path.read_text(encoding="utf-8"))
    summary.update(
        {
            "asset_index_ready": True,
            "index_schema": index.get("schema", ""),
            "indexed_asset_count": int(index.get("asset_count") or 0),
            "total_size_bytes": int(index.get("total_size_bytes") or 0),
            "formats": list(index.get("formats") or []),
            "contains_raw_dataframe": bool(index.get("contains_raw_dataframe")),
        }
    )
    return summary


def run_release_export_qa(output_dir: str | Path) -> dict[str, object]:
    """Run smoke export and validate the resulting bundle manifest."""

    smoke = run_export_smoke(output_dir)
    validation = validate_presentation_bundle_export(smoke["manifest"])
    validation_report_path = write_presentation_bundle_validation_report(validation)
    visualization_assets = _read_visualization_asset_summary(smoke["manifest"])
    contract = validate_export_contract(smoke["manifest"], validation_report_path=validation_report_path)
    return {
        "ok": bool(smoke.get("ok")) and validation.ok and contract.ok,
        "smoke": smoke,
        "visualization_assets": visualization_assets,
        "contract": contract.to_dict(),
        "validation": {
            "ok": validation.ok,
            "manifest": str(validation.manifest_path),
            "files_checked": [str(path) for path in validation.files_checked],
            "missing_files": list(validation.missing_files),
            "empty_files": list(validation.empty_files),
            "consistency": validation.consistency,
            "issue_count": validation.issue_count,
            "validation_report": str(validation_report_path),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Gas Ratio Pro release export QA.")
    parser.add_argument("--output-dir", default="tmp/release-export-qa", help="Directory for generated QA artifacts.")
    args = parser.parse_args()
    summary = run_release_export_qa(args.output_dir)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
