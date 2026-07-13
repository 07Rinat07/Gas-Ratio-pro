"""Deterministic render queue for expensive workspace components.

The queue is intentionally framework-neutral. It serializes expensive builders,
deduplicates task identifiers within one render cycle and records compact timing
metadata without retaining rendered payloads after the caller stores them in its
own bounded cache.
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

    def execute(self, tasks: Iterable[RenderTask]) -> tuple[RenderTaskResult, ...]:
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

        results: list[RenderTaskResult] = []
        for task in unique:
            task_id = str(task.task_id)
            if task_id in self._running:
                self._duplicates += 1
                continue
            self._running.add(task_id)
            started = perf_counter()
            try:
                value = task.builder()
            except Exception:
                self._failed += 1
                raise
            finally:
                self._running.discard(task_id)
            duration_ms = (perf_counter() - started) * 1000.0
            self._completed += 1
            results.append(RenderTaskResult(task_id, value, duration_ms, str(task.renderer)))
        return tuple(results)

    def stats(self) -> dict[str, int]:
        return {
            "completed": self._completed,
            "failed": self._failed,
            "duplicates": self._duplicates,
            "running": len(self._running),
        }
