from dataclasses import dataclass
import numpy as np
import pandas as pd

from app.visualization_v3.composite_v4 import build_composite_log_v4


@dataclass
class I:
    top: float
    base: float
    fluid: str
    confidence: float
    id: str


def frame():
    depth = np.arange(40.0, 2020.0, 0.2)
    active = (depth >= 1330.0)
    c1 = np.where(active, 0.02 + 0.01*np.sin(depth/13), 0.0)
    return pd.DataFrame({
        'depth': depth,
        'c1': c1,
        'c2': np.where(active, c1/4, 0.0),
        'c3': np.where(active, c1/8, 0.0),
        'ic4': np.where(active, c1/20, 0.0),
        'nc4': np.where(active, c1/18, 0.0),
        'ic5': np.where(active, c1/35, 0.0),
        'nc5': np.where(active, c1/30, 0.0),
        'wh': np.where(active, 20 + 5*np.sin(depth/20), 0.0),
    })


def intervals():
    return [
        I(1335.8, 1400.6, 'Газоконденсат', 0.91, 'HC-001'),
        I(1485.6, 1539.2, 'Нефть', 0.92, 'HC-002'),
        I(1658.8, 1691.6, 'Газ', 0.90, 'HC-003'),
        I(1805.8, 1889.6, 'Газ', 0.94, 'HC-004'),
    ]


def test_overview_crops_leading_empty_depth_and_draws_zone_cards():
    result = build_composite_log_v4(frame(), intervals=intervals(), report_kind='overview', target_width=4000, height=2600)
    assert result.depth_start > 1250
    assert result.depth_stop >= 1889.6
    assert 'HC-001' in result.svg
    assert 'Газоконденсат' in result.svg
    assert 'Переходная/прочее' in result.svg
    assert 'fill-opacity="0.18"' in result.svg


def test_detail_does_not_apply_overview_crop():
    result = build_composite_log_v4(frame(), intervals=intervals()[:1], report_kind='detail', target_width=4000, height=2600)
    assert result.depth_start == 40.0
