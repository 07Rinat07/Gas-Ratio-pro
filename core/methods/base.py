from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from core.methods.context import MethodContext
from core.methods.result import MethodResult


@dataclass(frozen=True, slots=True)
class MethodCapabilities:
    supports_intervals: bool = True
    supports_qc: bool = True
    supports_export: bool = True
    supports_plot: bool = False


class BaseMethod(ABC):
    method_id: str
    name: str
    version: str
    capabilities: MethodCapabilities = MethodCapabilities()

    @abstractmethod
    def analyze(self, context: MethodContext) -> MethodResult:
        raise NotImplementedError
