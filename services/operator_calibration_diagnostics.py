"""Localized read-only view models for Stage 5.2 operator calibration packages."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from services.operator_calibration_package_application_service import (
    OperatorCalibrationComparisonReport,
    OperatorCalibrationPackageRecord,
)


@dataclass(frozen=True, slots=True)
class OperatorCalibrationPackageRow:
    package_id: str
    version: str
    operator_name: str
    legal_status: str
    method_count: int
    final_report_rights: str
    active_status: str
    fingerprint: str


@dataclass(frozen=True, slots=True)
class OperatorCalibrationDiagnosticsView:
    locale: str
    title: str
    summary: str
    disclaimer: str
    labels: Mapping[str, str]
    rows: tuple[OperatorCalibrationPackageRow, ...]
    comparison_summary: str


_COPY: Mapping[str, Mapping[str, str]] = {
    "ru": {
        "title": "Операторские калибровочные пакеты",
        "summary": "Импортировано пакетов: {count}; активный пакет: {active}.",
        "none": "нет",
        "allowed": "разрешено",
        "blocked": "запрещено",
        "active": "активен",
        "inactive": "неактивен",
        "comparison": "Сравнение {comparison}: улучшено {improved}, ухудшено {degraded}, эквивалентно {equivalent}.",
        "no_comparison": "Сравнение калибровок ещё не выполнено.",
        "disclaimer": "Пакет применяется только в указанном проекте. Исходный ZIP и fingerprints неизменяемы; права на данные проверяются повторно перед финальным экспортом.",
        "package": "Пакет", "version": "Версия", "operator": "Оператор", "legal": "Правовой статус", "methods": "Методы", "report": "Финальный отчёт", "status": "Статус", "fingerprint": "Fingerprint",
    },
    "kk": {
        "title": "Операторлық калибрлеу пакеттері",
        "summary": "Импортталған пакеттер: {count}; белсенді пакет: {active}.",
        "none": "жоқ",
        "allowed": "рұқсат етілген",
        "blocked": "тыйым салынған",
        "active": "белсенді",
        "inactive": "белсенді емес",
        "comparison": "{comparison} салыстыруы: жақсарған {improved}, нашарлаған {degraded}, баламалы {equivalent}.",
        "no_comparison": "Калибрлеу салыстыруы әлі орындалмады.",
        "disclaimer": "Пакет тек көрсетілген жоба аясында қолданылады. Бастапқы ZIP және fingerprints өзгермейді; деректер құқығы қорытынды экспорт алдында қайта тексеріледі.",
        "package": "Пакет", "version": "Нұсқа", "operator": "Оператор", "legal": "Құқықтық мәртебе", "methods": "Әдістер", "report": "Қорытынды есеп", "status": "Күй", "fingerprint": "Fingerprint",
    },
    "en": {
        "title": "Operator calibration packages",
        "summary": "Imported packages: {count}; active package: {active}.",
        "none": "none",
        "allowed": "allowed",
        "blocked": "blocked",
        "active": "active",
        "inactive": "inactive",
        "comparison": "Comparison {comparison}: improved {improved}, degraded {degraded}, equivalent {equivalent}.",
        "no_comparison": "No calibration comparison has been run yet.",
        "disclaimer": "A package is used only inside its declared project scope. The source ZIP and fingerprints are immutable; data rights are checked again before final export.",
        "package": "Package", "version": "Version", "operator": "Operator", "legal": "Legal status", "methods": "Methods", "report": "Final report", "status": "Status", "fingerprint": "Fingerprint",
    },
}


def build_operator_calibration_diagnostics_view(
    packages: Sequence[OperatorCalibrationPackageRecord],
    *,
    comparison: OperatorCalibrationComparisonReport | None = None,
    locale: str = "ru",
) -> OperatorCalibrationDiagnosticsView:
    language = str(locale).lower().split("-")[0]
    copy = _COPY.get(language, _COPY["en"])
    active = next((item for item in packages if item.active), None)
    rows = tuple(
        OperatorCalibrationPackageRow(
            package_id=item.package_id,
            version=item.version,
            operator_name=item.operator_name,
            legal_status=item.legal_status,
            method_count=len(item.method_ids),
            final_report_rights=copy["allowed"] if item.final_report_use_allowed else copy["blocked"],
            active_status=copy["active"] if item.active else copy["inactive"],
            fingerprint=item.package_fingerprint,
        )
        for item in packages
    )
    if comparison is None:
        comparison_summary = copy["no_comparison"]
    else:
        counts = {"improved": 0, "degraded": 0, "equivalent": 0}
        for item in comparison.methods:
            if item.status in counts:
                counts[item.status] += 1
        comparison_summary = copy["comparison"].format(
            comparison=comparison.comparison_id,
            improved=counts["improved"],
            degraded=counts["degraded"],
            equivalent=counts["equivalent"],
        )
    return OperatorCalibrationDiagnosticsView(
        locale=language,
        title=copy["title"],
        summary=copy["summary"].format(
            count=len(rows),
            active=(f"{active.package_id} {active.version}" if active else copy["none"]),
        ),
        disclaimer=copy["disclaimer"],
        labels={key: copy[key] for key in ("package", "version", "operator", "legal", "methods", "report", "status", "fingerprint")},
        rows=rows,
        comparison_summary=comparison_summary,
    )
