from __future__ import annotations

import hashlib
import json
from pathlib import Path

from core.repository_io import AtomicJsonStore, RepositoryIOMetrics


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def test_recovery_verifies_backup_hash_and_restored_file(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    target = root / "data.json"
    original = b'{"value": "before"}\n'
    target.write_bytes(b'{"value": "after"}\n')

    tx_dir = root / ".repository_transactions" / "pending"
    tx_dir.mkdir(parents=True)
    (tx_dir / "backup-0000.bin").write_bytes(original)
    manifest = {
        "schema": "gas-ratio-pro/repository-transaction/v2",
        "transaction_id": "pending",
        "repository": "test",
        "root": str(root.resolve()),
        "status": "applying",
        "entries": [{
            "operation": "write",
            "target": str(target.resolve()),
            "existed": True,
            "backup": "backup-0000.bin",
            "staged": "staged-0000.json",
            "before_sha256": _sha256(original),
            "after_sha256": "",
        }],
    }
    (tx_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    metrics = RepositoryIOMetrics()
    result = AtomicJsonStore(repository="test", metrics=metrics).recover_transactions(root)

    assert result == {"recovered": 1, "failures": 0}
    assert target.read_bytes() == original
    snapshot = metrics.mutation_snapshot()
    assert snapshot["integrity_checks"] == 2
    assert snapshot["integrity_failures"] == 0
    assert snapshot["cleaned_transactions"] == 1


def test_corrupt_backup_is_quarantined_without_overwriting_target(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    target = root / "data.json"
    target.write_text('{"value": "after"}\n', encoding="utf-8")

    tx_dir = root / ".repository_transactions" / "corrupt"
    tx_dir.mkdir(parents=True)
    (tx_dir / "backup-0000.bin").write_bytes(b"corrupt")
    manifest = {
        "schema": "gas-ratio-pro/repository-transaction/v2",
        "transaction_id": "corrupt",
        "repository": "test",
        "root": str(root.resolve()),
        "status": "applying",
        "entries": [{
            "operation": "write",
            "target": str(target.resolve()),
            "existed": True,
            "backup": "backup-0000.bin",
            "staged": "staged-0000.json",
            "before_sha256": _sha256(b"expected"),
            "after_sha256": "",
        }],
    }
    (tx_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    metrics = RepositoryIOMetrics()
    result = AtomicJsonStore(repository="test", metrics=metrics).recover_transactions(root)

    assert result == {"recovered": 0, "failures": 0}
    assert json.loads(target.read_text(encoding="utf-8"))["value"] == "after"
    quarantined = list((root / ".repository_transactions_quarantine").iterdir())
    assert len(quarantined) == 1
    snapshot = metrics.mutation_snapshot()
    assert snapshot["integrity_failures"] == 1
    assert snapshot["quarantined_transactions"] == 1


def test_invalid_manifest_is_quarantined_instead_of_deleted(tmp_path: Path) -> None:
    root = tmp_path / "project"
    tx_dir = root / ".repository_transactions" / "broken"
    tx_dir.mkdir(parents=True)
    (tx_dir / "manifest.json").write_text("{broken", encoding="utf-8")

    metrics = RepositoryIOMetrics()
    result = AtomicJsonStore(repository="test", metrics=metrics).recover_transactions(root)

    assert result == {"recovered": 0, "failures": 0}
    assert not tx_dir.exists()
    assert any((root / ".repository_transactions_quarantine").iterdir())
    snapshot = metrics.mutation_snapshot()
    assert snapshot["quarantined_transactions"] == 1
    assert snapshot["integrity_failures"] == 1


def test_transaction_manifest_v2_hashes_are_verified_during_commit(tmp_path: Path) -> None:
    root = tmp_path / "project"
    metrics = RepositoryIOMetrics()
    store = AtomicJsonStore(repository="test", metrics=metrics)
    target = root / "data.json"

    tx = store.transaction()
    tx.write(target, {"value": 1})
    result = tx.commit()

    assert result.status == "committed"
    assert json.loads(target.read_text(encoding="utf-8")) == {"value": 1}
    assert not (root / ".repository_transactions").exists()
