"""Deterministic render queue for expensive workspace components.

The queue is framework-neutral. It serializes expensive builders, deduplicates
identifiers within one render cycle and can isolate a failed plot task so the
remaining engineering workspace stays available.
"""
from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any, Callable, Iterable


@dataclass(frozen=True, slots=True)
class RenderTask:
    task_id: str
    builder: Callable[[], Any]
    renderer: str = "plotly"


@dataclass(frozen=True, slots=True)
class RenderTaskResult:
    task_id: str
    value: Any
    duration_ms: float
    renderer: str


@dataclass(frozen=True, slots=True)
class RenderTaskFailure:
    task_id: str
    duration_ms: float
    renderer: str
    exception_type: str
    message: str


@dataclass(frozen=True, slots=True)
class RenderBatchResult:
    completed: tuple[RenderTaskResult, ...]
    failed: tuple[RenderTaskFailure, ...]


class RenderQueue:
    """Run unique render tasks sequentially and expose bounded statistics."""

    def __init__(self, *, max_tasks: int = 32) -> None:
        if int(max_tasks) < 1:
            raise ValueError("max_tasks must be positive")
        self.max_tasks = int(max_tasks)
        self._running: set[str] = set()
        self._completed = 0
        self._failed = 0
        self._duplicates = 0

    def _unique_tasks(self, tasks: Iterable[RenderTask]) -> list[RenderTask]:
        unique: list[RenderTask] = []
        seen: set[str] = set()
        for task in tasks:
            task_id = str(task.task_id).strip()
            if not task_id:
                raise ValueError("render task id must not be empty")
            if task_id in seen:
                self._duplicates += 1
                continue
            seen.add(task_id)
            unique.append(task)
            if len(unique) >= self.max_tasks:
                break
        return unique

    def execute_resilient(self, tasks: Iterable[RenderTask]) -> RenderBatchResult:
        """Execute all unique tasks and isolate individual builder failures."""

        results: list[RenderTaskResult] = []
        failures: list[RenderTaskFailure] = []
        for task in self._unique_tasks(tasks):
            task_id = str(task.task_id)
            if task_id in self._running:
                self._duplicates += 1
                continue
            self._running.add(task_id)
            started = perf_counter()
            try:
                value = task.builder()
            except Exception as exc:  # task boundary; caller receives structured failure
                duration_ms = (perf_counter() - started) * 1000.0
                self._failed += 1
                failures.append(
                    RenderTaskFailure(
                        task_id=task_id,
                        duration_ms=duration_ms,
                        renderer=str(task.renderer),
                        exception_type=type(exc).__name__,
                        message=str(exc),
                    )
                )
            else:
                duration_ms = (perf_counter() - started) * 1000.0
                self._completed += 1
                results.append(RenderTaskResult(task_id, value, duration_ms, str(task.renderer)))
            finally:
                self._running.discard(task_id)
        return RenderBatchResult(tuple(results), tuple(failures))

    def execute(self, tasks: Iterable[RenderTask]) -> tuple[RenderTaskResult, ...]:
        """Backward-compatible strict execution.

        The first task failure is raised after the queue releases its running
        marker. New workspace code should prefer :meth:`execute_resilient`.
        """

        batch = self.execute_resilient(tasks)
        if batch.failed:
            failure = batch.failed[0]
            raise RuntimeError(f"{failure.task_id}: {failure.exception_type}: {failure.message}")
        return batch.completed

    def stats(self) -> dict[str, int]:
        return {
            "completed": self._completed,
            "failed": self._failed,
            "duplicates": self._duplicates,
            "running": len(self._running),
        }
