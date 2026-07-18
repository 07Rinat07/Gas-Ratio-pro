"""Read-only localized diagnostics for Stage 5.1 validation and calibration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from services.petrophysical_calibration_application_service import PetrophysicalCalibrationReport
from services.petrophysical_validation_application_service import PetrophysicalValidationReport


@dataclass(frozen=True, slots=True)
class PetrophysicalDiagnosticRow:
    method_id: str
    validation_status: str
    calibration_status: str
    report_policy: str
    rmse: float | None
    uncertainty_width: float | None
    final_report_status: str


@dataclass(frozen=True, slots=True)
class PetrophysicalDiagnosticsView:
    locale: str
    title: str
    summary: str
    validation_gate_id: str
    calibration_gate_id: str
    validation_passed: bool
    calibration_passed: bool
    final_report_eligible_count: int
    calibrated_count: int
    rows: tuple[PetrophysicalDiagnosticRow, ...]
    labels: Mapping[str, str]
    disclaimer: str


_COPY: Mapping[str, Mapping[str, str]] = {
    "ru": {
        "title": "Петрофизический validation gate",
        "summary": "Численная проверка: {validated}/{total}; полевая калибровка: {calibrated}/{total}; допущено к финальному отчёту: {eligible}/{total}.",
        "passed": "пройдено",
        "failed": "ошибка",
        "required": "калиброван",
        "diagnostic": "только диагностика",
        "blocked": "заблокирован",
        "eligible": "разрешён",
        "disclaimer": "Диапазоны sensitivity/uncertainty являются детерминированной диагностикой и не заменяют операторские данные керна, SCAL, пластовой воды и испытаний.",
        "method": "Метод", "validation": "Численная проверка", "calibration": "Калибровка", "policy": "Политика отчёта", "rmse": "RMSE", "uncertainty": "Ширина envelope", "final": "Финальный отчёт",
    },
    "kk": {
        "title": "Петрофизикалық validation gate",
        "summary": "Сандық тексеру: {validated}/{total}; далалық калибрлеу: {calibrated}/{total}; қорытынды есепке рұқсат: {eligible}/{total}.",
        "passed": "өтті",
        "failed": "қате",
        "required": "калибрленген",
        "diagnostic": "тек диагностика",
        "blocked": "бұғатталған",
        "eligible": "рұқсат етілген",
        "disclaimer": "Sensitivity/uncertainty диапазондары детерминделген диагностика болып табылады және оператордың керн, SCAL, қабат суы мен сынақ деректерін алмастырмайды.",
        "method": "Әдіс", "validation": "Сандық тексеру", "calibration": "Калибрлеу", "policy": "Есеп саясаты", "rmse": "RMSE", "uncertainty": "Envelope ені", "final": "Қорытынды есеп",
    },
    "en": {
        "title": "Petrophysical validation gate",
        "summary": "Numerical validation: {validated}/{total}; field calibration: {calibrated}/{total}; final-report eligible: {eligible}/{total}.",
        "passed": "passed",
        "failed": "failed",
        "required": "calibrated",
        "diagnostic": "diagnostic only",
        "blocked": "blocked",
        "eligible": "eligible",
        "disclaimer": "Sensitivity/uncertainty envelopes are deterministic diagnostics and do not replace operator-owned core, SCAL, formation-water or test data.",
        "method": "Method", "validation": "Numerical validation", "calibration": "Calibration", "policy": "Report policy", "rmse": "RMSE", "uncertainty": "Envelope width", "final": "Final report",
    },
}


def build_petrophysical_diagnostics_view(
    validation: PetrophysicalValidationReport,
    calibration: PetrophysicalCalibrationReport,
    *,
    locale: str = "ru",
) -> PetrophysicalDiagnosticsView:
    language = str(locale).lower().split("-")[0]
    copy = _COPY.get(language, _COPY["en"])
    validation_by_id = {item.method_id: item for item in validation.methods}
    calibration_by_id = {item.method_id: item for item in calibration.methods}
    rows: list[PetrophysicalDiagnosticRow] = []
    for method_id in sorted(validation_by_id):
        validated = validation_by_id[method_id]
        calibrated = calibration_by_id.get(method_id)
        if calibrated is None:
            calibration_status = copy["failed"]
            rmse = None
            width = None
        elif calibrated.calibration_policy == "diagnostic_only":
            calibration_status = copy["diagnostic"]
            rmse = calibrated.metrics.rmse
            width = calibrated.uncertainty_envelope.max_width
        else:
            calibration_status = copy["required"] if calibrated.passed else copy["failed"]
            rmse = calibrated.metrics.rmse
            width = calibrated.uncertainty_envelope.max_width
        final_status = copy["eligible"] if validated.final_report_eligible and bool(calibrated and calibrated.final_report_calibrated) else copy["blocked"]
        rows.append(
            PetrophysicalDiagnosticRow(
                method_id=method_id,
                validation_status=copy["passed"] if validated.passed else copy["failed"],
                calibration_status=calibration_status,
                report_policy=validated.report_policy,
                rmse=rmse,
                uncertainty_width=width,
                final_report_status=final_status,
            )
        )
    total = len(rows)
    return PetrophysicalDiagnosticsView(
        locale=language,
        title=copy["title"],
        summary=copy["summary"].format(
            validated=validation.validated_method_count,
            calibrated=calibration.calibrated_method_count,
            eligible=validation.final_report_eligible_count,
            total=total,
        ),
        validation_gate_id=validation.gate_id,
        calibration_gate_id=calibration.gate_id,
        validation_passed=validation.passed,
        calibration_passed=calibration.passed,
        final_report_eligible_count=validation.final_report_eligible_count,
        calibrated_count=calibration.calibrated_method_count,
        rows=tuple(rows),
        labels={key: copy[key] for key in ("method", "validation", "calibration", "policy", "rmse", "uncertainty", "final")},
        disclaimer=copy["disclaimer"],
    )
