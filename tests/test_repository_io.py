import json
from pathlib import Path

import pytest

from core.repository_io import AtomicJsonStore, RepositoryIOMetrics


def test_atomic_json_store_roundtrip_and_schema_validation(tmp_path: Path) -> None:
    metrics = RepositoryIOMetrics(max_events=10)
    store = AtomicJsonStore(repository="test", metrics=metrics)
    path = tmp_path / "nested" / "state.json"

    written = store.write(path, {"schema": "v1", "value": "данные"})
    loaded = store.read(path, expected_schema="v1")

    assert written == path.stat().st_size
    assert loaded["value"] == "данные"
    assert not tuple(path.parent.glob("*.tmp"))
    snapshot = metrics.snapshot()
    assert snapshot.writes == 1
    assert snapshot.reads == 1
    assert snapshot.failures == 0
    assert snapshot.bytes_written == written


def test_atomic_json_store_records_failures_without_payload_retention(tmp_path: Path) -> None:
    metrics = RepositoryIOMetrics(max_events=10)
    store = AtomicJsonStore(repository="test", metrics=metrics)
    path = tmp_path / "broken.json"
    path.write_text("{broken", encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        store.read(path)

    snapshot = metrics.snapshot()
    assert snapshot.failures == 1
    assert snapshot.events[-1].error_type == "JSONDecodeError"
    assert snapshot.events[-1].path_name == "broken.json"
    assert not hasattr(snapshot.events[-1], "payload")


def test_repository_io_metrics_are_bounded() -> None:
    metrics = RepositoryIOMetrics(max_events=2)
    for index in range(3):
        metrics.record(
            repository="repo", operation="read", status="success",
            duration_ms=index + 1, path=f"{index}.json",
        )

    snapshot = metrics.snapshot(event_limit=10)
    assert snapshot.reads == 2
    assert [item.path_name for item in snapshot.events] == ["1.json", "2.json"]
