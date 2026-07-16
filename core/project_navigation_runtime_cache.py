"""Bounded runtime cache for serialized Workbench project navigation.

The cache stores only primitive project-tree rows.  It never retains repository
objects, Streamlit widgets, DataFrames or open files.  Freshness is determined
from a compact metadata fingerprint so route changes can reuse navigation data
without silently serving stale project trees.
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from hashlib import blake2b
from pathlib import Path
from threading import RLock
from time import perf_counter
from typing import Any, Iterable, Mapping

_METADATA_SUFFIXES = {".json", ".yaml", ".yml", ".toml", ".ini"}
_IGNORED_PARTS = {
    "__pycache__", ".git", ".pytest_cache", "cache", "temp", "tmp",
    "revisions", "backups", ".trash",
}


def _project_path(root: Path | str, project_id: str) -> Path:
    return Path(root) / str(project_id or "").strip()


def project_navigation_token(root: Path | str, project_id: str) -> tuple[str, float, int]:
    """Return ``(token, duration_ms, file_count)`` for navigation metadata.

    The fingerprint uses relative path, file size and nanosecond mtime.  File
    contents are not read, keeping the freshness check considerably cheaper
    than rebuilding the project tree.
    """

    started = perf_counter()
    project_dir = _project_path(root, project_id)
    digest = blake2b(digest_size=16)
    file_count = 0
    if not project_dir.exists():
        digest.update(b"missing")
        return digest.hexdigest(), (perf_counter() - started) * 1000.0, 0

    candidates: list[Path] = []
    for path in project_dir.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(project_dir)
        if any(part in _IGNORED_PARTS for part in relative.parts):
            continue
        # Project Explorer is metadata-only.  Ignore large payload formats and
        # include extensionless metadata manifests for backward compatibility.
        if path.suffix and path.suffix.lower() not in _METADATA_SUFFIXES:
            continue
        candidates.append(path)

    for path in sorted(candidates, key=lambda item: item.as_posix()):
        try:
            stat = path.stat()
        except OSError:
            continue
        relative = path.relative_to(project_dir).as_posix()
        digest.update(relative.encode("utf-8", errors="surrogatepass"))
        digest.update(b"\0")
        digest.update(str(stat.st_size).encode("ascii"))
        digest.update(b":")
        digest.update(str(stat.st_mtime_ns).encode("ascii"))
        digest.update(b"\n")
        file_count += 1

    return digest.hexdigest(), (perf_counter() - started) * 1000.0, file_count


@dataclass(frozen=True, slots=True)
class ProjectNavigationCacheEntry:
    project_id: str
    profile: str
    token: str
    tree: tuple[dict[str, Any], ...]
    counts: dict[str, int]
    metadata_files: int


@dataclass(frozen=True, slots=True)
class ProjectNavigationLookup:
    status: str
    reason: str
    token: str
    token_ms: float
    metadata_files: int
    tree: tuple[dict[str, Any], ...] = ()
    counts: dict[str, int] | None = None

    @property
    def hit(self) -> bool:
        return self.status == "hit"


class ProjectNavigationRuntimeCache:
    """Small process-local LRU cache keyed by project id and metadata token."""

    def __init__(self, *, max_projects: int = 4) -> None:
        self._max_projects = max(1, int(max_projects))
        self._entries: OrderedDict[tuple[str, str], ProjectNavigationCacheEntry] = OrderedDict()
        self._project_lru: OrderedDict[str, None] = OrderedDict()
        self._lock = RLock()
        self._hits = 0
        self._misses = 0
        self._invalidations = 0
        self._evictions = 0
        self._last_reason = "not-used"
        self._profile_stats: dict[str, dict[str, Any]] = {}
        self._latest_branch_timings_ms: dict[str, float] = {}

    def _touch_project(self, project_id: str) -> None:
        self._project_lru[project_id] = None
        self._project_lru.move_to_end(project_id)

    def _remove_project_entries(self, project_id: str) -> int:
        keys = [key for key in self._entries if key[0] == project_id]
        for key in keys:
            self._entries.pop(key, None)
        self._project_lru.pop(project_id, None)
        return len(keys)

    def lookup(
        self,
        root: Path | str,
        project_id: str,
        *,
        profile: str = "full",
    ) -> ProjectNavigationLookup:
        base_token, token_ms, metadata_files = project_navigation_token(root, project_id)
        clean_profile = str(profile or "full").strip() or "full"
        token = f"{base_token}:{clean_profile}"
        clean_id = str(project_id or "").strip()
        cache_key = (clean_id, clean_profile)
        with self._lock:
            profile_stats = self._profile_stats.setdefault(
                clean_profile, {"hits": 0, "misses": 0, "loads": 0, "last_load_ms": 0.0, "branch_timings_ms": {}}
            )
            entry = self._entries.get(cache_key)
            if entry is None:
                self._misses += 1
                profile_stats["misses"] += 1
                has_other_profile = any(key[0] == clean_id for key in self._entries)
                self._last_reason = "profile-cold" if has_other_profile else "cold"
                return ProjectNavigationLookup("miss", self._last_reason, token, token_ms, metadata_files)
            if entry.token != token:
                removed = self._remove_project_entries(clean_id)
                self._misses += 1
                profile_stats["misses"] += 1
                self._invalidations += removed
                self._last_reason = "metadata-changed"
                return ProjectNavigationLookup("miss", "metadata-changed", token, token_ms, metadata_files)
            self._entries.move_to_end(cache_key)
            self._touch_project(clean_id)
            self._hits += 1
            profile_stats["hits"] += 1
            self._last_reason = "token-match"
            return ProjectNavigationLookup(
                "hit", "token-match", token, token_ms, metadata_files,
                tree=tuple(dict(item) for item in entry.tree),
                counts=dict(entry.counts),
            )

    def store(
        self,
        *,
        project_id: str,
        token: str,
        tree: Iterable[Mapping[str, Any]],
        counts: Mapping[str, int],
        metadata_files: int,
        profile: str = "full",
        load_ms: float = 0.0,
        branch_timings_ms: Mapping[str, float] | None = None,
    ) -> None:
        clean_id = str(project_id or "").strip()
        clean_profile = str(profile or "full").strip() or "full"
        normalized_tree = tuple(dict(item) for item in tree)
        normalized_counts = {str(key): int(value) for key, value in counts.items()}
        entry = ProjectNavigationCacheEntry(
            project_id=clean_id,
            profile=clean_profile,
            token=str(token or ""),
            tree=normalized_tree,
            counts=normalized_counts,
            metadata_files=max(0, int(metadata_files)),
        )
        normalized_timings = {
            str(key): round(max(0.0, float(value)), 3)
            for key, value in dict(branch_timings_ms or {}).items()
        }
        with self._lock:
            profile_stats = self._profile_stats.setdefault(
                clean_profile, {"hits": 0, "misses": 0, "loads": 0, "last_load_ms": 0.0, "branch_timings_ms": {}}
            )
            profile_stats["loads"] += 1
            profile_stats["last_load_ms"] = round(max(0.0, float(load_ms)), 3)
            profile_stats["branch_timings_ms"] = normalized_timings
            self._latest_branch_timings_ms = normalized_timings
            cache_key = (clean_id, clean_profile)
            self._entries[cache_key] = entry
            self._entries.move_to_end(cache_key)
            self._touch_project(clean_id)
            while len(self._project_lru) > self._max_projects:
                oldest_project, _ = self._project_lru.popitem(last=False)
                removed = self._remove_project_entries(oldest_project)
                self._evictions += removed

    def invalidate(self, project_id: str | None = None, *, reason: str = "explicit") -> int:
        with self._lock:
            if project_id is None:
                removed = len(self._entries)
                self._entries.clear()
                self._project_lru.clear()
            else:
                removed = self._remove_project_entries(str(project_id or "").strip())
            if removed:
                self._invalidations += removed
            self._last_reason = str(reason or "explicit")
            return removed

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            total = self._hits + self._misses
            project_profiles: dict[str, list[str]] = {}
            for project_id, profile in self._entries:
                project_profiles.setdefault(project_id, []).append(profile)
            return {
                "entries": len(self._entries),
                "project_count": len(self._project_lru),
                "max_projects": self._max_projects,
                "hits": self._hits,
                "misses": self._misses,
                "invalidations": self._invalidations,
                "evictions": self._evictions,
                "hit_rate_percent": round((self._hits / total * 100.0) if total else 0.0, 2),
                "last_reason": self._last_reason,
                "projects": list(self._project_lru.keys()),
                "project_profiles": {
                    project_id: sorted(profiles)
                    for project_id, profiles in project_profiles.items()
                },
                "profiles": {
                    profile: {
                        **dict(values),
                        "hit_rate_percent": round(
                            (int(values.get("hits", 0)) / max(1, int(values.get("hits", 0)) + int(values.get("misses", 0))) * 100.0),
                            2,
                        ),
                    }
                    for profile, values in sorted(self._profile_stats.items())
                },
                "latest_branch_timings_ms": dict(self._latest_branch_timings_ms),
            }

    def close(self) -> None:
        self.invalidate(reason="close")
