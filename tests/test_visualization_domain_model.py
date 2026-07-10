from __future__ import annotations

from services.visualization_domain_model import VisualizationDomainModelAdapter


def test_domain_model_adapter_normalizes_source_payload_without_raw_tables() -> None:
    payload = {
        "source_type": "las",
        "source_id": "well-demo",
        "depth_curve": "DEPT",
        "depth_unit": "m",
        "depth_range": {"start": 1000.0, "stop": 1001.0, "step": 0.5},
        "tracks": [{"id": "track.gamma", "title": "Gamma", "width": 1.25}],
        "curves": [
            {
                "mnemonic": "GR",
                "track_id": "track.gamma",
                "unit": "API",
                "point_count": 3,
                "sampled_count": 3,
                "points": [
                    {"depth": 1000.0, "value": 80.0},
                    {"depth": 1000.5, "value": 82.0},
                    {"depth": 1001.0, "value": 85.0},
                ],
            }
        ],
        "overlays": [
            {
                "id": "interval.demo",
                "top": 1000.5,
                "base": 1001.0,
                "label": "Gas",
                "fluid_type": "gas",
                "track_scope": ["track.gamma"],
            }
        ],
        "quality_flags": ["sampled"],
        "visible_tracks": ["track.gamma"],
    }

    model = VisualizationDomainModelAdapter().from_payload(
        payload,
        source_type="las",
        source_id="well-demo",
    )
    result = model.to_dict()

    assert result["schema"] == "visualization.domain.model"
    assert result["source_type"] == "las"
    assert result["source_id"] == "well-demo"
    assert result["tracks"][0]["id"] == "track.gamma"
    assert result["curves"][0]["mnemonic"] == "GR"
    assert result["intervals"][0]["fluid_type"] == "gas"
    assert result["raw_dataframe_included"] is False
    assert "raw_dataframe" not in result["curves"][0]


def test_domain_model_converts_to_engine_payload() -> None:
    model = VisualizationDomainModelAdapter().from_payload(
        {
            "depth_curve": "DEPT",
            "depth_unit": "m",
            "tracks": [{"id": "track.gas", "title": "Gas"}],
            "curves": [{"mnemonic": "C1", "track_id": "track.gas", "points": []}],
            "overlays": [],
            "legend": [{"label": "Methane"}],
        }
    )

    engine_payload = model.to_engine_payload()

    assert engine_payload["depth_curve"] == "DEPT"
    assert engine_payload["tracks"][0]["id"] == "track.gas"
    assert engine_payload["curves"][0]["mnemonic"] == "C1"
    assert engine_payload["legend"] == [{"label": "Methane"}]
