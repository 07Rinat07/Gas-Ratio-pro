from __future__ import annotations

import hashlib
import json
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

from projects.project_manager import append_project_history
from projects.repository import safe_project_id

PROJECT_PERFORMANCE_FILE_NAME = "performance_optimization.json"
PERFORMANCE_SCHEMA = "gas-ratio-pro.performance-optimization.v1"
PERFORMANCE_METRIC_TYPES = {"timer", "memory", "io", "cache", "render", "dataframe", "custom"}
PERFORMANCE_STATUSES = {"ok", "warning", "critical"}
CACHE_STATUSES = {"fresh", "stale", "invalidated"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _project_dir(root: Path | str, project_id: str) -> Path:
    return Path(root) / safe_project_id(project_id)


def _performance_path(root: Path | str, project_id: str) -> Path:
    return _project_dir(root, project_id) / PROJECT_PERFORMANCE_FILE_NAME


def _json_read(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return default


def _json_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _payload(root: Path | str, project_id: str) -> dict[str, Any]:
    payload = _json_read(_performance_path(root, project_id), {"schema": PERFORMANCE_SCHEMA, "metrics": [], "cache": [], "recommendations": []})
    if not isinstance(payload, dict):
        payload = {"schema": PERFORMANCE_SCHEMA, "metrics": [], "cache": [], "recommendations": []}
    payload.setdefault("schema", PERFORMANCE_SCHEMA)
    payload.setdefault("metrics", [])
    payload.setdefault("cache", [])
    payload.setdefault("recommendations", [])
    return payload


def _clean_text(value: Any, field_label: str, *, max_length: int = 240, required: bool = False) -> str:
    text = "" if value is None else str(value).strip()
    if required and not text:
        raise ValueError(f"{field_label}: значение обязательно.")
    if len(text) > max_length:
        raise ValueError(f"{field_label}: максимум {max_length} символов.")
    return text


def _normalize_metric_type(value: Any) -> str:
    text = _clean_text(value, "Тип метрики", max_length=40).lower() or "custom"
    if text not in PERFORMANCE_METRIC_TYPES:
        raise ValueError(f"Тип метрики должен быть одним из: {', '.join(sorted(PERFORMANCE_METRIC_TYPES))}.")
    return text


def _normalize_status(value: Any) -> str:
    text = _clean_text(value, "Статус", max_length=40).lower() or "ok"
    if text not in PERFORMANCE_STATUSES:
        raise ValueError(f"Статус должен быть одним из: {', '.join(sorted(PERFORMANCE_STATUSES))}.")
    return text


def _normalize_cache_status(value: Any) -> str:
    text = _clean_text(value, "Статус кэша", max_length=40).lower() or "fresh"
    if text not in CACHE_STATUSES:
        raise ValueError(f"Статус кэша должен быть одним из: {', '.join(sorted(CACHE_STATUSES))}.")
    return text


def _safe_id(prefix: str, parts: Sequence[Any]) -> str:
    source = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def _to_float(value: Any, field_label: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_label}: должно быть числом.") from exc
    if result < 0:
        raise ValueError(f"{field_label}: не может быть отрицательным.")
    return result


@dataclass(frozen=True)
class PerformanceMetric:
    """One normalized performance observation stored as project metadata."""

    id: str
    name: str
    metric_type: str
    value: float
    unit: str = "ms"
    status: str = "ok"
    component: str = "core"
    created_at: str = ""
    threshold_warning: float | None = None
    threshold_critical: float | None = None
    details: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CacheEntry:
    id: str
    key: str
    namespace: str
    fingerprint: str
    value: Any
    created_at: str
    updated_at: str
    status: str = "fresh"
    ttl_seconds: int | None = None
    size_bytes: int = 0
    hits: int = 0
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OptimizationRecommendation:
    id: str
    component: str
    title: str
    description: str
    severity: str = "warning"
    created_at: str = ""
    metric_id: str = ""


@dataclass(frozen=True)
class PerformanceSummary:
    metrics: int
    warnings: int
    critical: int
    cache_entries: int
    cache_hits: int
    stale_cache_entries: int
    recommendations: int
    slowest_metric_name: str = ""
    slowest_metric_value: float = 0.0


def normalize_performance_metric(raw: PerformanceMetric | Mapping[str, Any]) -> PerformanceMetric:
    if isinstance(raw, PerformanceMetric):
        metric = raw
    elif isinstance(raw, Mapping):
        name = _clean_text(raw.get("name"), "Название метрики", required=True)
        metric_type = _normalize_metric_type(raw.get("metric_type") or raw.get("type") or "custom")
        value = _to_float(raw.get("value", 0), "Значение метрики")
        warning = raw.get("threshold_warning")
        critical = raw.get("threshold_critical")
        metric = PerformanceMetric(
            id=_clean_text(raw.get("id"), "ID метрики", max_length=120) or _safe_id("metric", (name, metric_type, raw.get("component", "core"), _utc_now())),
            name=name,
            metric_type=metric_type,
            value=value,
            unit=_clean_text(raw.get("unit") or "ms", "Единица", max_length=40),
            status=_normalize_status(raw.get("status") or classify_metric_status(value, warning, critical)),
            component=_clean_text(raw.get("component") or "core", "Компонент", max_length=120),
            created_at=_clean_text(raw.get("created_at") or _utc_now(), "Дата", max_length=80),
            threshold_warning=None if warning is None else _to_float(warning, "Warning threshold"),
            threshold_critical=None if critical is None else _to_float(critical, "Critical threshold"),
            details=raw.get("details", {}) if isinstance(raw.get("details", {}), Mapping) else {},
        )
    else:
        raise TypeError("Performance metric должен быть PerformanceMetric или mapping.")

    return PerformanceMetric(
        id=_clean_text(metric.id, "ID метрики", max_length=120, required=True),
        name=_clean_text(metric.name, "Название метрики", required=True),
        metric_type=_normalize_metric_type(metric.metric_type),
        value=_to_float(metric.value, "Значение метрики"),
        unit=_clean_text(metric.unit or "ms", "Единица", max_length=40),
        status=_normalize_status(metric.status),
        component=_clean_text(metric.component or "core", "Компонент", max_length=120),
        created_at=_clean_text(metric.created_at or _utc_now(), "Дата", max_length=80),
        threshold_warning=metric.threshold_warning,
        threshold_critical=metric.threshold_critical,
        details=metric.details if isinstance(metric.details, Mapping) else {},
    )


def metric_to_dict(metric: PerformanceMetric) -> dict[str, Any]:
    normalized = normalize_performance_metric(metric)
    return {
        "id": normalized.id,
        "name": normalized.name,
        "metric_type": normalized.metric_type,
        "value": normalized.value,
        "unit": normalized.unit,
        "status": normalized.status,
        "component": normalized.component,
        "created_at": normalized.created_at,
        "threshold_warning": normalized.threshold_warning,
        "threshold_critical": normalized.threshold_critical,
        "details": dict(normalized.details),
    }


def classify_metric_status(value: float, threshold_warning: Any = None, threshold_critical: Any = None) -> str:
    numeric = _to_float(value, "Значение метрики")
    critical = None if threshold_critical is None else _to_float(threshold_critical, "Critical threshold")
    warning = None if threshold_warning is None else _to_float(threshold_warning, "Warning threshold")
    if critical is not None and numeric >= critical:
        return "critical"
    if warning is not None and numeric >= warning:
        return "warning"
    return "ok"


def list_performance_metrics(root: Path | str, project_id: str, *, component: str = "", metric_type: str = "") -> tuple[PerformanceMetric, ...]:
    payload = _payload(root, project_id)
    result: list[PerformanceMetric] = []
    for item in payload.get("metrics", []):
        if not isinstance(item, Mapping):
            continue
        metric = normalize_performance_metric(item)
        if component and metric.component != component:
            continue
        if metric_type and metric.metric_type != metric_type:
            continue
        result.append(metric)
    return tuple(result)


def record_performance_metric(root: Path | str, project_id: str, metric: PerformanceMetric | Mapping[str, Any]) -> PerformanceMetric:
    safe_id = safe_project_id(project_id)
    normalized = normalize_performance_metric(metric)
    payload = _payload(root, safe_id)
    metrics = [item for item in payload.get("metrics", []) if isinstance(item, Mapping) and item.get("id") != normalized.id]
    metrics.insert(0, metric_to_dict(normalized))
    payload["metrics"] = metrics[:1000]
    _json_write(_performance_path(root, safe_id), payload)
    append_project_history(
        root,
        safe_id,
        "performance.metric.recorded",
        f"Recorded performance metric: {normalized.name}",
        object_type="performance_metric",
        object_id=normalized.id,
    )
    return normalized


@contextmanager
def measure_performance(
    root: Path | str,
    project_id: str,
    name: str,
    *,
    component: str = "core",
    threshold_warning_ms: float | None = None,
    threshold_critical_ms: float | None = None,
    details: Mapping[str, Any] | None = None,
) -> Iterator[dict[str, Any]]:
    """Context manager that records elapsed milliseconds even if the block fails."""
    started = time.perf_counter()
    state: dict[str, Any] = {"metric": None, "error": None}
    try:
        yield state
    except Exception as exc:  # pragma: no cover - re-raised intentionally
        state["error"] = str(exc)
        raise
    finally:
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        metric = record_performance_metric(
            root,
            project_id,
            {
                "name": name,
                "metric_type": "timer",
                "value": elapsed_ms,
                "unit": "ms",
                "component": component,
                "threshold_warning": threshold_warning_ms,
                "threshold_critical": threshold_critical_ms,
                "details": {**(dict(details or {})), **({"error": state["error"]} if state["error"] else {})},
            },
        )
        state["metric"] = metric


def _cache_value_size(value: Any) -> int:
    try:
        return len(json.dumps(value, ensure_ascii=False, default=str).encode("utf-8"))
    except (TypeError, ValueError):
        return len(str(value).encode("utf-8"))


def _cache_fingerprint(value: Any) -> str:
    try:
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    except (TypeError, ValueError):
        raw = str(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def cache_value(
    root: Path | str,
    project_id: str,
    namespace: str,
    key: str,
    value: Any,
    *,
    ttl_seconds: int | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> CacheEntry:
    safe_id = safe_project_id(project_id)
    now = _utc_now()
    clean_namespace = _clean_text(namespace, "Namespace кэша", max_length=120, required=True)
    clean_key = _clean_text(key, "Ключ кэша", max_length=240, required=True)
    cache_id = _safe_id("cache", (clean_namespace, clean_key))
    payload = _payload(root, safe_id)
    entries = [item for item in payload.get("cache", []) if isinstance(item, Mapping) and item.get("id") != cache_id]
    previous = next((item for item in payload.get("cache", []) if isinstance(item, Mapping) and item.get("id") == cache_id), {})
    entry = CacheEntry(
        id=cache_id,
        key=clean_key,
        namespace=clean_namespace,
        fingerprint=_cache_fingerprint(value),
        value=value,
        created_at=str(previous.get("created_at") or now),
        updated_at=now,
        status="fresh",
        ttl_seconds=ttl_seconds,
        size_bytes=_cache_value_size(value),
        hits=int(previous.get("hits", 0) or 0),
        metadata=metadata or {},
    )
    entries.insert(0, cache_entry_to_dict(entry))
    payload["cache"] = entries[:500]
    _json_write(_performance_path(root, safe_id), payload)
    return entry


def cache_entry_to_dict(entry: CacheEntry) -> dict[str, Any]:
    status = _normalize_cache_status(entry.status)
    return {
        "id": entry.id,
        "key": entry.key,
        "namespace": entry.namespace,
        "fingerprint": entry.fingerprint,
        "value": entry.value,
        "created_at": entry.created_at,
        "updated_at": entry.updated_at,
        "status": status,
        "ttl_seconds": entry.ttl_seconds,
        "size_bytes": int(entry.size_bytes),
        "hits": int(entry.hits),
        "metadata": dict(entry.metadata),
    }


def _cache_entry_from_dict(raw: Mapping[str, Any]) -> CacheEntry:
    return CacheEntry(
        id=_clean_text(raw.get("id"), "Cache ID", required=True),
        key=_clean_text(raw.get("key"), "Ключ", required=True),
        namespace=_clean_text(raw.get("namespace"), "Namespace", required=True),
        fingerprint=_clean_text(raw.get("fingerprint"), "Fingerprint", max_length=120),
        value=raw.get("value"),
        created_at=_clean_text(raw.get("created_at") or _utc_now(), "Дата создания", max_length=80),
        updated_at=_clean_text(raw.get("updated_at") or _utc_now(), "Дата обновления", max_length=80),
        status=_normalize_cache_status(raw.get("status") or "fresh"),
        ttl_seconds=None if raw.get("ttl_seconds") is None else int(raw.get("ttl_seconds")),
        size_bytes=int(raw.get("size_bytes", 0) or 0),
        hits=int(raw.get("hits", 0) or 0),
        metadata=raw.get("metadata", {}) if isinstance(raw.get("metadata", {}), Mapping) else {},
    )


def get_cached_value(root: Path | str, project_id: str, namespace: str, key: str) -> Any:
    safe_id = safe_project_id(project_id)
    clean_namespace = _clean_text(namespace, "Namespace кэша", max_length=120, required=True)
    clean_key = _clean_text(key, "Ключ кэша", max_length=240, required=True)
    cache_id = _safe_id("cache", (clean_namespace, clean_key))
    payload = _payload(root, safe_id)
    entries = []
    found: CacheEntry | None = None
    now_ts = time.time()
    for item in payload.get("cache", []):
        if not isinstance(item, Mapping):
            continue
        entry = _cache_entry_from_dict(item)
        if entry.id == cache_id and entry.status == "fresh":
            # ISO Z parsing is intentionally conservative; malformed dates remain readable.
            is_expired = False
            if entry.ttl_seconds is not None:
                try:
                    updated_dt = datetime.fromisoformat(entry.updated_at.replace("Z", "+00:00"))
                    is_expired = now_ts - updated_dt.timestamp() > entry.ttl_seconds
                except ValueError:
                    is_expired = False
            if is_expired:
                entry = CacheEntry(**{**entry.__dict__, "status": "stale"})
            else:
                entry = CacheEntry(**{**entry.__dict__, "hits": entry.hits + 1})
                found = entry
        entries.append(cache_entry_to_dict(entry))
    payload["cache"] = entries
    _json_write(_performance_path(root, safe_id), payload)
    return None if found is None else found.value


def invalidate_cache(root: Path | str, project_id: str, *, namespace: str = "", key_prefix: str = "") -> int:
    safe_id = safe_project_id(project_id)
    payload = _payload(root, safe_id)
    changed = 0
    entries = []
    for item in payload.get("cache", []):
        if not isinstance(item, Mapping):
            continue
        entry = _cache_entry_from_dict(item)
        namespace_match = not namespace or entry.namespace == namespace
        key_match = not key_prefix or entry.key.startswith(key_prefix)
        if namespace_match and key_match and entry.status != "invalidated":
            entry = CacheEntry(**{**entry.__dict__, "status": "invalidated", "updated_at": _utc_now()})
            changed += 1
        entries.append(cache_entry_to_dict(entry))
    payload["cache"] = entries
    _json_write(_performance_path(root, safe_id), payload)
    if changed:
        append_project_history(root, safe_id, "performance.cache.invalidated", f"Invalidated cache entries: {changed}", object_type="performance_cache")
    return changed


def list_cache_entries(root: Path | str, project_id: str, *, namespace: str = "", status: str = "") -> tuple[CacheEntry, ...]:
    payload = _payload(root, project_id)
    result: list[CacheEntry] = []
    for item in payload.get("cache", []):
        if not isinstance(item, Mapping):
            continue
        entry = _cache_entry_from_dict(item)
        if namespace and entry.namespace != namespace:
            continue
        if status and entry.status != status:
            continue
        result.append(entry)
    return tuple(result)


def estimate_table_memory_bytes(table: Any) -> int:
    """Estimate DataFrame-like or list-of-dicts memory usage without requiring pandas."""
    if hasattr(table, "memory_usage"):
        try:
            usage = table.memory_usage(deep=True)
            if hasattr(usage, "sum"):
                return int(usage.sum())
            return int(usage)
        except Exception:  # pragma: no cover - third-party objects can fail unpredictably
            pass
    return _cache_value_size(table)


def build_optimization_recommendations(metrics: Sequence[PerformanceMetric]) -> tuple[OptimizationRecommendation, ...]:
    recommendations: list[OptimizationRecommendation] = []
    for metric in metrics:
        normalized = normalize_performance_metric(metric)
        if normalized.status == "ok":
            continue
        if normalized.metric_type == "timer":
            title = "Оптимизировать медленную операцию"
            description = f"Операция '{normalized.name}' заняла {normalized.value:.2f} {normalized.unit}; проверьте кэширование, векторизацию Pandas и ленивую загрузку."
        elif normalized.metric_type == "memory":
            title = "Снизить потребление памяти"
            description = f"Компонент '{normalized.component}' использует {normalized.value:.2f} {normalized.unit}; проверьте downcast типов, chunked reading и очистку промежуточных DataFrame."
        elif normalized.metric_type == "render":
            title = "Оптимизировать рендеринг"
            description = f"Рендер '{normalized.name}' превысил порог; сократите число точек, включите resample/decimation или используйте cached preview."
        else:
            title = "Проверить производительность компонента"
            description = f"Метрика '{normalized.name}' имеет статус {normalized.status}; требуется инженерная проверка."
        recommendations.append(
            OptimizationRecommendation(
                id=_safe_id("recommendation", (normalized.id, normalized.status, title)),
                component=normalized.component,
                title=title,
                description=description,
                severity=normalized.status,
                created_at=_utc_now(),
                metric_id=normalized.id,
            )
        )
    return tuple(recommendations)


def summarize_performance(root: Path | str, project_id: str) -> PerformanceSummary:
    metrics = list_performance_metrics(root, project_id)
    cache_entries = list_cache_entries(root, project_id)
    recommendations = build_optimization_recommendations(metrics)
    slowest = max(metrics, key=lambda item: item.value, default=None)
    return PerformanceSummary(
        metrics=len(metrics),
        warnings=sum(1 for item in metrics if item.status == "warning"),
        critical=sum(1 for item in metrics if item.status == "critical"),
        cache_entries=len(cache_entries),
        cache_hits=sum(item.hits for item in cache_entries),
        stale_cache_entries=sum(1 for item in cache_entries if item.status in {"stale", "invalidated"}),
        recommendations=len(recommendations),
        slowest_metric_name="" if slowest is None else slowest.name,
        slowest_metric_value=0.0 if slowest is None else slowest.value,
    )


def build_performance_metric_table(metrics: Sequence[PerformanceMetric]) -> list[dict[str, Any]]:
    return [
        {
            "ID": metric.id,
            "Компонент": metric.component,
            "Метрика": metric.name,
            "Тип": metric.metric_type,
            "Значение": round(metric.value, 3),
            "Единица": metric.unit,
            "Статус": metric.status,
            "Дата": metric.created_at,
        }
        for metric in metrics
    ]


def build_cache_entry_table(entries: Sequence[CacheEntry]) -> list[dict[str, Any]]:
    return [
        {
            "ID": entry.id,
            "Namespace": entry.namespace,
            "Ключ": entry.key,
            "Статус": entry.status,
            "Размер, байт": entry.size_bytes,
            "Hits": entry.hits,
            "TTL, сек": entry.ttl_seconds,
            "Обновлено": entry.updated_at,
        }
        for entry in entries
    ]


def build_optimization_recommendation_table(recommendations: Sequence[OptimizationRecommendation]) -> list[dict[str, Any]]:
    return [
        {
            "ID": item.id,
            "Компонент": item.component,
            "Уровень": item.severity,
            "Рекомендация": item.title,
            "Описание": item.description,
            "Metric ID": item.metric_id,
        }
        for item in recommendations
    ]


def build_performance_manifest(root: Path | str, project_id: str) -> dict[str, Any]:
    metrics = list_performance_metrics(root, project_id)
    cache_entries = list_cache_entries(root, project_id)
    recommendations = build_optimization_recommendations(metrics)
    summary = summarize_performance(root, project_id)
    return {
        "schema": PERFORMANCE_SCHEMA,
        "project_id": safe_project_id(project_id),
        "generated_at": _utc_now(),
        "summary": summary.__dict__,
        "metrics": [metric_to_dict(metric) for metric in metrics],
        "cache": [cache_entry_to_dict(entry) for entry in cache_entries],
        "recommendations": [item.__dict__ for item in recommendations],
    }
