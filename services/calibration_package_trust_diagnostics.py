"""Localized read-only diagnostics for Stage 5.3 package trust workflow."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from services.calibration_package_trust_application_service import (
    CalibrationPackageTrustApplicationService,
    CalibrationPackageTrustError,
)
from services.operator_calibration_package_application_service import OperatorCalibrationPackageRecord


@dataclass(frozen=True, slots=True)
class CalibrationTrustRow:
    package_id: str
    version: str
    environment: str
    signature_status: str
    review_status: str
    trust_status: str
    next_environment: str
    package_fingerprint: str


@dataclass(frozen=True, slots=True)
class CalibrationTrustDiagnosticsView:
    locale: str
    title: str
    summary: str
    disclaimer: str
    labels: Mapping[str, str]
    rows: tuple[CalibrationTrustRow, ...]
    expiry_summary: str


_COPY: Mapping[str, Mapping[str, str]] = {
    "ru": {
        "title": "Доверие и проверка калибровочного пакета",
        "summary": "Пакетов: {count}; production-ready: {ready}; отозвано/заблокировано: {blocked}.",
        "disclaimer": "Закрытые ключи не хранятся в проекте. Финальный отчёт допускает только подписанный, одобренный и продвинутый в production пакет без отзыва и истечения срока.",
        "package": "Пакет", "version": "Версия", "environment": "Среда", "signature": "Подпись", "review": "Проверка", "trust": "Доверие", "next": "Следующая среда", "fingerprint": "Fingerprint",
        "valid": "проверена", "missing": "отсутствует", "approved": "одобрено", "pending": "ожидает", "passed": "разрешён", "blocked": "заблокирован", "none": "—",
        "expiry": "Истекает в течение {days} дней: {expiring}; уже истекло: {expired}.",
    },
    "kk": {
        "title": "Калибрлеу пакетінің сенімі және тексеруі",
        "summary": "Пакеттер: {count}; production-ready: {ready}; қайтарылған/бұғатталған: {blocked}.",
        "disclaimer": "Жеке кілттер жобада сақталмайды. Қорытынды есепке тек қол қойылған, мақұлданған, production ортасына өткізілген және мерзімі өтпеген пакет жіберіледі.",
        "package": "Пакет", "version": "Нұсқа", "environment": "Орта", "signature": "Қолтаңба", "review": "Тексеру", "trust": "Сенім", "next": "Келесі орта", "fingerprint": "Fingerprint",
        "valid": "тексерілді", "missing": "жоқ", "approved": "мақұлданды", "pending": "күтілуде", "passed": "рұқсат", "blocked": "бұғатталған", "none": "—",
        "expiry": "{days} күн ішінде мерзімі аяқталады: {expiring}; мерзімі өткен: {expired}.",
    },
    "en": {
        "title": "Calibration package trust and review",
        "summary": "Packages: {count}; production-ready: {ready}; revoked/blocked: {blocked}.",
        "disclaimer": "Private keys are never stored in the project. Final reports accept only signed, approved, production-promoted packages with no revocation or expiry.",
        "package": "Package", "version": "Version", "environment": "Environment", "signature": "Signature", "review": "Review", "trust": "Trust", "next": "Next environment", "fingerprint": "Fingerprint",
        "valid": "verified", "missing": "missing", "approved": "approved", "pending": "pending", "passed": "allowed", "blocked": "blocked", "none": "—",
        "expiry": "Expiring within {days} days: {expiring}; already expired: {expired}.",
    },
}


def build_calibration_trust_diagnostics_view(
    packages: Sequence[OperatorCalibrationPackageRecord],
    *,
    trust_service: CalibrationPackageTrustApplicationService,
    locale: str = "ru",
    warning_window_days: int = 30,
) -> CalibrationTrustDiagnosticsView:
    language = str(locale).lower().split("-")[0]
    copy = _COPY.get(language, _COPY["en"])
    rows: list[CalibrationTrustRow] = []
    ready = 0
    blocked = 0
    for package in packages:
        environment = trust_service.current_environment(package.package_fingerprint)
        next_environment = {
            "development": "validation",
            "validation": "production",
            "production": "production",
        }[environment]
        signatures = trust_service.list_signatures(package.package_fingerprint)
        reviews = trust_service.list_reviews(package.package_fingerprint, latest_only=True)
        try:
            decision = trust_service.evaluate(
                package.package_fingerprint,
                requested_environment=next_environment,
                final_report=environment == "production",
            )
            trusted = decision.passed
        except (CalibrationPackageTrustError, KeyError, OSError, ValueError):
            trusted = False
        if environment == "production" and trusted:
            ready += 1
        elif not trusted:
            blocked += 1
        required_roles = set(trust_service.REQUIRED_REVIEWS[next_environment])
        approved_roles = {item.reviewer_role for item in reviews if item.decision == "approve"}
        review_ok = required_roles.issubset(approved_roles) and not any(item.decision == "reject" for item in reviews)
        rows.append(
            CalibrationTrustRow(
                package_id=package.package_id,
                version=package.version,
                environment=environment,
                signature_status=copy["valid"] if signatures else copy["missing"],
                review_status=copy["approved"] if review_ok else copy["pending"],
                trust_status=copy["passed"] if trusted else copy["blocked"],
                next_environment=next_environment if environment != "production" else copy["none"],
                package_fingerprint=package.package_fingerprint,
            )
        )
    expiry = trust_service.monitor_expiry(warning_window_days=warning_window_days)
    return CalibrationTrustDiagnosticsView(
        locale=language,
        title=copy["title"],
        summary=copy["summary"].format(count=len(rows), ready=ready, blocked=blocked),
        disclaimer=copy["disclaimer"],
        labels={key: copy[key] for key in ("package", "version", "environment", "signature", "review", "trust", "next", "fingerprint")},
        rows=tuple(rows),
        expiry_summary=copy["expiry"].format(days=warning_window_days, expiring=expiry.expiring_count, expired=expiry.expired_count),
    )
