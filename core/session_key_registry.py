"""Central ownership and lifecycle registry for Streamlit session-state keys.

The registry classifies keys without reading or copying their values.  It gives
cleanup and diagnostics one source of truth instead of duplicating prefix lists
across modules.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

SESSION_KEY_REGISTRY_SCHEMA = "gas-ratio-pro/session-key-registry/v1"


@dataclass(frozen=True, slots=True)
class SessionKeyRule:
    pattern: str
    owner: str
    lifecycle: str
    prefix: bool = True

    def matches(self, key: str) -> bool:
        return key.startswith(self.pattern) if self.prefix else key == self.pattern


@dataclass(frozen=True, slots=True)
class SessionKeyDescriptor:
    key: str
    owner: str
    lifecycle: str
    registered: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "key": self.key,
            "owner": self.owner,
            "lifecycle": self.lifecycle,
            "registered": self.registered,
        }


class SessionKeyRegistry:
    """Immutable key-classification rules ordered from specific to general."""

    def __init__(self, rules: Iterable[SessionKeyRule]) -> None:
        self._rules = tuple(rules)

    @property
    def rules(self) -> tuple[SessionKeyRule, ...]:
        return self._rules

    def describe(self, key: str) -> SessionKeyDescriptor:
        clean_key = str(key)
        for rule in self._rules:
            if rule.matches(clean_key):
                return SessionKeyDescriptor(clean_key, rule.owner, rule.lifecycle, True)
        return SessionKeyDescriptor(clean_key, "unknown", "session", False)

    def is_transient(self, key: str) -> bool:
        return self.describe(key).lifecycle in {"workspace", "las", "well", "project", "transient"}

    def ownership_counts(self, keys: Iterable[str]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for key in keys:
            owner = self.describe(str(key)).owner
            counts[owner] = counts.get(owner, 0) + 1
        return dict(sorted(counts.items()))

    def lifecycle_counts(self, keys: Iterable[str]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for key in keys:
            lifecycle = self.describe(str(key)).lifecycle
            counts[lifecycle] = counts.get(lifecycle, 0) + 1
        return dict(sorted(counts.items()))


def build_default_session_key_registry(
    *,
    transient_prefixes: Sequence[str],
    transient_keys: Sequence[str],
    preserved_keys: Sequence[str],
) -> SessionKeyRegistry:
    rules: list[SessionKeyRule] = [
        SessionKeyRule("runtime::", "runtime", "runtime", prefix=True),
        SessionKeyRule("workbench.", "workbench", "session", prefix=True),
        SessionKeyRule("workspace.", "workspace", "workspace", prefix=True),
    ]
    rules.extend(SessionKeyRule(str(key), "application", "session", prefix=False) for key in preserved_keys)
    rules.extend(SessionKeyRule(str(key), "application", "transient", prefix=False) for key in transient_keys)
    rules.extend(SessionKeyRule(str(prefix), "application", "transient", prefix=True) for prefix in transient_prefixes)
    return SessionKeyRegistry(rules)
