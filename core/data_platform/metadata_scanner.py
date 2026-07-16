"""Lightweight metadata-scanner contracts for industry data formats."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Protocol


@dataclass(frozen=True, slots=True)
class MetadataScanResult:
    format_id: str
    metadata: Mapping[str, str | int | float | bool | None] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    bytes_read: int = 0
    complete: bool = True

    def __post_init__(self) -> None:
        if not self.format_id.strip():
            raise ValueError("format_id must not be empty")
        if self.bytes_read < 0:
            raise ValueError("bytes_read must not be negative")
        object.__setattr__(self, "format_id", self.format_id.strip().lower())
        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, object]:
        return {
            "format_id": self.format_id,
            "metadata": dict(self.metadata),
            "warnings": list(self.warnings),
            "bytes_read": self.bytes_read,
            "complete": self.complete,
        }


class MetadataScanner(Protocol):
    format_id: str

    def scan(self, source: Path | str) -> MetadataScanResult:
        """Read metadata only, without materializing the complete dataset."""
