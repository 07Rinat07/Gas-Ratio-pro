from __future__ import annotations

import gc
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class ResourceRecord:
    """Registered runtime resource that may keep project files alive.

    The first implementation intentionally stores metadata only.  It gives the
    platform one place to report which workspace or service is using a file and
    one place to request release before destructive storage operations.
    """

    resource_id: str
    path: str
    owner: str
    resource_type: str = "file"
    metadata: dict[str, str] = field(default_factory=dict)


class ResourceManager:
    """Small in-process registry for open files, dataframes and previews."""

    def __init__(self) -> None:
        self._resources: dict[str, ResourceRecord] = {}

    def register(
        self,
        resource_id: str,
        path: Path | str,
        *,
        owner: str,
        resource_type: str = "file",
        metadata: dict[str, str] | None = None,
    ) -> ResourceRecord:
        record = ResourceRecord(
            resource_id=str(resource_id),
            path=str(Path(path)),
            owner=owner,
            resource_type=resource_type,
            metadata=dict(metadata or {}),
        )
        self._resources[record.resource_id] = record
        return record

    def release(self, resource_id: str) -> bool:
        return self._resources.pop(str(resource_id), None) is not None

    def release_path(self, path: Path | str) -> tuple[ResourceRecord, ...]:
        target = Path(path).resolve()
        released: list[ResourceRecord] = []
        for key, record in list(self._resources.items()):
            try:
                record_path = Path(record.path).resolve()
            except OSError:
                record_path = Path(record.path)
            if record_path == target or target in record_path.parents:
                released.append(self._resources.pop(key))
        return tuple(released)

    def release_all(self) -> tuple[ResourceRecord, ...]:
        records = tuple(self._resources.values())
        self._resources.clear()
        return records

    def diagnostics(self) -> tuple[ResourceRecord, ...]:
        return tuple(self._resources.values())


GLOBAL_RESOURCE_MANAGER = ResourceManager()


@dataclass(frozen=True)
class DeleteAttempt:
    attempt: int
    success: bool
    error_type: str = ""
    error_message: str = ""


@dataclass(frozen=True)
class DeleteResult:
    path: str
    deleted: bool
    existed: bool
    attempts: tuple[DeleteAttempt, ...]
    released_resources: tuple[ResourceRecord, ...] = ()

    @property
    def last_error(self) -> str:
        for attempt in reversed(self.attempts):
            if not attempt.success:
                return attempt.error_message
        return ""

    @property
    def diagnostic_message(self) -> str:
        if self.deleted:
            return "Удаление выполнено."
        if not self.existed:
            return "Объект уже отсутствует."
        if self.last_error:
            return self.last_error
        return "Не удалось удалить объект."


class StorageDeleteError(RuntimeError):
    """Raised when the lifecycle delete engine cannot remove a path."""

    def __init__(self, result: DeleteResult) -> None:
        self.result = result
        super().__init__(result.diagnostic_message)


class DeleteEngine:
    """Single safe deletion point for project storage objects.

    The engine releases registered resources, clears Python-owned references via
    garbage collection and retries Windows-sensitive delete operations.  It does
    not know business semantics; repositories/services decide what path belongs
    to a dataset, LAS, export or report.
    """

    def __init__(
        self,
        *,
        resource_manager: ResourceManager | None = None,
        retries: int = 3,
        retry_delays: Iterable[float] = (0.2, 0.5, 1.0),
    ) -> None:
        self.resource_manager = resource_manager or GLOBAL_RESOURCE_MANAGER
        self.retries = max(1, int(retries))
        self.retry_delays = tuple(float(delay) for delay in retry_delays)

    def delete_path(self, path: Path | str, *, missing_ok: bool = True) -> DeleteResult:
        target = Path(path)
        existed = target.exists()
        released = self.resource_manager.release_path(target)
        gc.collect()

        if not existed:
            result = DeleteResult(path=str(target), deleted=False, existed=False, attempts=(), released_resources=released)
            if missing_ok:
                return result
            raise StorageDeleteError(result)

        attempts: list[DeleteAttempt] = []
        for attempt_index in range(1, self.retries + 1):
            try:
                if target.is_dir():
                    shutil.rmtree(target)
                else:
                    target.unlink()
            except PermissionError as exc:
                message = self._permission_message(target, exc)
                attempts.append(DeleteAttempt(attempt_index, False, type(exc).__name__, message))
            except FileNotFoundError:
                attempts.append(DeleteAttempt(attempt_index, True))
                return DeleteResult(str(target), True, existed, tuple(attempts), released)
            except OSError as exc:
                attempts.append(DeleteAttempt(attempt_index, False, type(exc).__name__, str(exc)))
            else:
                attempts.append(DeleteAttempt(attempt_index, True))
                return DeleteResult(str(target), True, existed, tuple(attempts), released)

            gc.collect()
            if attempt_index < self.retries:
                delay = self.retry_delays[min(attempt_index - 1, len(self.retry_delays) - 1)] if self.retry_delays else 0
                if delay > 0:
                    time.sleep(delay)

        result = DeleteResult(str(target), False, existed, tuple(attempts), released)
        raise StorageDeleteError(result)

    @staticmethod
    def _permission_message(path: Path, exc: PermissionError) -> str:
        return (
            f"Файл или каталог занят другим процессом: {path}. "
            "Закройте предпросмотр, Excel/редактор файла или связанный workspace и повторите операцию. "
            f"Исходная ошибка: {exc}"
        )
