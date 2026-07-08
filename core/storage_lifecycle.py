from __future__ import annotations

import gc
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

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

    def __init__(self, resource_manager: ResourceManager | None = None, *, attempts: int = 3, delay_seconds: float = 0.2) -> None:
        self.resource_manager = resource_manager or ResourceManager()
        self.attempts = max(1, int(attempts))
        self.delay_seconds = max(0.0, float(delay_seconds))

    def delete_path(self, path: Path | str, *, missing_ok: bool = True) -> DeleteResult:
        target = Path(path)
        released = self.resource_manager.release_path(target)
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
                self.resource_manager.release_path(target)
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
DEFAULT_DELETE_ENGINE = DeleteEngine(DEFAULT_RESOURCE_MANAGER)
