"""Runtime diagnostics for Modern Workbench integration boundaries.

The module stores only compact, serializable incident metadata in application
state. Full tracebacks stay in the rotating application log.
"""
from __future__ import annotations

from datetime import datetime, timezone
import os
import traceback
import uuid
from typing import Any, MutableMapping

from core.logging_config import configure_logging, safe_log_value

DIAGNOSTIC_INCIDENTS_KEY = "workbench.runtime_diagnostics.incidents"
DIAGNOSTIC_BINDING_KEY = "workbench.runtime_diagnostics.binding"
DIAGNOSTIC_MAX_INCIDENTS = 40
DIAGNOSTICS_ENV_VAR = "GAS_RATIO_PRO_DIAGNOSTICS"
_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})


def diagnostics_enabled(environ: dict[str, str] | None = None) -> bool:
    source = os.environ if environ is None else environ
    return str(source.get(DIAGNOSTICS_ENV_VAR, "")).strip().lower() in _TRUE_VALUES


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_correlation_id(prefix: str = "wb") -> str:
    token = uuid.uuid4().hex[:10]
    clean_prefix = "".join(ch for ch in str(prefix) if ch.isalnum() or ch in "-_" ).strip("-_") or "wb"
    return f"{clean_prefix}-{token}"


def record_binding_state(
    state: MutableMapping[str, Any],
    *,
    route_id: str,
    renderer: str,
    provider: str,
    module_loaded: bool,
    project_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record = {
        "timestamp": _now_iso(),
        "route_id": str(route_id or ""),
        "renderer": str(renderer or ""),
        "provider": str(provider or ""),
        "module_loaded": bool(module_loaded),
        "project_id": str(project_id or ""),
        "details": dict(details or {}),
    }
    state[DIAGNOSTIC_BINDING_KEY] = record
    return record


def record_runtime_exception(
    state: MutableMapping[str, Any],
    exc: BaseException,
    *,
    boundary: str,
    operation: str,
    context: dict[str, Any] | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    correlation = correlation_id or new_correlation_id("err")
    logger = configure_logging()
    compact_context = {str(k): safe_log_value(v, 240) for k, v in dict(context or {}).items()}
    logger.error(
        "workbench_runtime_exception correlation_id=%s boundary=%s operation=%s context=%s\n%s",
        correlation,
        safe_log_value(boundary),
        safe_log_value(operation),
        compact_context,
        "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
    )
    incident = {
        "correlation_id": correlation,
        "timestamp": _now_iso(),
        "boundary": str(boundary or ""),
        "operation": str(operation or ""),
        "exception_type": type(exc).__name__,
        "message": safe_log_value(exc, 500),
        "context": compact_context,
    }
    incidents = list(state.get(DIAGNOSTIC_INCIDENTS_KEY, ()))
    incidents.append(incident)
    state[DIAGNOSTIC_INCIDENTS_KEY] = incidents[-DIAGNOSTIC_MAX_INCIDENTS:]
    return incident


def diagnostics_snapshot(state: MutableMapping[str, Any]) -> dict[str, Any]:
    return {
        "binding": dict(state.get(DIAGNOSTIC_BINDING_KEY, {}) or {}),
        "incidents": tuple(dict(item) for item in state.get(DIAGNOSTIC_INCIDENTS_KEY, ()) if isinstance(item, dict)),
    }
