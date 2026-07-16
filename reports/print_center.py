from __future__ import annotations

"""Framework-neutral contracts for the GAS RATIO PRO Print & Export Center."""

from dataclasses import asdict, dataclass
from typing import Literal

DocumentLocale = Literal["ru", "kk", "en"]

_LOCALE_LABELS: dict[DocumentLocale, str] = {
    "ru": "Русский",
    "kk": "Қазақша",
    "en": "English",
}

_DEFAULT_COPY: dict[DocumentLocale, dict[str, str]] = {
    "ru": {
        "title": "Профессиональный отчёт GAS RATIO PRO",
        "subtitle": "Инженерное заключение по вероятным УВ-интервалам",
        "classification": "ИНЖЕНЕРНОЕ ИСПОЛЬЗОВАНИЕ",
        "footer": "GAS RATIO PRO · Инженерный отчёт",
    },
    "kk": {
        "title": "GAS RATIO PRO кәсіби есебі",
        "subtitle": "Ықтимал көмірсутек аралықтары бойынша инженерлік қорытынды",
        "classification": "ИНЖЕНЕРЛІК ПАЙДАЛАНУ",
        "footer": "GAS RATIO PRO · Инженерлік есеп",
    },
    "en": {
        "title": "GAS RATIO PRO Professional Report",
        "subtitle": "Engineering assessment of probable hydrocarbon intervals",
        "classification": "ENGINEERING USE",
        "footer": "GAS RATIO PRO · Engineering report",
    },
}


@dataclass(frozen=True)
class PrintCenterSession:
    project_id: str
    document_locale: DocumentLocale = "ru"
    template_id: str = "engineering"
    output_format: str = "pdf"
    paper_size: str = "A4"
    orientation: str = "portrait"
    include_legend: bool = True
    include_page_chrome: bool = True

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def normalize_document_locale(value: object, *, fallback: DocumentLocale = "ru") -> DocumentLocale:
    candidate = str(value or "").strip().lower()
    return candidate if candidate in _DEFAULT_COPY else fallback  # type: ignore[return-value]


def document_locale_options() -> tuple[tuple[DocumentLocale, str], ...]:
    return tuple((locale, _LOCALE_LABELS[locale]) for locale in ("ru", "kk", "en"))


def default_report_copy(locale: object) -> dict[str, str]:
    normalized = normalize_document_locale(locale)
    return dict(_DEFAULT_COPY[normalized])


__all__ = [
    "DocumentLocale",
    "PrintCenterSession",
    "default_report_copy",
    "document_locale_options",
    "normalize_document_locale",
]
