from __future__ import annotations

import json
from pathlib import Path

from core.repository_io import AtomicJsonStore, RepositoryIOMetrics


def test_recover_pending_transaction_restores_original_files(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    first = root / "first.json"
    second = root / "second.json"
    first.write_text('{"value": "before"}\n', encoding="utf-8")

    tx_dir = root / ".repository_transactions" / "deadbeef"
    tx_dir.mkdir(parents=True)
    (tx_dir / "backup-0000.bin").write_bytes(first.read_bytes())
    first.write_text('{"value": "after"}\n', encoding="utf-8")
    second.write_text('{"created": true}\n', encoding="utf-8")
    manifest = {
        "schema": "gas-ratio-pro/repository-transaction/v1",
        "transaction_id": "deadbeef",
        "repository": "test",
        "root": str(root.resolve()),
        "status": "applying",
        "entries": [
            {
                "operation": "write",
                "target": str(first.resolve()),
                "existed": True,
                "backup": "backup-0000.bin",
                "staged": "staged-0000.json",
            },
            {
                "operation": "write",
                "target": str(second.resolve()),
                "existed": False,
                "backup": "",
                "staged": "staged-0001.json",
            },
        ],
    }
    (tx_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    metrics = RepositoryIOMetrics()
    result = AtomicJsonStore(repository="test", metrics=metrics).recover_transactions(root)

    assert result == {"recovered": 1, "failures": 0}
    assert json.loads(first.read_text(encoding="utf-8"))["value"] == "before"
    assert not second.exists()
    assert not tx_dir.exists()
    snapshot = metrics.mutation_snapshot()
    assert snapshot["recovery_count"] == 1
    assert snapshot["recovery_failures"] == 0


def test_committed_transaction_journal_is_cleaned_without_rollback(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    target = root / "data.json"
    target.write_text('{"value": "committed"}\n', encoding="utf-8")
    tx_dir = root / ".repository_transactions" / "committed"
    tx_dir.mkdir(parents=True)
    manifest = {
        "schema": "gas-ratio-pro/repository-transaction/v1",
        "transaction_id": "committed",
        "repository": "test",
        "root": str(root.resolve()),
        "status": "committed",
        "entries": [],
    }
    (tx_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    result = AtomicJsonStore(repository="test").recover_transactions(root)

    assert result == {"recovered": 0, "failures": 0}
    assert json.loads(target.read_text(encoding="utf-8"))["value"] == "committed"
    assert not tx_dir.exists()


def test_transaction_leaves_no_recovery_journal_after_success(tmp_path: Path) -> None:
    root = tmp_path / "project"
    store = AtomicJsonStore(repository="test")
    tx = store.transaction()
    tx.write(root / "a.json", {"a": 1})
    tx.write(root / "nested" / "b.json", {"b": 2})

    result = tx.commit()

    assert result.status == "committed"
    assert not (root / ".repository_transactions").exists()
