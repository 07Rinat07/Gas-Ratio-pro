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
import json
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
    estimated_bytes: int


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

    def __init__(
        self,
        *,
        max_projects: int = 4,
        max_profiles_per_project: int = 6,
        max_estimated_bytes: int = 4 * 1024 * 1024,
    ) -> None:
        self._max_projects = max(1, int(max_projects))
        self._max_profiles_per_project = max(1, int(max_profiles_per_project))
        self._max_estimated_bytes = max(1, int(max_estimated_bytes))
        self._entries: OrderedDict[tuple[str, str], ProjectNavigationCacheEntry] = OrderedDict()
        self._project_lru: OrderedDict[str, None] = OrderedDict()
        self._lock = RLock()
        self._hits = 0
        self._misses = 0
        self._invalidations = 0
        self._evictions = 0
        self._profile_evictions = 0
        self._byte_evictions = 0
        self._oversized_rejections = 0
        self._estimated_bytes = 0
        self._last_reason = "not-used"
        self._profile_stats: dict[str, dict[str, Any]] = {}
        self._latest_branch_timings_ms: dict[str, float] = {}

    def _touch_project(self, project_id: str) -> None:
        self._project_lru[project_id] = None
        self._project_lru.move_to_end(project_id)

    @staticmethod
    def _estimate_entry_bytes(
        *,
        project_id: str,
        profile: str,
        token: str,
        tree: tuple[dict[str, Any], ...],
        counts: Mapping[str, int],
    ) -> int:
        """Return a stable UTF-8 JSON size estimate for one primitive cache entry."""
        payload = {
            "project_id": project_id,
            "profile": profile,
            "token": token,
            "tree": tree,
            "counts": dict(counts),
        }
        try:
            encoded = json.dumps(
                payload, ensure_ascii=False, separators=(",", ":"), default=str
            ).encode("utf-8")
        except (TypeError, ValueError):
            encoded = repr(payload).encode("utf-8", errors="replace")
        return len(encoded)

    def _pop_entry(self, key: tuple[str, str]) -> ProjectNavigationCacheEntry | None:
        entry = self._entries.pop(key, None)
        if entry is not None:
            self._estimated_bytes = max(0, self._estimated_bytes - entry.estimated_bytes)
        return entry

    def _remove_project_entries(self, project_id: str) -> int:
        keys = [key for key in self._entries if key[0] == project_id]
        for key in keys:
            self._pop_entry(key)
        self._project_lru.pop(project_id, None)
        return len(keys)

    def _drop_project_lru_if_empty(self, project_id: str) -> None:
        if not any(key[0] == project_id for key in self._entries):
            self._project_lru.pop(project_id, None)

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
        clean_token = str(token or "")
        estimated_bytes = self._estimate_entry_bytes(
            project_id=clean_id,
            profile=clean_profile,
            token=clean_token,
            tree=normalized_tree,
            counts=normalized_counts,
        )
        entry = ProjectNavigationCacheEntry(
            project_id=clean_id,
            profile=clean_profile,
            token=clean_token,
            tree=normalized_tree,
            counts=normalized_counts,
            metadata_files=max(0, int(metadata_files)),
            estimated_bytes=estimated_bytes,
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
            previous = self._pop_entry(cache_key)
            if entry.estimated_bytes > self._max_estimated_bytes:
                self._oversized_rejections += 1
                self._last_reason = "profile-over-byte-budget"
                self._drop_project_lru_if_empty(clean_id)
                return

            self._entries[cache_key] = entry
            self._estimated_bytes += entry.estimated_bytes
            self._entries.move_to_end(cache_key)
            self._touch_project(clean_id)

            project_keys = [key for key in self._entries if key[0] == clean_id]
            while len(project_keys) > self._max_profiles_per_project:
                oldest_profile_key = project_keys.pop(0)
                # The just-stored key is newest, so normal LRU order keeps it.
                if self._pop_entry(oldest_profile_key) is not None:
                    self._evictions += 1
                    self._profile_evictions += 1
            while len(self._project_lru) > self._max_projects:
                oldest_project, _ = self._project_lru.popitem(last=False)
                removed = self._remove_project_entries(oldest_project)
                self._evictions += removed

            while self._estimated_bytes > self._max_estimated_bytes and self._entries:
                oldest_key = next(iter(self._entries))
                if self._pop_entry(oldest_key) is not None:
                    self._evictions += 1
                    self._byte_evictions += 1
                    self._drop_project_lru_if_empty(oldest_key[0])

    def invalidate(self, project_id: str | None = None, *, reason: str = "explicit") -> int:
        with self._lock:
            if project_id is None:
                removed = len(self._entries)
                self._entries.clear()
                self._project_lru.clear()
                self._estimated_bytes = 0
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
            project_estimated_bytes: dict[str, int] = {}
            profile_estimated_bytes: dict[str, int] = {}
            total_estimated_bytes = 0
            for (project_id, profile), entry in self._entries.items():
                project_profiles.setdefault(project_id, []).append(profile)
                project_estimated_bytes[project_id] = (
                    project_estimated_bytes.get(project_id, 0) + entry.estimated_bytes
                )
                profile_estimated_bytes[profile] = (
                    profile_estimated_bytes.get(profile, 0) + entry.estimated_bytes
                )
                total_estimated_bytes += entry.estimated_bytes
            return {
                "entries": len(self._entries),
                "project_count": len(self._project_lru),
                "max_projects": self._max_projects,
                "max_profiles_per_project": self._max_profiles_per_project,
                "max_estimated_bytes": self._max_estimated_bytes,
                "max_estimated_kib": round(self._max_estimated_bytes / 1024.0, 3),
                "hits": self._hits,
                "misses": self._misses,
                "invalidations": self._invalidations,
                "evictions": self._evictions,
                "profile_evictions": self._profile_evictions,
                "byte_evictions": self._byte_evictions,
                "oversized_rejections": self._oversized_rejections,
                "estimated_bytes": total_estimated_bytes,
                "estimated_kib": round(total_estimated_bytes / 1024.0, 3),
                "budget_utilization_percent": round(total_estimated_bytes / self._max_estimated_bytes * 100.0, 2),
                "hit_rate_percent": round((self._hits / total * 100.0) if total else 0.0, 2),
                "last_reason": self._last_reason,
                "projects": list(self._project_lru.keys()),
                "project_profiles": {
                    project_id: sorted(profiles)
                    for project_id, profiles in project_profiles.items()
                },
                "project_estimated_bytes": dict(sorted(project_estimated_bytes.items())),
                "profile_estimated_bytes": dict(sorted(profile_estimated_bytes.items())),
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
