"""Single-cycle Streamlit rerun coordination.

Streamlit normally stops execution when ``st.rerun`` is called, but tests,
compatibility wrappers and future fragments may not.  This coordinator keeps a
small state-backed gate so one render cycle can request at most one full-app
rerun while preserving the first reason for diagnostics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, MutableMapping

RERUN_CYCLE_KEY = "runtime::rerun_cycle"
RERUN_REQUEST_KEY = "runtime::rerun_requested"
RERUN_HISTORY_KEY = "runtime::rerun_history"
RERUN_HISTORY_LIMIT = 32


@dataclass(frozen=True, slots=True)
class RerunDecision:
    allowed: bool
    cycle: int
    reason: str
    source: str


def begin_rerun_cycle(state: MutableMapping[str, Any]) -> int:
    """Start a new UI render cycle and clear only the per-cycle rerun gate."""

    cycle = int(state.get(RERUN_CYCLE_KEY, 0) or 0) + 1
    state[RERUN_CYCLE_KEY] = cycle
    state.pop(RERUN_REQUEST_KEY, None)
    return cycle


def request_rerun(
    state: MutableMapping[str, Any],
    reason: str,
    *,
    source: str = "streamlit_app",
) -> RerunDecision:
    """Allow the first full rerun request in the active render cycle only."""

    cycle = int(state.get(RERUN_CYCLE_KEY, 0) or 0)
    normalized_reason = str(reason or "ui_refresh")
    normalized_source = str(source or "streamlit_app")
    existing = state.get(RERUN_REQUEST_KEY)
    if isinstance(existing, dict) and int(existing.get("cycle", -1)) == cycle:
        return RerunDecision(
            allowed=False,
            cycle=cycle,
            reason=str(existing.get("reason", normalized_reason)),
            source=str(existing.get("source", normalized_source)),
        )

    record = {
        "cycle": cycle,
        "reason": normalized_reason,
        "source": normalized_source,
    }
    state[RERUN_REQUEST_KEY] = record
    history = list(state.get(RERUN_HISTORY_KEY, ()) or ())
    history.append(record)
    state[RERUN_HISTORY_KEY] = history[-RERUN_HISTORY_LIMIT:]
    return RerunDecision(True, cycle, normalized_reason, normalized_source)


def rerun_history(state: MutableMapping[str, Any]) -> tuple[dict[str, Any], ...]:
    return tuple(dict(item) for item in state.get(RERUN_HISTORY_KEY, ()) or ())
