from __future__ import annotations

import gc
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, MutableMapping

ReleaseCallback = Callable[[], None]


@dataclass(frozen=True)
class RegisteredResource:
    """A resource currently owned by an application workflow.

    Resources are intentionally generic: a dataset preview can register a
    dataframe, an Excel workbook path, a generated ZIP, or a plot object.  The
    storage lifecycle layer only needs enough metadata to release resources
    before destructive operations and to produce useful diagnostics when Windows
    refuses deletion because a file handle is still open.
    """

    id: str
    kind: str
    owner: str
    path: Path | None = None
    description: str = ""
    release_callback: ReleaseCallback | None = field(default=None, compare=False, repr=False)


@dataclass(frozen=True)
class ResourceDiagnostics:
    """Snapshot of registered resources grouped for diagnostics."""

    total: int
    open_files: tuple[RegisteredResource, ...]
    resources: tuple[RegisteredResource, ...]

    def owners_for_path(self, path: Path | str) -> tuple[str, ...]:
        target = Path(path).resolve()
        owners: list[str] = []
        for resource in self.resources:
            if resource.path is None:
                continue
            try:
                resource_path = resource.path.resolve()
            except OSError:
                resource_path = resource.path
            if resource_path == target or target in resource_path.parents or resource_path in target.parents:
                owners.append(resource.owner)
        return tuple(dict.fromkeys(owners))


class ResourceManager:
    """Registry and release point for open files, dataframes, figures and caches.

    UI and services must not delete files directly.  They should first ask this
    manager to release resources for the path being deleted.  This is critical
    on Windows, where a still-open Excel handle prevents ``rmtree``/``unlink``
    and raises ``WinError 32``.
    """

    def __init__(self) -> None:
        self._resources: dict[str, RegisteredResource] = {}

    def register(
        self,
        resource_id: str,
        *,
        kind: str,
        owner: str,
        path: Path | str | None = None,
        description: str = "",
        release_callback: ReleaseCallback | None = None,
    ) -> RegisteredResource:
        clean_id = str(resource_id).strip()
        if not clean_id:
            raise ValueError("resource_id must not be empty")
        resource = RegisteredResource(
            id=clean_id,
            kind=str(kind).strip() or "resource",
            owner=str(owner).strip() or "unknown",
            path=None if path is None else Path(path),
            description=str(description or ""),
            release_callback=release_callback,
        )
        self._resources[resource.id] = resource
        return resource

    def register_file(
        self,
        path: Path | str,
        *,
        owner: str,
        resource_id: str | None = None,
        description: str = "",
        release_callback: ReleaseCallback | None = None,
    ) -> RegisteredResource:
        file_path = Path(path)
        return self.register(
            resource_id or f"file:{file_path.resolve()}",
            kind="file",
            owner=owner,
            path=file_path,
            description=description,
            release_callback=release_callback,
        )

    def register_dataframe(
        self,
        resource_id: str,
        *,
        owner: str,
        path: Path | str | None = None,
        description: str = "",
        release_callback: ReleaseCallback | None = None,
    ) -> RegisteredResource:
        return self.register(
            resource_id,
            kind="dataframe",
            owner=owner,
            path=path,
            description=description,
            release_callback=release_callback,
        )

    def release(self, resource_id: str) -> bool:
        resource = self._resources.pop(str(resource_id), None)
        if resource is None:
            return False
        if resource.release_callback is not None:
            resource.release_callback()
        return True

    def release_many(self, resource_ids: Iterable[str]) -> int:
        count = 0
        for resource_id in tuple(resource_ids):
            if self.release(resource_id):
                count += 1
        if count:
            gc.collect()
        return count

    def release_owner(self, owner: str) -> int:
        owner_value = str(owner)
        return self.release_many(
            resource.id for resource in self._resources.values() if resource.owner == owner_value
        )

    def release_path(self, path: Path | str) -> int:
        target = Path(path).resolve()
        matching_ids: list[str] = []
        for resource in self._resources.values():
            if resource.path is None:
                continue
            try:
                resource_path = resource.path.resolve()
            except OSError:
                resource_path = resource.path
            if resource_path == target or resource_path in target.parents or target in resource_path.parents:
                matching_ids.append(resource.id)
        return self.release_many(matching_ids)

    def release_all(self) -> int:
        return self.release_many(tuple(self._resources))

    def diagnostics(self) -> ResourceDiagnostics:
        resources = tuple(self._resources.values())
        open_files = tuple(resource for resource in resources if resource.kind == "file" and resource.path is not None)
        return ResourceDiagnostics(total=len(resources), open_files=open_files, resources=resources)


