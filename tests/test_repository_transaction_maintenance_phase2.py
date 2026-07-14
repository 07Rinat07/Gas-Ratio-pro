from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from core.repository_io import AtomicJsonStore, RepositoryIOMetrics


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _write_manifest(directory: Path, payload: dict) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "manifest.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )


def test_list_and_inspect_recoverable_quarantined_transaction(tmp_path: Path) -> None:
    target = tmp_path / "data.json"
    original = b'{"value": 1}\n'
    target.write_bytes(b'{"value": 2}\n')
    transaction_id = "abc123"
    directory = tmp_path / ".repository_transactions_quarantine" / transaction_id
    directory.mkdir(parents=True)
    (directory / "backup-0000.bin").write_bytes(original)
    _write_manifest(directory, {
        "schema": "gas-ratio-pro/repository-transaction/v2",
        "transaction_id": transaction_id,
        "repository": "test",
        "root": str(tmp_path.resolve()),
        "status": "applying",
        "created_at": 1.0,
        "entries": [{
            "operation": "write",
            "target": str(target.resolve()),
            "existed": True,
            "backup": "backup-0000.bin",
            "staged": "staged-0000.json",
            "before_sha256": _sha(original),
            "after_sha256": "",
        }],
    })

    store = AtomicJsonStore(repository="test")
    rows = store.list_transaction_journals(tmp_path)

    assert len(rows) == 1
    assert rows[0]["location"] == "quarantine"
    assert rows[0]["recoverable"] is True
    assert rows[0]["issues"] == []


def test_recover_quarantined_transaction_restores_original_file(tmp_path: Path) -> None:
    target = tmp_path / "data.json"
    original = b'{"value": 1}\n'
    target.write_bytes(b'{"value": 2}\n')
    transaction_id = "recover-me"
    directory = tmp_path / ".repository_transactions_quarantine" / transaction_id
    directory.mkdir(parents=True)
    (directory / "backup-0000.bin").write_bytes(original)
    _write_manifest(directory, {
        "schema": "gas-ratio-pro/repository-transaction/v2",
        "transaction_id": transaction_id,
        "repository": "test",
        "root": str(tmp_path.resolve()),
        "status": "applying",
        "created_at": 1.0,
        "entries": [{
            "operation": "write",
            "target": str(target.resolve()),
            "existed": True,
            "backup": "backup-0000.bin",
            "staged": "staged-0000.json",
            "before_sha256": _sha(original),
            "after_sha256": "",
        }],
    })
    metrics = RepositoryIOMetrics()
    store = AtomicJsonStore(repository="test", metrics=metrics)

    result = store.recover_quarantined_transaction(tmp_path, transaction_id)

    assert result["recovered"] is True
    assert result["cleaned"] is True
    assert target.read_bytes() == original
    assert not directory.exists()
    assert metrics.mutation_snapshot()["recovery_count"] == 1


def test_recover_rejects_corrupt_backup_without_touching_target(tmp_path: Path) -> None:
    target = tmp_path / "data.json"
    current = b'{"value": 2}\n'
    target.write_bytes(current)
    transaction_id = "corrupt"
    directory = tmp_path / ".repository_transactions_quarantine" / transaction_id
    directory.mkdir(parents=True)
    (directory / "backup-0000.bin").write_bytes(b"corrupt")
    _write_manifest(directory, {
        "schema": "gas-ratio-pro/repository-transaction/v2",
        "transaction_id": transaction_id,
        "repository": "test",
        "root": str(tmp_path.resolve()),
        "status": "applying",
        "created_at": 1.0,
        "entries": [{
            "operation": "write",
            "target": str(target.resolve()),
            "existed": True,
            "backup": "backup-0000.bin",
            "before_sha256": _sha(b"expected"),
            "after_sha256": "",
        }],
    })
    store = AtomicJsonStore(repository="test")

    with pytest.raises(ValueError, match="not safe"):
        store.recover_quarantined_transaction(tmp_path, transaction_id)

    assert target.read_bytes() == current
    assert directory.exists()


def test_cleanup_only_removes_old_valid_committed_journals(tmp_path: Path) -> None:
    target = tmp_path / "data.json"
    payload = b'{"value": 3}\n'
    target.write_bytes(payload)
    journal = tmp_path / ".repository_transactions" / "committed-one"
    _write_manifest(journal, {
        "schema": "gas-ratio-pro/repository-transaction/v2",
        "transaction_id": "committed-one",
        "repository": "test",
        "root": str(tmp_path.resolve()),
        "status": "committed",
        "created_at": 1.0,
        "entries": [{
            "operation": "write",
            "target": str(target.resolve()),
            "existed": True,
            "backup": "",
            "before_sha256": "",
            "after_sha256": _sha(payload),
        }],
    })
    store = AtomicJsonStore(repository="test")

    preview = store.cleanup_transaction_journals(
        tmp_path, older_than_seconds=0.0, dry_run=True
    )
    applied = store.cleanup_transaction_journals(
        tmp_path, older_than_seconds=0.0, dry_run=False
    )

    assert preview["candidate_count"] == 1
    assert preview["removed_count"] == 0
    assert applied["removed"] == ["committed-one"]
    assert not journal.exists()
    assert target.read_bytes() == payload
