from types import SimpleNamespace

import pandas as pd

from palettes.depth_tracks import build_depth_gas_tracks, build_depth_ratio_tracks, build_depth_pixler_tracks
from tests.visual_rebaseline_helpers import assert_visual_rebaseline


def _frame():
    return pd.DataFrame({
        'depth':[1000.0,1001.0,1002.0], 'c1':[1,2,3], 'c2':[2,3,4], 'c3':[3,4,5],
        'ic4':[1,1,2], 'nc4':[1,2,2], 'ic5':[1,1,1], 'nc5':[1,2,3],
        'wh':[10,20,30], 'bh':[5,6,7], 'ch':[2,3,4], 'bar2':[1,2,3],
        'c1_c2':[2,3,4], 'c1_c3':[4,5,6], 'c1_c4':[6,7,8], 'c1_c5':[8,9,10],
    })


def test_depth_graphs_share_focused_range_and_interval_overlays():
    overlay = SimpleNamespace(interval_id="HC-001", top_depth=1000.4, bottom_depth=1001.6, fluid_type="oil")
    snapshots = []
    for builder in (build_depth_gas_tracks, build_depth_ratio_tracks, build_depth_pixler_tracks):
        fig = builder(
            _frame(),
            depth_range=(1000.0, 1002.0),
            reservoir_intervals=(overlay,),
            selected_interval_id="HC-001",
        )
        marker = next(trace for trace in fig.data if getattr(trace, "name", "") == "Нефть")
        curve_names = []
        for trace in fig.data:
            name = str(getattr(trace, "name", "") or "")
            if getattr(trace, "mode", "") == "lines" and name and name not in curve_names:
                curve_names.append(name)
        snapshots.append({
            "builder": builder.__name__,
            "curve_names": curve_names,
            "depth_range": list(fig.layout.yaxis.range),
            "interval_marker": str(marker.name),
            "interval_marker_mode": str(marker.mode),
            "shape_count": len(fig.layout.shapes),
            "legend_y": float(fig.layout.legend.y),
        })

    assert_visual_rebaseline(
        "tests/test_depth_graph_focus_v222_10.py::test_depth_graphs_share_focused_range_and_interval_overlays",
        {"builders": snapshots},
    )

