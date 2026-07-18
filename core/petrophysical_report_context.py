"""Lightweight method provenance carried with calculated data frames."""

from __future__ import annotations

from typing import Any, Iterable

PETROPHYSICAL_METHOD_CONTEXT_KEY = "gas_ratio_petrophysical_method_context"
PETROPHYSICAL_METHOD_CONTEXT_SCHEMA = "gas-ratio-pro/petrophysical-method-context/v1"


def attach_petrophysical_method_context(
    frame: Any,
    method_ids: Iterable[str],
    *,
    source: str,
) -> Any:
    """Attach serializable method provenance without storing service objects."""

    attrs = getattr(frame, "attrs", None)
    if not isinstance(attrs, dict):
        return frame
    existing = attrs.get(PETROPHYSICAL_METHOD_CONTEXT_KEY, {})
    previous = existing.get("method_ids", ()) if isinstance(existing, dict) else ()
    merged = tuple(dict.fromkeys(
        str(item).strip()
        for item in (*tuple(previous), *tuple(method_ids))
        if str(item).strip()
    ))
    attrs[PETROPHYSICAL_METHOD_CONTEXT_KEY] = {
        "schema": PETROPHYSICAL_METHOD_CONTEXT_SCHEMA,
        "method_ids": list(merged),
        "sources": list(dict.fromkeys(
            [*(existing.get("sources", ()) if isinstance(existing, dict) else ()), str(source)]
        )),
    }
    return frame


def petrophysical_method_ids_from_frame(frame: Any) -> tuple[str, ...]:
    attrs = getattr(frame, "attrs", None)
    if not isinstance(attrs, dict):
        return ()
    context = attrs.get(PETROPHYSICAL_METHOD_CONTEXT_KEY)
    if not isinstance(context, dict) or context.get("schema") != PETROPHYSICAL_METHOD_CONTEXT_SCHEMA:
        return ()
    return tuple(dict.fromkeys(
        str(item).strip() for item in context.get("method_ids", ()) if str(item).strip()
    ))
