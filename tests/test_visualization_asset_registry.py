from __future__ import annotations

import json
from pathlib import Path

from services.visualization_asset_registry import VisualizationAssetRegistry
from services.visualization_scene_pipeline import VisualizationScenePipeline


def _payload():
    return {
        "source_type": "las",
        "source_id": "asset-registry-demo",
        "depth_curve": "DEPT",
        "depth_unit": "m",
        "depth_range": {"start": 1000.0, "stop": 1002.0, "step": 1.0},
        "tracks": [{"id": "track.gamma", "title": "Гамма", "width": 1.0}],
        "curves": [
            {
                "id": "curve.GR",
                "track_id": "track.gamma",
                "mnemonic": "GR",
                "unit": "API",
                "scale_type": "linear",
                "range": {"min": 0, "max": 150},
                "points": [
                    {"depth": 1000.0, "value": 45.0},
                    {"depth": 1001.0, "value": 60.0},
                    {"depth": 1002.0, "value": 72.0},
                ],
            }
        ],
        "overlays": [],
    }


def test_asset_registry_writes_svg_pdf_and_contract_assets(tmp_path: Path):
    pipeline = VisualizationScenePipeline().run(_payload()).to_dict()
    result = VisualizationAssetRegistry().build(pipeline, output_dir=tmp_path, base_name="well-a")
    data = result.to_dict()

    assert data["ok"] is True
    assert data["asset_count"] == 4
    assert len(data["geometry_signature"]) == 64
    assert data["single_pipeline_source"] is True
    assert {item["format"] for item in data["assets"]} == {"svg", "pdf", "json"}

    for asset in data["assets"]:
        path = tmp_path / asset["path"]
        assert path.exists()
        assert path.stat().st_size == asset["size_bytes"]
        assert len(asset["sha256"]) == 64
        assert asset["geometry_signature"] == data["geometry_signature"]

    assert (tmp_path / "assets/well-a-preview_svg.svg").read_text(encoding="utf-8").startswith("<svg")
    assert (tmp_path / "assets/well-a-preview_pdf.pdf").read_bytes().startswith(b"%PDF-")

    registry = json.loads((tmp_path / "well-a.visualization-assets.json").read_text(encoding="utf-8"))
    assert registry["geometry_signature"] == data["geometry_signature"]
    assert registry["asset_count"] == 4


def test_asset_registry_rejects_invalid_pipeline(tmp_path: Path):
    result = VisualizationAssetRegistry().build({}, output_dir=tmp_path)

    assert result.ok is False
    assert "visualization_asset_registry_unsupported_pipeline_schema" in result.issues
    assert "visualization_asset_registry_render_model_missing" in result.issues
