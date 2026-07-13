"""Performance budget evaluation for engineering workspaces.

The audit consumes compact runtime diagnostic events and produces a stable,
framework-neutral summary. It is intentionally small enough to live in
Streamlit session state and to be asserted in automated release gates.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import fmean
from typing import Iterable

from core.runtime_diagnostics import RuntimeDiagnosticEvent


@dataclass(frozen=True, slots=True)
class PerformanceBudget:
    stage: str
    warning_ms: float
    critical_ms: float
    max_payload_bytes: int = 0

    def __post_init__(self) -> None:
        if not self.stage.strip():
            raise ValueError("stage must not be empty")
        if self.warning_ms < 0 or self.critical_ms < self.warning_ms:
            raise ValueError("invalid duration budget")
        if self.max_payload_bytes < 0:
            raise ValueError("max_payload_bytes must not be negative")


@dataclass(frozen=True, slots=True)
class StagePerformanceSummary:
    stage: str
    samples: int
    average_ms: float
    maximum_ms: float
    cache_hits: int
    cache_misses: int
    failed: int
    maximum_payload_bytes: int
    status: str


DEFAULT_PERFORMANCE_BUDGETS: tuple[PerformanceBudget, ...] = (
    PerformanceBudget("interpretation_plots", warning_ms=2500.0, critical_ms=6000.0),
    PerformanceBudget(
        "plot_frontend_dispatch",
        warning_ms=400.0,
        critical_ms=1200.0,
        max_payload_bytes=12 * 1024 * 1024,
    ),
)


def evaluate_performance(
    events: Iterable[RuntimeDiagnosticEvent],
    *,
    budgets: Iterable[PerformanceBudget] = DEFAULT_PERFORMANCE_BUDGETS,
) -> tuple[StagePerformanceSummary, ...]:
    """Aggregate diagnostic events against explicit performance budgets."""

    event_list = tuple(events)
    results: list[StagePerformanceSummary] = []
    for budget in budgets:
        matching = tuple(event for event in event_list if event.stage == budget.stage)
        if not matching:
            results.append(
                StagePerformanceSummary(
                    stage=budget.stage,
                    samples=0,
                    average_ms=0.0,
                    maximum_ms=0.0,
                    cache_hits=0,
                    cache_misses=0,
                    failed=0,
                    maximum_payload_bytes=0,
                    status="not-measured",
                )
            )
            continue

        average_ms = fmean(event.duration_ms for event in matching)
        maximum_ms = max(event.duration_ms for event in matching)
        maximum_payload = max(event.memory_bytes for event in matching)
        failed = sum(1 for event in matching if event.status != "success")
        cache_hits = sum(1 for event in matching if event.cache_status == "hit")
        cache_misses = sum(1 for event in matching if event.cache_status == "miss")

        status = "ok"
        if failed or maximum_ms >= budget.critical_ms:
            status = "critical"
        elif maximum_ms >= budget.warning_ms:
            status = "warning"
        if budget.max_payload_bytes and maximum_payload > budget.max_payload_bytes:
            status = "critical"

        results.append(
            StagePerformanceSummary(
                stage=budget.stage,
                samples=len(matching),
                average_ms=round(average_ms, 2),
                maximum_ms=round(maximum_ms, 2),
                cache_hits=cache_hits,
                cache_misses=cache_misses,
                failed=failed,
                maximum_payload_bytes=maximum_payload,
                status=status,
            )
        )
    return tuple(results)
