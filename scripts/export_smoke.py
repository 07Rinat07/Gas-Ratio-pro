from __future__ import annotations

"""Reproducible smoke export command for professional report packages.

The command is intentionally small and deterministic. It builds one sample
PresentationModel from in-memory engineering data and exports PDF and DOCX
through the production renderers. This gives QA a fast way to verify
that renderer dependencies, Unicode fonts and manifests are ready before a user
exports a real LAS report.
"""

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from reports.hydrocarbon_report import build_hydrocarbon_report_payload
from reports.presentation_export import PresentationExportOptions, export_presentation_bundle_package


def build_sample_export_frame() -> pd.DataFrame:
    """Return deterministic multilingual gas-ratio data for export QA.

    The strings deliberately include Russian and Kazakh Cyrillic glyphs. PDF
    smoke export will fail with a clear renderer error if a Unicode-capable font
    is unavailable, which is exactly what the P0 QA step must expose early.
    """

    return pd.DataFrame(
        {
            "depth": [2148.2, 2149.0, 2155.0, 2156.0],
            "interpretation": ["Газовая залежь", "Газовая залежь", "Мұнай интервалы", "Мұнай интервалы"],
            "c1": [0.10, 0.20, 0.15, 0.12],
            "wh": [6.0, 7.0, 25.0, 26.0],
            "bh": [45.0, 44.0, 10.0, 11.0],
            "c1_c2": [80.0, 82.0, 6.0, 6.5],
            "oil_indicator": [0.04, 0.05, 0.20, 0.22],
            "lithology": ["Sandstone", "Sandstone", "Sandstone", "Sandstone"],
        }
    )


def run_export_smoke(output_dir: str | Path) -> dict[str, object]:
    """Export the sample report bundle and return a compact QA summary."""

    payload = build_hydrocarbon_report_payload(
        build_sample_export_frame(),
        source_label="export-smoke-sample.las",
        project_label="Gas Ratio Pro QA",
        depth_label="2148.2-2156.0 м",
        include_plot=False,
    )
    options = PresentationExportOptions(
        output_dir=output_dir,
        base_name="gas-ratio-export-smoke",
        include_figures=False,
        include_technical_appendix=False,
        overwrite=True,
    )
    # Bundle generation remains an internal release-QA compatibility path.
    # The HTML artifact is not exposed by the application or returned as a
    # user-selectable export format.
    result = export_presentation_bundle_package(payload.presentation_model, options=options)
    return {
        "ok": True,
        "profile": result.profile,
        "pdf": str(result.pdf_path),
        "docx": str(result.docx_path),
        "manifest": str(result.manifest_path),
        "table_titles": list(result.table_titles),
        "figure_count": result.figure_count,
    }



def main() -> int:
    parser = argparse.ArgumentParser(description="Run Gas Ratio Pro professional export smoke QA.")
    parser.add_argument("--output-dir", default="tmp/export-smoke", help="Directory for generated PDF/DOCX files.")
    args = parser.parse_args()
    summary = run_export_smoke(args.output_dir)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
