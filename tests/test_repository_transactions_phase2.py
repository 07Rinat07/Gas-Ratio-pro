from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.repository_io import AtomicJsonStore, RepositoryIOMetrics


def test_transaction_commits_multiple_files_with_one_mutation(tmp_path: Path) -> None:
    metrics = RepositoryIOMetrics()
    events: list[dict[str, object]] = []
    metrics.subscribe_mutations("test", events.append)
    store = AtomicJsonStore(repository="test-repository", metrics=metrics)
    first = tmp_path / "data" / "projects" / "p1" / "first.json"
    second = tmp_path / "data" / "projects" / "p1" / "second.json"

    tx = store.transaction()
    tx.write(first, {"value": 1})
    tx.write(second, {"value": 2})
    result = tx.commit()

    assert json.loads(first.read_text(encoding="utf-8"))["value"] == 1
    assert json.loads(second.read_text(encoding="utf-8"))["value"] == 2
    assert result.status == "committed"
    assert result.change_count == 2
    assert len(events) == 1
    assert events[0]["operation"] == "transaction"
    assert events[0]["project_id"] == "p1"
    assert events[0]["change_count"] == 2
    assert events[0]["transaction_id"] == result.transaction_id

    snapshot = metrics.mutation_snapshot()
    assert snapshot["mutation_count"] == 1
    assert snapshot["transaction_count"] == 1
    assert snapshot["transaction_failures"] == 0


def test_transaction_rolls_back_applied_files_on_commit_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    metrics = RepositoryIOMetrics()
    store = AtomicJsonStore(repository="test-repository", metrics=metrics)
    first = tmp_path / "data" / "projects" / "p1" / "first.json"
    second = tmp_path / "data" / "projects" / "p1" / "second.json"
    first.parent.mkdir(parents=True)
    first.write_text('{"value": "original-first"}\n', encoding="utf-8")
    second.write_text('{"value": "original-second"}\n', encoding="utf-8")

    import core.repository_io as repository_io

    real_replace = repository_io.os.replace
    calls = 0

    def fail_second_replace(source: object, destination: object) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated commit failure")
        real_replace(source, destination)

    monkeypatch.setattr(repository_io.os, "replace", fail_second_replace)

    tx = store.transaction()
    tx.write(first, {"value": "new-first"})
    tx.write(second, {"value": "new-second"})
    with pytest.raises(OSError, match="simulated commit failure"):
        tx.commit()

    assert json.loads(first.read_text(encoding="utf-8"))["value"] == "original-first"
    assert json.loads(second.read_text(encoding="utf-8"))["value"] == "original-second"
    snapshot = metrics.mutation_snapshot()
    assert snapshot["mutation_count"] == 0
    assert snapshot["transaction_count"] == 1
    assert snapshot["transaction_failures"] == 1
    assert snapshot["last_transaction"]["status"] == "rolled_back"


def test_transaction_rejects_duplicate_destinations_without_changes(tmp_path: Path) -> None:
    store = AtomicJsonStore(repository="test-repository")
    target = tmp_path / "same.json"
    target.write_text('{"value": "original"}\n', encoding="utf-8")

    tx = store.transaction()
    tx.write(target, {"value": 1})
    tx.write(target, {"value": 2})

    with pytest.raises(ValueError, match="duplicate destination"):
        tx.commit()
    assert json.loads(target.read_text(encoding="utf-8"))["value"] == "original"


def test_transaction_context_manager_commits(tmp_path: Path) -> None:
    store = AtomicJsonStore(repository="test-repository")
    target = tmp_path / "context.json"
    with store.transaction() as tx:
        tx.write(target, {"ok": True})
    assert json.loads(target.read_text(encoding="utf-8")) == {"ok": True}
