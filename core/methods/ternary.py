from __future__ import annotations

from core.methods.base import BaseMethod, MethodCapabilities
from core.methods.context import MethodContext
from core.methods.result import MethodDiagnostic, MethodResult
from palettes.ternary import analyze_ternary_interval


def _normalize_fluid(value: object) -> str:
    text = str(value or "").strip().lower()
    if "condens" in text or "конденсат" in text:
        return "condensate"
    if "oil" in text or "нефт" in text:
        return "oil"
    if "gas" in text or "газ" in text:
        return "gas"
    if "water" in text or "вод" in text:
        return "water"
    if any(token in text for token in ("mixed", "transition", "смеш", "переход")):
        return "mixed"
    return "unknown"


class TernaryMethod(BaseMethod):
    method_id = "ternary_gas_composition"
    name = "Ternary"
    version = "2.0"
    capabilities = MethodCapabilities(supports_plot=True)

    def analyze(self, context: MethodContext) -> MethodResult:
        summary = analyze_ternary_interval(
            context.frame,
            context.selected_row,
            regions=context.ternary_regions,
        )
        available = bool(summary.valid_measurements)
        support = float(summary.region_support_percent if available else 0.0)
        limitations: list[str] = []
        diagnostics: list[MethodDiagnostic] = []
        if not available:
            limitations.append("Недостаточно совместно валидных C2, C3 и nC4 для ternary-анализа.")
            diagnostics.append(MethodDiagnostic("WARNING", "TERNARY_NO_VALID_POINTS", limitations[-1]))
        elif float(summary.completeness_percent) < 60.0:
            limitations.append(f"Полнота ternary-точек составляет {summary.completeness_percent:.1f}%.")
            diagnostics.append(MethodDiagnostic("WARNING", "TERNARY_LOW_COMPLETENESS", limitations[-1]))
        return MethodResult(
            method=self.name,
            method_id=self.method_id,
            version=self.version,
            classification=_normalize_fluid(summary.dominant_region),
            confidence=support,
            support=support,
            evidence=(f"Валидных точек: {summary.valid_measurements} из {summary.total_measurements}.",),
            limitations=tuple(limitations),
            diagnostics=tuple(diagnostics),
            explanation=str(summary.conclusion or ""),
            available=available,
        )
