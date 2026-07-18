from pathlib import Path

import pandas as pd

from core.physical_print_profiles import build_user_physical_print_profile
from services.print_center_acceptance import ProfessionalPrintCenterAcceptanceRunner


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "depth": [1000.0, 1001.0, 1002.0, 1003.0],
            "GR": [10.0, 20.0, 30.0, 25.0],
            "C1": [1.0, 2.0, 3.0, 2.5],
            "C2": [0.2, 0.4, 0.7, 0.5],
            "C3": [0.1, 0.2, 0.4, 0.3],
            "RT": [100.0, 200.0, 300.0, 250.0],
            "NPHI": [0.20, 0.25, 0.30, 0.28],
            "X": [4.0, 5.0, 6.0, 5.5],
            "interpretation": ["Газовая залежь"] * 4,
            "wh": [8.0, 9.0, 10.0, 11.0],
            "bh": [40.0, 39.0, 38.0, 37.0],
            "c1_c2": [60.0, 62.0, 64.0, 66.0],
            "oil_indicator": [0.05, 0.06, 0.07, 0.08],
            "lithology": ["Sandstone"] * 4,
        }
    )


def test_professional_print_center_full_user_acceptance_path(tmp_path: Path):
    profile = build_user_physical_print_profile(
        name="Acceptance A4 portrait",
        page_size="A4",
        orientation="portrait",
        dpi=96,
        max_tracks_per_page=3,
    )
    result = ProfessionalPrintCenterAcceptanceRunner().run(
        _frame(),
        output_dir=tmp_path / "exports",
        profile=profile,
        profile_store_path=tmp_path / "profiles.json",
        project_id="acceptance-project",
        source_id="well-a",
        locale="en",
        curve_limit=10,
    )

    assert result.ok is True
    assert result.page_count >= 2
    assert result.profile_id == profile.id
    assert result.parity_gate_id
    assert result.geometry_signature
    assert all(result.checks.values())
    assert {artifact.kind for artifact in result.artifacts} >= {
        "html", "pdf", "docx", "svg", "png", "bundle_manifest", "acceptance_report"
    }
    assert (tmp_path / "exports" / "print-center-acceptance-report.json").exists()


def test_pdf_preview_raster_scales_to_actual_report_frame(tmp_path: Path):
    """Regression for portrait physical pages embedded in a landscape report."""

    profile = build_user_physical_print_profile(
        name="Mixed orientation acceptance",
        page_size="A4",
        orientation="portrait",
        dpi=96,
        max_tracks_per_page=3,
    )
    result = ProfessionalPrintCenterAcceptanceRunner().run(
        _frame(),
        output_dir=tmp_path / "exports",
        profile=profile,
        profile_store_path=tmp_path / "profiles.json",
        curve_limit=10,
    )
    assert result.checks["pdf_is_valid"] is True
    assert "document_bundle_export_failed:LayoutError" not in result.issues
