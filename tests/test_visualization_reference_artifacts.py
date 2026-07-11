from __future__ import annotations

import json
from pathlib import Path

from services.visualization_reference_artifacts import VisualizationReferenceArtifactService


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "visualization"
ARTIFACT_DIR = FIXTURE_DIR / "reference_artifacts"
FIXTURES = [
    FIXTURE_DIR / "reference_multitrack_linear.json",
    FIXTURE_DIR / "reference_multitrack_unicode.json",
    FIXTURE_DIR / "reference_multitrack_overlays.json",
]


def test_committed_reference_artifacts_pass_integrity_and_structure_checks():
    manifest = VisualizationReferenceArtifactService().verify(ARTIFACT_DIR)

    assert manifest.ok is True
    assert [item.name for item in manifest.entries] == [path.stem for path in FIXTURES]
    assert all(item.geometry_signature for item in manifest.entries)
    assert all(item.page_count == 1 for item in manifest.entries)
    assert all(item.font_name for item in manifest.entries)


def test_regenerated_reference_artifacts_match_approved_structural_baseline(tmp_path):
    service = VisualizationReferenceArtifactService()
    approved = service.verify(ARTIFACT_DIR)
    generated = service.generate(FIXTURES, tmp_path)

    assert generated.ok is True
    assert [service.structural_signature(item) for item in generated.entries] == [
        service.structural_signature(item) for item in approved.entries
    ]


def test_unicode_reference_svg_preserves_engineering_labels():
    svg = (ARTIFACT_DIR / "reference_multitrack_unicode.svg").read_text(encoding="utf-8")

    assert "Литология" in svg
    assert "Газовый каротаж" in svg
    assert "Метан C1" in svg
    assert "Газонасыщенный интервал" in svg


def test_reference_manifest_is_renderer_neutral_and_machine_readable():
    payload = json.loads((ARTIFACT_DIR / "manifest.json").read_text(encoding="utf-8"))

    assert payload["schema"] == "visualization.reference-artifacts.manifest"
    assert payload["version"] == "1.0"
    assert payload["renderer_neutral"] is True
    assert payload["ok"] is True
    assert len(payload["entries"]) == 3
