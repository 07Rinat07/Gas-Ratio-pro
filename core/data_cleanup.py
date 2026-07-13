"""Safe cleanup of generated application data.

The service removes disposable runtime data while preserving user projects by
default.  Destructive project removal must be requested explicitly.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
from typing import Iterable


@dataclass(frozen=True)
class DataCleanupItem:
    path: str
    bytes: int
    removed: bool


@dataclass(frozen=True)
class DataCleanupResult:
    items: tuple[DataCleanupItem, ...]
    freed_bytes: int
    dry_run: bool


class DataCleanupService:
    """Clean disposable folders under a bounded project root."""

    DISPOSABLE_DIRS = ("cache", "temp", "exports", "thumbnails")

    def __init__(self, data_root: Path | str) -> None:
        self.data_root = Path(data_root).resolve()

    def _bounded(self, path: Path) -> Path:
        resolved = path.resolve()
        if resolved != self.data_root and self.data_root not in resolved.parents:
            raise ValueError(f"Cleanup path escapes data root: {resolved}")
        return resolved

    @staticmethod
    def _size(path: Path) -> int:
        if not path.exists():
            return 0
        if path.is_file() or path.is_symlink():
            return path.stat().st_size
        return sum(
            item.stat().st_size
            for item in path.rglob("*")
            if item.is_file() and not item.is_symlink()
        )

    def candidates(self) -> tuple[Path, ...]:
        return tuple(self._bounded(self.data_root / name) for name in self.DISPOSABLE_DIRS)

    def cleanup(self, *, dry_run: bool = False, extra_paths: Iterable[Path | str] = ()) -> DataCleanupResult:
        paths = [*self.candidates(), *(self._bounded(Path(path)) for path in extra_paths)]
        items: list[DataCleanupItem] = []
        freed = 0
        seen: set[Path] = set()
        for path in paths:
            if path in seen or not path.exists():
                continue
            seen.add(path)
            size = self._size(path)
            removed = False
            if not dry_run:
                if path.is_dir() and not path.is_symlink():
                    shutil.rmtree(path)
                else:
                    path.unlink()
                removed = True
                freed += size
            items.append(DataCleanupItem(str(path), size, removed))
        return DataCleanupResult(tuple(items), freed, dry_run)
