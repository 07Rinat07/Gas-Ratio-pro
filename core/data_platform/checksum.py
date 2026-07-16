"""Streaming checksums for source and derived engineering artifacts."""
from __future__ import annotations

import hashlib
from pathlib import Path

_DEFAULT_CHUNK_SIZE = 1024 * 1024


def sha256_file(path: Path | str, *, chunk_size: int = _DEFAULT_CHUNK_SIZE) -> str:
    """Return a lowercase SHA-256 digest without loading the whole file."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")
    source = Path(path)
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()