@dataclass(frozen=True)
class FileHandleRecord:
    """A registered file handle or file-backed resource."""

    path: Path
    owner: str
    resource_id: str
    description: str = ""


class FileHandleManager:
    """Tracks file-backed resources and delegates release to ResourceManager.

    The class does not keep operating-system file descriptors open.  It records
    the logical owner of file-backed objects so destructive storage operations
    can release previews, cached readers and workbook-like objects before
    Windows attempts to remove the underlying file or directory.
    """

    def __init__(self, resource_manager: ResourceManager | None = None) -> None:
        self.resource_manager = resource_manager or ResourceManager()

    def register_file(
        self,
        path: Path | str,
        *,
        owner: str,
        resource_id: str | None = None,
        description: str = "",
        release_callback: ReleaseCallback | None = None,
    ) -> FileHandleRecord:
        resource = self.resource_manager.register_file(
            path,
            owner=owner,
            resource_id=resource_id,
            description=description,
            release_callback=release_callback,
        )
        assert resource.path is not None
        return FileHandleRecord(
            path=resource.path,
            owner=resource.owner,
            resource_id=resource.id,
            description=resource.description,
        )

    def release_path(self, path: Path | str) -> int:
        return self.resource_manager.release_path(path)

    def release_owner(self, owner: str) -> int:
        return self.resource_manager.release_owner(owner)

    def release_all(self) -> int:
        return self.resource_manager.release_all()

    def diagnostics(self) -> tuple[FileHandleRecord, ...]:
        records: list[FileHandleRecord] = []
        for resource in self.resource_manager.diagnostics().open_files:
            assert resource.path is not None
            records.append(
                FileHandleRecord(
                    path=resource.path,
                    owner=resource.owner,
                    resource_id=resource.id,
                    description=resource.description,
                )
            )
        return tuple(records)


@dataclass(frozen=True)
class CacheEntry:
    """A logical cache object registered with the platform cache manager."""

    key: str
    owner: str
    path: Path | None = None
    description: str = ""


class CacheManager:
    """Central cache registry and cleanup point for previews/tables/plots.

    The manager intentionally supports two cleanup mechanisms:
    1. registered callbacks for explicit cache owners;
    2. optional mutable mappings (for example ``st.session_state`` in UI code)
       cleaned by key prefix.

    Core services can use the first mechanism without importing Streamlit, while
    UI integration can pass session mappings when it is safe to do so.
    """

    def __init__(self) -> None:
        self._entries: dict[str, CacheEntry] = {}
        self._callbacks: dict[str, ReleaseCallback] = {}

    def register(
        self,
        key: str,
        *,
        owner: str,
        path: Path | str | None = None,
        description: str = "",
        release_callback: ReleaseCallback | None = None,
    ) -> CacheEntry:
        clean_key = str(key).strip()
        if not clean_key:
            raise ValueError("cache key must not be empty")
        entry = CacheEntry(
            key=clean_key,
            owner=str(owner).strip() or "unknown",
            path=None if path is None else Path(path),
            description=str(description or ""),
        )
        self._entries[clean_key] = entry
        if release_callback is not None:
            self._callbacks[clean_key] = release_callback
        return entry

    def clear(self, key: str) -> bool:
        clean_key = str(key)
        entry = self._entries.pop(clean_key, None)
        callback = self._callbacks.pop(clean_key, None)
        if callback is not None:
            callback()
        return entry is not None or callback is not None

    def clear_owner(self, owner: str) -> int:
        owner_value = str(owner)
        keys = [key for key, entry in self._entries.items() if entry.owner == owner_value]
        return self.clear_many(keys)

    def clear_path(self, path: Path | str) -> int:
        target = Path(path).resolve()
        keys: list[str] = []
        for key, entry in self._entries.items():
            if entry.path is None:
                continue
            try:
                entry_path = entry.path.resolve()
            except OSError:
                entry_path = entry.path
            if entry_path == target or entry_path in target.parents or target in entry_path.parents:
                keys.append(key)
        return self.clear_many(keys)

    def clear_many(self, keys: Iterable[str]) -> int:
        count = 0
        for key in tuple(keys):
            if self.clear(key):
                count += 1
        if count:
            gc.collect()
        return count

    def clear_all(self) -> int:
        return self.clear_many(tuple(self._entries))

    def clear_mapping_prefixes(self, mapping: MutableMapping[str, Any], prefixes: Iterable[str]) -> int:
        """Remove keys from a mutable mapping by prefix.

        This is used by UI adapters for session-state cleanup without making the
        storage lifecycle module depend on Streamlit.
        """

        prefix_tuple = tuple(str(prefix) for prefix in prefixes)
        keys = [key for key in tuple(mapping.keys()) if str(key).startswith(prefix_tuple)]
        for key in keys:
            del mapping[key]
        if keys:
            gc.collect()
        return len(keys)

    def diagnostics(self) -> tuple[CacheEntry, ...]:
        return tuple(self._entries.values())


