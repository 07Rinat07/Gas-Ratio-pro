from __future__ import annotations

from collections import OrderedDict
from typing import Iterable

from core.methods.base import BaseMethod
from core.methods.context import MethodContext
from core.methods.result import MethodResult


class MethodRegistry:
    """Ordered registry used by the Expert Engine and downstream reports."""

    def __init__(self, methods: Iterable[BaseMethod] = ()) -> None:
        self._methods: OrderedDict[str, BaseMethod] = OrderedDict()
        for method in methods:
            self.register(method)

    def register(self, method: BaseMethod, *, replace: bool = False) -> None:
        method_id = str(method.method_id).strip()
        if not method_id:
            raise ValueError("Method id must not be empty.")
        if method_id in self._methods and not replace:
            raise ValueError(f"Method is already registered: {method_id}")
        self._methods[method_id] = method

    def get(self, method_id: str) -> BaseMethod:
        try:
            return self._methods[str(method_id)]
        except KeyError as exc:
            raise KeyError(f"Method is not registered: {method_id}") from exc

    def methods(self) -> tuple[BaseMethod, ...]:
        return tuple(self._methods.values())

    def analyze_all(self, context: MethodContext) -> tuple[MethodResult, ...]:
        return tuple(method.analyze(context) for method in self._methods.values())
