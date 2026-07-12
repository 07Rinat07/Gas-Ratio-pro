from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MethodDiagnostic:
    severity: str
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class MethodResult:
    """Normalized result returned by every interpretation method."""

    method: str
    classification: str
    confidence: float
    support: float
    method_id: str = ""
    version: str = ""
    evidence: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    recommendations: tuple[str, ...] = ()
    diagnostics: tuple[MethodDiagnostic, ...] = ()
    explanation: str = ""
    available: bool = True
