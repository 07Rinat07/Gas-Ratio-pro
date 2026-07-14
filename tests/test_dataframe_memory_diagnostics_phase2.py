from __future__ import annotations

import pandas as pd

from core.application_state import ApplicationStateController
from core.dataframe_runtime_cache import DataframeRuntimeCache
from core.diagnostics_center import build_diagnostics_center_snapshot


def test_diagnostics_center_reports_dataframe_memory_without_values() -> None:
    state: dict[str, object] = {}
    controller = ApplicationStateController(state)
    cache = controller.ensure_runtime_service(
        "dataframe_runtime_cache",
        lambda: DataframeRuntimeCache(max_bytes=1024 * 1024),
        expected_type=DataframeRuntimeCache,
        scope="project",
    )
    frame = pd.DataFrame({"value": [1.0, 2.0, 3.0]})
    signature = cache.signature(frame, revision=1, builder=lambda _: "sig")
    cache.screen_sample(
        frame,
        source_signature=signature,
        depth_range=(1.0, 3.0),
        max_rows=3,
        sampler=lambda source, max_rows: source.head(max_rows).copy(),
    )

    snapshot = build_diagnostics_center_snapshot(state)
    memory = snapshot["dataframe_memory"]

    assert memory["sample_entries"] == 1
    assert memory["sample_bytes"] > 0
    assert memory["max_sample_bytes"] == 1024 * 1024
    assert snapshot["runtime"]["service_scopes"]["dataframe_runtime_cache"] == "project"
    assert "_samples" not in repr(snapshot)
