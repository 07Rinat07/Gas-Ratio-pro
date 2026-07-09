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

from reports.presentation_export import validate_presentation_bundle_export
from scripts.export_smoke import run_export_smoke


def run_release_export_qa(output_dir: str | Path) -> dict[str, object]:
    """Run smoke export and validate the resulting bundle manifest."""

    smoke = run_export_smoke(output_dir)
    validation = validate_presentation_bundle_export(smoke["manifest"])
    return {
        "ok": bool(smoke.get("ok")) and validation.ok,
        "smoke": smoke,
        "validation": {
            "ok": validation.ok,
            "manifest": str(validation.manifest_path),
            "files_checked": [str(path) for path in validation.files_checked],
            "missing_files": list(validation.missing_files),
            "empty_files": list(validation.empty_files),
            "consistency": validation.consistency,
            "issue_count": validation.issue_count,
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
