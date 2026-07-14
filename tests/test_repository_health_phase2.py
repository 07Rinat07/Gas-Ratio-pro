from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.diagnostics_center import build_diagnostics_center_snapshot
from core.repository_health import RepositoryHealthService
from core.runtime_service_registry import runtime_service_registry


def test_health_scan_reports_invalid_json_and_stale_temp(tmp_path: Path) -> None:
    (tmp_path / "ok.json").write_text('{"ok": true}', encoding="utf-8")
    (tmp_path / "broken.json").write_text('{broken', encoding="utf-8")
    temp = tmp_path / ".write.tmp"
    temp.write_text("temporary", encoding="utf-8")
    service = RepositoryHealthService(
        tmp_path, stale_temp_seconds=0, scan_ttl_seconds=0
    )

    snapshot = service.scan(force=True)

    assert snapshot.healthy is False
    assert snapshot.files_scanned == 3
    assert snapshot.json_files == 2
    assert {item.kind for item in snapshot.issues} == {"invalid_json", "stale_temp"}
    assert len(snapshot.repair_plan) == 2


def test_repair_quarantines_only_unchanged_explicit_target(tmp_path: Path) -> None:
    broken = tmp_path / "broken.json"
    broken.write_text("not-json", encoding="utf-8")
    service = RepositoryHealthService(tmp_path, scan_ttl_seconds=0)
    snapshot = service.scan(force=True)
    action = snapshot.repair_plan[0]

    result = service.apply_repair(action.action_id)

    assert result["status"] == "quarantined"
    assert not broken.exists()
    assert (tmp_path / result["destination"]).read_text(encoding="utf-8") == "not-json"


def test_stale_repair_action_is_rejected(tmp_path: Path) -> None:
    broken = tmp_path / "broken.json"
    broken.write_text("not-json", encoding="utf-8")
    service = RepositoryHealthService(tmp_path, scan_ttl_seconds=0)
    action = service.scan(force=True).repair_plan[0]
    broken.write_text("still-not-json-but-changed", encoding="utf-8")

    with pytest.raises(ValueError, match="missing or stale"):
        service.apply_repair(action.action_id)

    assert broken.exists()


def test_scan_is_bounded_and_reports_truncation(tmp_path: Path) -> None:
    for index in range(5):
        (tmp_path / f"{index}.json").write_text(json.dumps({"n": index}), encoding="utf-8")
    snapshot = RepositoryHealthService(tmp_path, max_files=2, scan_ttl_seconds=0).scan(force=True)

    assert snapshot.truncated is True
    assert snapshot.files_scanned == 2
    assert any(item.kind == "scan_truncated" for item in snapshot.issues)


def test_diagnostics_center_exposes_serializable_health_snapshot(tmp_path: Path) -> None:
    (tmp_path / "broken.json").write_text("not-json", encoding="utf-8")
    state: dict = {}
    registry = runtime_service_registry(state)
    registry.set(
        "repository_health_service",
        RepositoryHealthService(tmp_path, scan_ttl_seconds=0),
        scope="project",
    )

    snapshot = build_diagnostics_center_snapshot(state)

    assert snapshot["repository_health"]["issue_count"] == 1
    json.dumps(snapshot["repository_health"])
