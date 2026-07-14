"""Serializable performance baseline and regression evaluation.

The module compares compact diagnostics snapshots. It never receives or stores
live Streamlit, Plotly, pandas, executor or repository objects. Reports are
stable JSON-compatible values suitable for local release gates and CI.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping


@dataclass(frozen=True, slots=True)
class RegressionPolicy:
    max_duration_growth_pct: float = 25.0
    max_duration_growth_ms: float = 250.0
    max_cache_hit_rate_drop_pct: float = 10.0
    max_session_key_growth: int = 20
    fail_on_new_errors: bool = True

    def __post_init__(self) -> None:
        if self.max_duration_growth_pct < 0:
            raise ValueError("max_duration_growth_pct must not be negative")
        if self.max_duration_growth_ms < 0:
            raise ValueError("max_duration_growth_ms must not be negative")
        if self.max_cache_hit_rate_drop_pct < 0:
            raise ValueError("max_cache_hit_rate_drop_pct must not be negative")
        if self.max_session_key_growth < 0:
            raise ValueError("max_session_key_growth must not be negative")


@dataclass(frozen=True, slots=True)
class PerformanceBaseline:
    schema: str
    stages: tuple[tuple[str, float], ...]
    cache_hit_rate: float
    cache_measured: int
    session_keys: int
    failed_events: int

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["stages"] = dict(self.stages)
        return payload

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PerformanceBaseline":
        stages_value = value.get("stages") or {}
        if not isinstance(stages_value, Mapping):
            raise ValueError("baseline stages must be an object")
        return cls(
            schema=str(value.get("schema") or "gasratio.performance-baseline.v1"),
            stages=tuple(sorted((str(key), max(0.0, float(duration))) for key, duration in stages_value.items())),
            cache_hit_rate=max(0.0, min(100.0, float(value.get("cache_hit_rate") or 0.0))),
            cache_measured=max(0, int(value.get("cache_measured") or 0)),
            session_keys=max(0, int(value.get("session_keys") or 0)),
            failed_events=max(0, int(value.get("failed_events") or 0)),
        )


@dataclass(frozen=True, slots=True)
class RegressionFinding:
    metric: str
    status: str
    baseline: float
    current: float
    delta: float
    limit: float
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PerformanceRegressionReport:
    schema: str
    status: str
    findings: tuple[RegressionFinding, ...]
    compared_stages: int
    baseline: PerformanceBaseline
    current: PerformanceBaseline

    @property
    def passed(self) -> bool:
        return self.status != "critical"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "status": self.status,
            "passed": self.passed,
            "compared_stages": self.compared_stages,
            "findings": [item.to_dict() for item in self.findings],
            "baseline": self.baseline.to_dict(),
            "current": self.current.to_dict(),
        }

    def to_markdown(self) -> str:
        lines = [
            "## GASRATIO Pro performance regression gate",
            "",
            f"**Status:** {self.status.upper()}",
            f"**Compared stages:** {self.compared_stages}",
            "",
            "| Metric | Status | Baseline | Current | Delta | Limit |",
            "|---|---:|---:|---:|---:|---:|",
        ]
        for item in self.findings:
            lines.append(
                f"| {item.metric} | {item.status} | {item.baseline:.2f} | "
                f"{item.current:.2f} | {item.delta:.2f} | {item.limit:.2f} |"
            )
        if not self.findings:
            lines.append("| no comparable metrics | ok | 0 | 0 | 0 | 0 |")
        return "\n".join(lines) + "\n"


def build_performance_baseline(snapshot: Mapping[str, Any]) -> PerformanceBaseline:
    """Create a compact baseline from Diagnostics Center output."""

    runtime = snapshot.get("runtime") or {}
    events = runtime.get("events") or []
    stage_values: dict[str, list[float]] = {}
    failed = 0
    for event in events:
        if not isinstance(event, Mapping):
            continue
        stage = str(event.get("stage") or "").strip()
        if not stage:
            continue
        stage_values.setdefault(stage, []).append(max(0.0, float(event.get("duration_ms") or 0.0)))
        if str(event.get("status") or "success") != "success":
            failed += 1

    # Use p95-like value instead of the latest sample so one fast rerun cannot
    # hide a persistent slowdown. This mirrors core.performance_audit.
    stage_p95: dict[str, float] = {}
    for stage, values in stage_values.items():
        ordered = sorted(values)
        index = max(0, min(len(ordered) - 1, int((len(ordered) - 1) * 0.95)))
        stage_p95[stage] = round(ordered[index], 3)

    cache_summary = (snapshot.get("cache") or {}).get("summary") or {}
    session = snapshot.get("session") or {}
    return PerformanceBaseline(
        schema="gasratio.performance-baseline.v1",
        stages=tuple(sorted(stage_p95.items())),
        cache_hit_rate=max(0.0, min(100.0, float(cache_summary.get("hit_rate") or 0.0))),
        cache_measured=max(0, int(cache_summary.get("measured") or 0)),
        session_keys=max(0, int(session.get("total_keys") or 0)),
        failed_events=failed,
    )


def _duration_limit(baseline_ms: float, policy: RegressionPolicy) -> float:
    return max(
        float(policy.max_duration_growth_ms),
        baseline_ms * (float(policy.max_duration_growth_pct) / 100.0),
    )


def compare_performance_baselines(
    baseline: PerformanceBaseline,
    current: PerformanceBaseline,
    *,
    policy: RegressionPolicy = RegressionPolicy(),
) -> PerformanceRegressionReport:
    findings: list[RegressionFinding] = []
    baseline_stages = dict(baseline.stages)
    current_stages = dict(current.stages)

    for stage in sorted(set(baseline_stages) & set(current_stages)):
        old = baseline_stages[stage]
        new = current_stages[stage]
        delta = new - old
        limit = _duration_limit(old, policy)
        status = "critical" if delta > limit else "ok"
        findings.append(
            RegressionFinding(
                metric=f"stage:{stage}",
                status=status,
                baseline=old,
                current=new,
                delta=round(delta, 3),
                limit=round(limit, 3),
                message=("duration regression" if status == "critical" else "within duration budget"),
            )
        )

    if baseline.cache_measured > 0 and current.cache_measured > 0:
        drop = baseline.cache_hit_rate - current.cache_hit_rate
        findings.append(
            RegressionFinding(
                metric="cache_hit_rate_pct",
                status="critical" if drop > policy.max_cache_hit_rate_drop_pct else "ok",
                baseline=baseline.cache_hit_rate,
                current=current.cache_hit_rate,
                delta=round(-drop, 3),
                limit=policy.max_cache_hit_rate_drop_pct,
                message="cache hit-rate drop",
            )
        )

    key_growth = current.session_keys - baseline.session_keys
    findings.append(
        RegressionFinding(
            metric="session_state_keys",
            status="critical" if key_growth > policy.max_session_key_growth else "ok",
            baseline=float(baseline.session_keys),
            current=float(current.session_keys),
            delta=float(key_growth),
            limit=float(policy.max_session_key_growth),
            message="session-state key growth",
        )
    )

    new_failures = current.failed_events - baseline.failed_events
    if policy.fail_on_new_errors:
        findings.append(
            RegressionFinding(
                metric="failed_runtime_events",
                status="critical" if new_failures > 0 else "ok",
                baseline=float(baseline.failed_events),
                current=float(current.failed_events),
                delta=float(new_failures),
                limit=0.0,
                message="new failed runtime events",
            )
        )

    status = "critical" if any(item.status == "critical" for item in findings) else "ok"
    return PerformanceRegressionReport(
        schema="gasratio.performance-regression-report.v1",
        status=status,
        findings=tuple(findings),
        compared_stages=len(set(baseline_stages) & set(current_stages)),
        baseline=baseline,
        current=current,
    )
