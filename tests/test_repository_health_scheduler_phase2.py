from __future__ import annotations

import json
from pathlib import Path

from core.diagnostics_center import build_diagnostics_center_snapshot
from core.repository_health import RepositoryHealthService
from core.repository_health_scheduler import RepositoryHealthScheduler
from core.runtime_service_registry import runtime_service_registry


def test_scheduler_runs_only_when_due(tmp_path: Path) -> None:
    (tmp_path / "ok.json").write_text('{"ok": true}', encoding="utf-8")
    scheduler = RepositoryHealthScheduler(
        RepositoryHealthService(tmp_path, scan_ttl_seconds=0), interval_seconds=60
    )

    first = scheduler.tick(now=100.0)
    second = scheduler.tick(now=120.0)
    state = scheduler.snapshot(now=120.0)

    assert first is second
    assert state["scan_count"] == 1
    assert state["skipped_count"] >= 1


def test_readiness_reports_blocking_json_corruption(tmp_path: Path) -> None:
    (tmp_path / "broken.json").write_text("{broken", encoding="utf-8")
    scheduler = RepositoryHealthScheduler(
        RepositoryHealthService(tmp_path, scan_ttl_seconds=0), interval_seconds=60
    )

    readiness = scheduler.readiness(scheduler.tick(force=True)).to_dict()

    assert readiness["score"] < 90
    assert readiness["status"] in {"attention", "blocked"}
    assert readiness["blocking_issues"] == 1


def test_diagnostics_exposes_scheduled_health_and_readiness(tmp_path: Path) -> None:
    (tmp_path / "ok.json").write_text('{"ok": true}', encoding="utf-8")
    state: dict = {}
    registry = runtime_service_registry(state)
    registry.set(
        "repository_health_service",
        RepositoryHealthScheduler(
            RepositoryHealthService(tmp_path, scan_ttl_seconds=0), interval_seconds=60
        ),
        scope="project",
    )

    health = build_diagnostics_center_snapshot(state)["repository_health"]

    assert health["schedule"]["enabled"] is True
    assert health["readiness"]["score"] == 100
    json.dumps(health)
