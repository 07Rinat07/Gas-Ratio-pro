from __future__ import annotations

"""Framework-neutral contracts for the GAS RATIO PRO Print & Export Center."""

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from services.visualization_print_center_contract import VisualizationPrintCenterPreparedPackage

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


@dataclass(frozen=True, slots=True)
class PrintCenterPreviewPage:
    index: int
    label: str
    width_pt: float
    height_pt: float
    track_ids: tuple[str, ...] = ()
    svg: str = ""

    def to_dict(self, *, include_svg: bool = True) -> dict[str, Any]:
        data: dict[str, Any] = {
            "index": self.index,
            "label": self.label,
            "width_pt": self.width_pt,
            "height_pt": self.height_pt,
            "track_ids": list(self.track_ids),
        }
        if include_svg:
            data["svg"] = self.svg
        return data


@dataclass(frozen=True, slots=True)
class ProfessionalPrintCenterViewModel:
    """Visible UI contract backed by one prepared physical package."""

    session: PrintCenterSession
    title: str
    exact_profile_label: str
    page_count_label: str
    status_label: str
    geometry_signature: str
    parity_gate_id: str = ""
    cross_format_parity_passed: bool = False
    pages: tuple[PrintCenterPreviewPage, ...] = ()
    available_formats: tuple[str, ...] = ("pdf", "docx", "html", "svg", "png")
    export_ready: bool = False
    issues: tuple[str, ...] = field(default_factory=tuple)

    @property
    def page_count(self) -> int:
        return len(self.pages)

    def to_dict(self, *, include_svgs: bool = True) -> dict[str, Any]:
        return {
            "schema": "gas-ratio-pro/print-center/view/v1",
            "version": "1.0",
            "session": self.session.to_dict(),
            "title": self.title,
            "exact_profile_label": self.exact_profile_label,
            "page_count": self.page_count,
            "page_count_label": self.page_count_label,
            "status_label": self.status_label,
            "geometry_signature": self.geometry_signature,
            "parity_gate_id": self.parity_gate_id,
            "cross_format_parity_passed": self.cross_format_parity_passed,
            "pages": [page.to_dict(include_svg=include_svgs) for page in self.pages],
            "available_formats": list(self.available_formats),
            "export_ready": self.export_ready,
            "issues": list(self.issues),
            "direct_multi_page_preview": True,
            "single_page_fallback": False,
            "contains_raw_dataframe": False,
        }


def build_professional_print_center_view(
    prepared: VisualizationPrintCenterPreparedPackage,
    *,
    project_id: str,
    locale: object = "ru",
    title: str = "LAS visualization",
    template_id: str = "engineering",
    output_format: str = "pdf",
) -> ProfessionalPrintCenterViewModel:
    normalized_locale = normalize_document_locale(locale)
    package = prepared.package
    session = PrintCenterSession(
        project_id=str(project_id or ""),
        document_locale=normalized_locale,
        template_id=str(template_id or "engineering"),
        output_format=str(output_format or "pdf"),
        paper_size=package.page_size or "A4",
        orientation=package.orientation or "portrait",
        include_legend=bool(prepared.summary.repeated_legend_enabled),
        include_page_chrome=bool(prepared.summary.page_chrome_enabled),
    )
    page_word = {"ru": "Страница", "kk": "Бет", "en": "Page"}[normalized_locale]
    pages = tuple(
        PrintCenterPreviewPage(
            index=page.index,
            label=f"{page_word} {page.index}/{package.page_count}",
            width_pt=page.width_pt,
            height_pt=page.height_pt,
            track_ids=page.track_ids,
            svg=page.svg,
        )
        for page in package.pages
    )
    return ProfessionalPrintCenterViewModel(
        session=session,
        title=str(title or "LAS visualization"),
        exact_profile_label=prepared.summary.exact_profile_label,
        page_count_label=prepared.summary.page_count_label,
        status_label=prepared.summary.status_label,
        geometry_signature=package.geometry_signature,
        parity_gate_id=str(package.parity_gate.get("gate_id") or ""),
        cross_format_parity_passed=bool(package.parity_gate.get("ok")),
        pages=pages,
        export_ready=prepared.export_ready,
        issues=tuple(dict.fromkeys((*prepared.summary.issues, *package.issues))),
    )


__all__ = [
    "DocumentLocale",
    "PrintCenterSession",
    "default_report_copy",
    "document_locale_options",
    "normalize_document_locale",
    "PrintCenterPreviewPage",
    "ProfessionalPrintCenterViewModel",
    "build_professional_print_center_view",
]
