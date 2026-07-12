from __future__ import annotations

import math

from core.methods.base import BaseMethod
from core.methods.context import MethodContext
from core.methods.result import MethodDiagnostic, MethodResult


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


class HaworthMethod(BaseMethod):
    method_id = "haworth_mud_gas"
    name = "Haworth"
    version = "1.0"

    def analyze(self, context: MethodContext) -> MethodResult:
        raw = context.interval.average_ch
        try:
            ch_value = float(raw)
        except (TypeError, ValueError):
            ch_value = math.nan
        if not math.isfinite(ch_value):
            message = "Ch отсутствует в выбранном интервале."
            return MethodResult(
                method=self.name,
                method_id=self.method_id,
                version=self.version,
                classification=_normalize_fluid(context.interval.fluid_type),
                confidence=0.0,
                support=0.0,
                limitations=(message,),
                diagnostics=(MethodDiagnostic("WARNING", "HAWORTH_CH_MISSING", message),),
                explanation=message,
                available=False,
            )
        support = min(100.0, max(35.0, float(context.interval.confidence_score)))
        return MethodResult(
            method=self.name,
            method_id=self.method_id,
            version=self.version,
            classification=_normalize_fluid(context.interval.fluid_type),
            confidence=support,
            support=support,
            evidence=(f"Медиана/среднее Ch: {ch_value:.3g}.",),
            explanation=f"Haworth использует Ch={ch_value:.3g} как поддерживающий признак интервала.",
            available=True,
        )
