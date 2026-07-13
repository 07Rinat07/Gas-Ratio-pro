"""Lazy workspace route registry.

Only the requested route is resolved and invoked. The registry keeps route
metadata separate from renderer execution, making it straightforward to audit
that inactive workspaces do not construct figures or reports.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping


@dataclass(frozen=True, slots=True)
class WorkspaceRoute:
    route_id: str
    provider: str
    renderer: Callable[[Any], Any]
    expected_controls: tuple[str, ...] = ()


class LazyWorkspaceRegistry:
    def __init__(self, routes: Mapping[str, WorkspaceRoute]) -> None:
        self._routes = dict(routes)

    def resolve(self, route_id: str) -> WorkspaceRoute | None:
        return self._routes.get(str(route_id or "").strip())

    def route_ids(self) -> tuple[str, ...]:
        return tuple(self._routes)

    def __len__(self) -> int:
        return len(self._routes)