@dataclass(frozen=True)
class DeleteResult:
    """Result of a lifecycle-managed delete operation."""

    path: Path
    deleted: bool
    attempts: int
    released_resources: int


class StorageDeleteError(RuntimeError):
    """Raised when DeleteEngine cannot remove a path safely."""

    def __init__(self, path: Path, *, attempts: int, original_error: BaseException, diagnostics: ResourceDiagnostics):
        self.path = path
        self.attempts = attempts
        self.original_error = original_error
        self.diagnostics = diagnostics
        owners = diagnostics.owners_for_path(path)
        owner_hint = "; используется: " + ", ".join(owners) if owners else ""
        super().__init__(
            f"Не удалось удалить {path}. Попыток: {attempts}. "
            f"Причина: {type(original_error).__name__}: {original_error}{owner_hint}"
        )


class DeleteEngine:
    """Single deletion entry point for project storage objects."""

    def __init__(
        self,
        resource_manager: ResourceManager | None = None,
        *,
        cache_manager: CacheManager | None = None,
        file_handle_manager: FileHandleManager | None = None,
        attempts: int = 3,
        delay_seconds: float = 0.2,
    ) -> None:
        self.resource_manager = resource_manager or ResourceManager()
        self.cache_manager = cache_manager or CacheManager()
        self.file_handle_manager = file_handle_manager or FileHandleManager(self.resource_manager)
        self.attempts = max(1, int(attempts))
        self.delay_seconds = max(0.0, float(delay_seconds))

    def delete_path(self, path: Path | str, *, missing_ok: bool = True) -> DeleteResult:
        target = Path(path)
        released = self.file_handle_manager.release_path(target)
        released += self.resource_manager.release_path(target)
        self.cache_manager.clear_path(target)
        gc.collect()

        if not target.exists():
            if missing_ok:
                return DeleteResult(path=target, deleted=False, attempts=0, released_resources=released)
            raise FileNotFoundError(target)

        last_error: BaseException | None = None
        for attempt in range(1, self.attempts + 1):
            try:
                if target.is_dir():
                    shutil.rmtree(target)
                else:
                    target.unlink()
                return DeleteResult(path=target, deleted=True, attempts=attempt, released_resources=released)
            except (PermissionError, OSError) as exc:
                last_error = exc
                self.file_handle_manager.release_path(target)
                self.resource_manager.release_path(target)
                self.cache_manager.clear_path(target)
                gc.collect()
                if attempt < self.attempts and self.delay_seconds:
                    time.sleep(self.delay_seconds)
        assert last_error is not None
        raise StorageDeleteError(
            target,
            attempts=self.attempts,
            original_error=last_error,
            diagnostics=self.resource_manager.diagnostics(),
        )


