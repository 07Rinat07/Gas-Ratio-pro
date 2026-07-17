"""One-step Print Center contract for page-aware visualization exports.

The service is UI-framework neutral.  It prepares exactly one physical export
package and exposes the profile/page summary that a Print Center can show before
launching PDF, DOCX, SVG or PNG delivery.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from services.visualization_page_aware_package import (
    VisualizationPageAwarePackage,
    VisualizationPageAwarePackageBuilder,
)


_TEXT = {
    "ru": {
        "portrait": "Книжная",
        "landscape": "Альбомная",
        "page": "страница",
        "pages_2_4": "страницы",
        "pages_other": "страниц",
        "ready": "Пакет готов к экспорту",
        "not_ready": "Пакет не готов к экспорту",
    },
    "kk": {
        "portrait": "Кітаптық",
        "landscape": "Альбомдық",
        "page": "бет",
        "pages_2_4": "бет",
        "pages_other": "бет",
        "ready": "Пакет экспортқа дайын",
        "not_ready": "Пакет экспортқа дайын емес",
    },
    "en": {
        "portrait": "Portrait",
        "landscape": "Landscape",
        "page": "page",
        "pages_2_4": "pages",
        "pages_other": "pages",
        "ready": "Package is ready for export",
        "not_ready": "Package is not ready for export",
    },
}


@dataclass(frozen=True, slots=True)
class VisualizationPrintCenterSummary:
    schema: str = "visualization.print-center.summary"
    version: str = "1.0"
    locale: str = "ru"
    profile_id: str = ""
    page_size: str = ""
    orientation: str = ""
    orientation_label: str = ""
    dpi: int = 0
    page_count: int = 0
    page_count_label: str = ""
    exact_profile_label: str = ""
    page_chrome_enabled: bool = False
    repeated_legend_enabled: bool = False
    export_ready: bool = False
    status_label: str = ""
    issues: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "version": self.version,
            "locale": self.locale,
            "profile_id": self.profile_id,
            "page_size": self.page_size,
            "orientation": self.orientation,
            "orientation_label": self.orientation_label,
            "dpi": self.dpi,
            "page_count": self.page_count,
            "page_count_label": self.page_count_label,
            "exact_profile_label": self.exact_profile_label,
            "page_chrome_enabled": self.page_chrome_enabled,
            "repeated_legend_enabled": self.repeated_legend_enabled,
            "export_ready": self.export_ready,
            "status_label": self.status_label,
            "issues": list(self.issues),
            "single_pipeline_source": True,
            "single_page_fallback": False,
        }


@dataclass(frozen=True, slots=True)
class VisualizationPrintCenterPreparedPackage:
    package: VisualizationPageAwarePackage
    summary: VisualizationPrintCenterSummary

    @property
    def export_ready(self) -> bool:
        return self.package.export_ready and self.summary.export_ready

    def output_contract(self, *, title: str = "LAS visualization") -> dict[str, Any]:
        """Return format-neutral outputs without rebuilding the page layout."""

        return {
            "schema": "visualization.print-center.output-contract",
            "version": "1.0",
            "summary": self.summary.to_dict(),
            "pdf": {
                "page_count": self.package.page_count,
                "content": self.package.pdf_bytes,
            },
            "svg": {
                "page_count": self.package.page_count,
                "pages": [page.svg for page in self.package.pages],
            },
            "png": {
                "page_count": self.package.page_count,
                "pages": [page.png_bytes for page in self.package.pages],
            },
            "docx_html_preview": self.package.preview_contract(title=title),
            "geometry_signature": self.package.geometry_signature,
            "export_ready": self.export_ready,
            "single_pipeline_source": True,
            "single_page_fallback": False,
        }


class VisualizationPrintCenterService:
    """Prepare one auditable page-aware package for a one-click export run."""

    def __init__(self, builder: VisualizationPageAwarePackageBuilder | None = None) -> None:
        self._builder = builder or VisualizationPageAwarePackageBuilder()

    def prepare(
        self,
        pipeline: Mapping[str, Any],
        *,
        locale: str = "ru",
        title: str = "LAS visualization",
        raster_dpi: int = 300,
    ) -> VisualizationPrintCenterPreparedPackage:
        normalized_locale = _locale(locale)
        package = self._builder.build(pipeline, raster_dpi=raster_dpi)
        chrome = dict(package.page_chrome)
        issues = list(package.issues)
        if package.export_ready and not bool(chrome.get("enabled")):
            issues.append("print_center_page_chrome_disabled")
        summary = VisualizationPrintCenterSummary(
            locale=normalized_locale,
            profile_id=package.profile_id,
            page_size=package.page_size,
            orientation=package.orientation,
            orientation_label=_TEXT[normalized_locale].get(package.orientation, package.orientation),
            dpi=package.dpi,
            page_count=package.page_count,
            page_count_label=_page_count_label(package.page_count, normalized_locale),
            exact_profile_label=_exact_profile_label(package, normalized_locale),
            page_chrome_enabled=bool(chrome.get("enabled")),
            repeated_legend_enabled=bool(chrome.get("enabled") and chrome.get("repeat_legend", True)),
            export_ready=package.export_ready,
            status_label=_TEXT[normalized_locale]["ready" if package.export_ready else "not_ready"],
            issues=tuple(dict.fromkeys(issues)),
        )
        prepared = VisualizationPrintCenterPreparedPackage(package=package, summary=summary)
        # Access the preview once here so invalid future implementations fail at
        # the one-click boundary rather than in a downstream DOCX/HTML adapter.
        prepared.output_contract(title=title)["docx_html_preview"]
        return prepared


def _locale(value: object) -> str:
    candidate = str(value or "ru").strip().lower()
    return candidate if candidate in _TEXT else "ru"


def _page_count_label(page_count: int, locale: str) -> str:
    count = max(0, int(page_count))
    if locale != "ru":
        noun = _TEXT[locale]["page" if count == 1 else "pages_other"]
        return f"{count} {noun}"
    remainder_100 = count % 100
    remainder_10 = count % 10
    if remainder_10 == 1 and remainder_100 != 11:
        noun = _TEXT[locale]["page"]
    elif 2 <= remainder_10 <= 4 and not 12 <= remainder_100 <= 14:
        noun = _TEXT[locale]["pages_2_4"]
    else:
        noun = _TEXT[locale]["pages_other"]
    return f"{count} {noun}"


def _exact_profile_label(package: VisualizationPageAwarePackage, locale: str) -> str:
    orientation = _TEXT[locale].get(package.orientation, package.orientation)
    return f"{package.page_size} · {orientation} · {package.dpi} DPI · {_page_count_label(package.page_count, locale)}"


__all__ = [
    "VisualizationPrintCenterPreparedPackage",
    "VisualizationPrintCenterService",
    "VisualizationPrintCenterSummary",
]
