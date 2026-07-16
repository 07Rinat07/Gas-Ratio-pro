from core.diagnostics_center import build_diagnostics_center_snapshot
from core.project_open_diagnostics import ProjectOpenDiagnostics
from core.runtime_service_registry import runtime_service_registry


def test_project_open_diagnostics_are_bounded_and_classify_slow_events() -> None:
    diagnostics = ProjectOpenDiagnostics(max_events=2, budget_ms=10.0)
    for index, total in enumerate((4.0, 8.0, 12.0), start=1):
        diagnostics.record(
            project_id=f"p{index}",
            project_load_ms=1.0,
            recent_project_ms=1.0,
            workspace_open_ms=1.0,
            navigation_ms=1.0,
            total_ms=total,
        )

    snapshot = diagnostics.snapshot(limit=10)

    assert snapshot["event_count"] == 2
    assert snapshot["slow_count"] == 1
    assert [item["project_id"] for item in snapshot["events"]] == ["p2", "p3"]
    assert snapshot["latest"]["status"] == "slow"


def test_diagnostics_center_exposes_project_open_profile() -> None:
    state: dict[str, object] = {}
    diagnostics = runtime_service_registry(state).set(
        "project_open_diagnostics", ProjectOpenDiagnostics(), scope="session"
    )
    diagnostics.record(
        project_id="project-a",
        project_load_ms=2.0,
        recent_project_ms=1.0,
        workspace_open_ms=3.0,
        navigation_ms=4.0,
        total_ms=10.0,
    )

    snapshot = build_diagnostics_center_snapshot(state)

    assert snapshot["project_open"]["event_count"] == 1
    assert snapshot["project_open"]["latest"]["project_id"] == "project-a"