DEFAULT_RESOURCE_MANAGER = ResourceManager()
DEFAULT_CACHE_MANAGER = CacheManager()
DEFAULT_FILE_HANDLE_MANAGER = FileHandleManager(DEFAULT_RESOURCE_MANAGER)
DEFAULT_DELETE_ENGINE = DeleteEngine(
    DEFAULT_RESOURCE_MANAGER,
    cache_manager=DEFAULT_CACHE_MANAGER,
    file_handle_manager=DEFAULT_FILE_HANDLE_MANAGER,
)

@dataclass(frozen=True)
class VersionSyncResult:
    """Result of metadata-only project file version synchronization."""

    project_id: str
    asset_count: int
    version_count: int


@dataclass(frozen=True)
class IndexSyncResult:
    """Result of project storage index synchronization.

    ``version_asset_count`` and ``version_count`` are filled when the file
    versions metadata is synchronized together with the file index.  This keeps
    Project Database tables consistent after Dataset/LAS/Export delete
    operations and prevents stale rows from surviving in
    ``project_file_versions.json`` after ``project_index.json`` was rebuilt.
    """

    project_id: str
    entries_count: int
    missing_count: int = 0
    duplicate_count: int = 0
    version_asset_count: int = 0
    version_count: int = 0


class VersionManager:
    """Synchronize metadata-only file versions with the saved project index.

    File versions are diagnostic metadata, not independent storage.  Therefore
    they must be rebuilt from the current ``project_index.json`` after every
    Storage Lifecycle operation that changes files.
    """

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)

    def sync_project_versions(self, project_id: str, *, author: str = "local") -> VersionSyncResult:
        from projects.project_index import update_project_file_versions

        assets = update_project_file_versions(self.root, project_id, author=author)
        return VersionSyncResult(
            project_id=str(project_id),
            asset_count=len(assets),
            version_count=sum(asset.version_count for asset in assets),
        )

    def clear_project_versions(self, project_id: str) -> VersionSyncResult:
        # Updating versions from an empty or freshly rebuilt index writes an
        # empty metadata file.  The function is kept as a compatibility-friendly
        # explicit operation for cleanup workflows.
        return self.sync_project_versions(project_id)


class IndexManager:
    """Project file index synchronization facade.

    Project Database must not be treated as an isolated screen.  It is a
    storage-lifecycle index that has to be rebuilt after destructive filesystem
    operations so deleted datasets/LAS/exports do not continue to appear in the
    UI after a rerun or application restart.
    """

    def __init__(self, root: Path | str, *, version_manager: VersionManager | None = None) -> None:
        self.root = Path(root)
        self.version_manager = version_manager or VersionManager(self.root)

    def rebuild_project_index(self, project_id: str) -> IndexSyncResult:
        from projects.project_index import (
            detect_project_duplicate_files,
            save_project_file_index,
        )

        entries = save_project_file_index(self.root, project_id)
        duplicate_count = sum(group.duplicate_count for group in detect_project_duplicate_files(entries))
        versions = self.version_manager.sync_project_versions(project_id)
        return IndexSyncResult(
            project_id=str(project_id),
            entries_count=len(entries),
            missing_count=0,
            duplicate_count=duplicate_count,
            version_asset_count=versions.asset_count,
            version_count=versions.version_count,
        )

    def validate_project_index(self, project_id: str) -> IndexSyncResult:
        from projects.project_index import detect_project_duplicate_files, validate_project_file_index

        entries = validate_project_file_index(self.root, project_id)
        missing_count = sum(1 for entry in entries if entry.status == "missing")
        duplicate_count = sum(group.duplicate_count for group in detect_project_duplicate_files(entries))
        return IndexSyncResult(
            project_id=str(project_id),
            entries_count=len(entries),
            missing_count=missing_count,
            duplicate_count=duplicate_count,
        )

    def sync_after_delete(self, project_id: str) -> IndexSyncResult:
        """Rebuild project index and versions after a successful lifecycle delete."""

        return self.rebuild_project_index(project_id)

    def sync_project_storage(self, project_id: str) -> IndexSyncResult:
        """Synchronize every Project Database table from actual storage.

        This is the explicit API used by Project Database/Storage Explorer UI:
        it rebuilds the file index from the filesystem and then rewrites file
        versions from that fresh index.
        """

        return self.rebuild_project_index(project_id)
