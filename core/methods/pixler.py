from __future__ import annotations

from core.methods.base import BaseMethod, MethodCapabilities
from core.methods.context import MethodContext
from core.methods.result import MethodDiagnostic, MethodResult
from palettes.pixler import analyze_pixler_interval


def _normalize_fluid(value: object) -> str:
    text = str(value or "").strip().lower()
    if "condens" in text or "конденсат" in text:
        return "condensate"
    if "oil" in text or "нефт" in text:
        return "oil"
    if "dry gas" in text or "сух" in text:
        return "dry_gas"
    if "gas" in text or "газ" in text:
        return "gas"
    if "water" in text or "вод" in text:
        return "water"
    if any(token in text for token in ("mixed", "transition", "смеш", "переход")):
        return "mixed"
    return "unknown"


class PixlerMethod(BaseMethod):
    method_id = "pixler_gas_ratio"
    name = "Pixler"
    version = "2.0"
    capabilities = MethodCapabilities(supports_plot=True)

    def analyze(self, context: MethodContext) -> MethodResult:
        summary = analyze_pixler_interval(
            context.frame,
            context.selected_row,
            zones=context.pixler_zones,
        )
        available = bool(summary.valid_measurements)
        support = float(summary.zone_support_percent if available else 0.0)
        limitations: list[str] = []
        diagnostics: list[MethodDiagnostic] = []
        if not available:
            limitations.append("Недостаточно валидных отношений Pixler в выбранном интервале.")
            diagnostics.append(MethodDiagnostic("WARNING", "PIXLER_NO_VALID_RATIOS", limitations[-1]))
        return MethodResult(
            method=self.name,
            method_id=self.method_id,
            version=self.version,
            classification=_normalize_fluid(summary.dominant_zone),
            confidence=support,
            support=support,
            evidence=(f"Валидных отношений: {summary.valid_measurements}.",),
            limitations=tuple(limitations),
            diagnostics=tuple(diagnostics),
            explanation=str(summary.conclusion or ""),
            available=available,
        )
