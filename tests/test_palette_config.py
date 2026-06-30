from __future__ import annotations

import json

import pandas as pd
import pytest

from palettes.config import load_palette_config
from palettes.ternary import build_ternary_palette


def test_load_palette_config_from_json(tmp_path):
    config_path = tmp_path / "palettes.json"
    config_path.write_text(
        json.dumps(
            {
                "version": "test",
                "notice": "test notice",
                "pixler": {
                    "zones": [
                        {
                            "name": "Zone A",
                            "y_min": 1,
                            "y_max": 10,
                            "color": "rgba(1, 2, 3, 0.1)",
                        }
                    ]
                },
                "ternary": {
                    "regions": [
                        {
                            "name": "Region A",
                            "a": [0.6, 0.8, 0.6],
                            "b": [0.2, 0.1, 0.3],
                            "c": [0.2, 0.1, 0.1],
                            "color": "rgba(1, 2, 3, 0.1)",
                        }
                    ]
                },
            }
        ),
        encoding="utf-8",
    )

    config = load_palette_config(config_path)

    assert config.version == "test"
    assert config.notice == "test notice"
    assert config.pixler_zones[0].name == "Zone A"
    assert config.ternary_regions[0].name == "Region A"


def test_invalid_pixler_zone_is_rejected(tmp_path):
    config_path = tmp_path / "palettes.json"
    config_path.write_text(
        json.dumps(
            {
                "pixler": {
                    "zones": [
                        {
                            "name": "Broken",
                            "y_min": 10,
                            "y_max": 1,
                            "color": "rgba(1, 2, 3, 0.1)",
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="0 < y_min < y_max"):
        load_palette_config(config_path)


def test_ternary_regions_are_rendered():
    config = load_palette_config()
    row = pd.Series({"c2_sumc": 0.5, "c3_sumc": 0.3, "nc4_sumc": 0.2})

    fig = build_ternary_palette(row, regions=config.ternary_regions)

    assert len(fig.data) == len(config.ternary_regions) + 1
