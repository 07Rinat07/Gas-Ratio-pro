from types import SimpleNamespace

import pandas as pd

from palettes.depth_tracks import build_depth_gas_tracks, build_depth_ratio_tracks, build_depth_pixler_tracks


def _frame():
    return pd.DataFrame({
        'depth':[1000.0,1001.0,1002.0], 'c1':[1,2,3], 'c2':[2,3,4], 'c3':[3,4,5],
        'ic4':[1,1,2], 'nc4':[1,2,2], 'ic5':[1,1,1], 'nc5':[1,2,3],
        'wh':[10,20,30], 'bh':[5,6,7], 'ch':[2,3,4], 'bar2':[1,2,3],
        'c1_c2':[2,3,4], 'c1_c3':[4,5,6], 'c1_c4':[6,7,8], 'c1_c5':[8,9,10],
    })


def test_depth_graphs_share_focused_range_and_interval_overlays():
    overlay = SimpleNamespace(interval_id='HC-001', top_depth=1000.4, bottom_depth=1001.6, fluid_type='oil')
    for builder in (build_depth_gas_tracks, build_depth_ratio_tracks, build_depth_pixler_tracks):
        fig = builder(_frame(), depth_range=(1000.0, 1002.0), reservoir_intervals=(overlay,), selected_interval_id='HC-001')
        assert tuple(fig.layout.yaxis.range) == (1002.0, 1000.0)
        assert len(fig.layout.shapes) >= 3
        assert any(getattr(trace, 'name', '') == 'Нефть' for trace in fig.data)
        assert any(getattr(trace, 'mode', '') == 'lines+markers' for trace in fig.data)
        assert fig.layout.legend.y > 1
