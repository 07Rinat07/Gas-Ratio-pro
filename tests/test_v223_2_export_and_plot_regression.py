from __future__ import annotations

from time import sleep

import pandas as pd

from palettes.depth_tracks import build_depth_gas_tracks, build_depth_interpretation_track
from reports.background_export import BackgroundExportManager, ExportJobStatus


def test_depth_curves_are_lines_without_dense_markers() -> None:
    frame = pd.DataFrame({"depth": [1000.0, 1001.0, 1002.0], "c1": [0.1, 0.2, 0.15]})
    figure = build_depth_gas_tracks(frame)
    data_trace = next(trace for trace in figure.data if trace.name == "C1" and trace.x[0] is not None)
    assert data_trace.mode == "lines"


def test_interpretation_is_a_continuous_track_not_connected_scatter() -> None:
    frame = pd.DataFrame({
        "depth": [1000.0, 1001.0, 1002.0],
        "interpretation": ["Газовая залежь", "Газовая залежь", "Нефтяная залежь"],
    })
    figure = build_depth_interpretation_track(frame)
    assert figure.data[0].type == "heatmap"


def test_background_job_survives_manager_recreation() -> None:
    state: dict[str, object] = {}
    first = BackgroundExportManager(state)

    def work(report, check_cancelled):
        report(50, "working")
        sleep(0.03)
        check_cancelled()
        return b"ready"

    job = first.submit(project_id="default", request_signature="same", work=work)
    second = BackgroundExportManager(state)
    snapshot = next(item for item in second.list(project_id="default") if item.id == job.id)
    assert snapshot.status in {ExportJobStatus.PENDING, ExportJobStatus.RUNNING, ExportJobStatus.COMPLETED}

    for _ in range(100):
        snapshot = next(item for item in second.list(project_id="default") if item.id == job.id)
        if snapshot.terminal:
            break
        sleep(0.01)
    assert snapshot.status is ExportJobStatus.COMPLETED
    assert second.pop_result(job.id) == b"ready"
