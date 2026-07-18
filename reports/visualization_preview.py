"""Shared normalization for visualization previews embedded in documents.

Page-aware previews are strict: every physical page must be supplied explicitly
through the canonical ``pages`` array. Legacy previews may still expose one SVG,
but report renderers never silently collapse a page-aware package to page one.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class VisualizationPreviewPage:
    index: int
    svg: str
    track_ids: tuple[str, ...] = ()
    width_pt: float = 0.0
    height_pt: float = 0.0


@dataclass(frozen=True, slots=True)
class NormalizedVisualizationPreview:
    schema: str
    version: str
    title: str
    locale: str
    pages: tuple[VisualizationPreviewPage, ...]
    track_count: int
    curve_count: int
    overlay_count: int
    profile_id: str
    page_size: str
    orientation: str
    dpi: int
    geometry_signature: str
    export_ready: bool
    direct_multi_page: bool
    issues: tuple[str, ...] = ()

    @property
    def page_count(self) -> int:
        return len(self.pages)

    @property
    def ok(self) -> bool:
        return self.export_ready and bool(self.pages) and not self.issues


def normalize_visualization_preview(value: Mapping[str, Any] | None) -> NormalizedVisualizationPreview:
    preview = dict(value or {})
    schema = str(preview.get("schema") or "")
    version = str(preview.get("version") or "")
    page_aware = schema == "visualization.preview.page-aware"
    issues: list[str] = []
    pages: list[VisualizationPreviewPage] = []

    if page_aware:
        raw_pages = preview.get("pages")
        if not isinstance(raw_pages, (list, tuple)):
            issues.append("page_aware_preview_pages_missing")
            raw_pages = ()
        for offset, item in enumerate(raw_pages, start=1):
            if not isinstance(item, Mapping):
                issues.append(f"page_aware_preview_page_invalid:{offset}")
                continue
            svg = str(item.get("svg") or "").strip()
            if not svg.startswith("<svg"):
                issues.append(f"page_aware_preview_svg_invalid:{offset}")
                continue
            pages.append(
                VisualizationPreviewPage(
                    index=_positive_int(item.get("index"), offset),
                    svg=svg,
                    track_ids=tuple(str(track) for track in item.get("track_ids", ()) if str(track)),
                    width_pt=_non_negative_float(item.get("width_pt")),
                    height_pt=_non_negative_float(item.get("height_pt")),
                )
            )
        declared_count = _non_negative_int(preview.get("page_count"))
        if declared_count != len(pages):
            issues.append(f"page_aware_preview_page_count_mismatch:{declared_count}:{len(pages)}")
        if bool(preview.get("single_page_fallback")) or bool(preview.get("legacy_svg_fallback_allowed")):
            issues.append("page_aware_preview_legacy_fallback_forbidden")
    else:
        declared_pages = preview.get("page_svgs")
        raw_svgs = [str(item).strip() for item in declared_pages] if isinstance(declared_pages, (list, tuple)) else []
        if not raw_svgs:
            raw_svgs = [str(preview.get("svg") or "").strip()]
        pages = [
            VisualizationPreviewPage(index=index, svg=svg)
            for index, svg in enumerate(raw_svgs, start=1)
            if svg.startswith("<svg")
        ]

    return NormalizedVisualizationPreview(
        schema=schema,
        version=version,
        title=str(preview.get("title") or ""),
        locale=_locale(preview.get("locale"), fallback="ru" if page_aware else "en"),
        pages=tuple(pages),
        track_count=_non_negative_int(preview.get("track_count")),
        curve_count=_non_negative_int(preview.get("curve_count")),
        overlay_count=_non_negative_int(preview.get("overlay_count")),
        profile_id=str(preview.get("profile_id") or ""),
        page_size=str(preview.get("page_size") or ""),
        orientation=str(preview.get("orientation") or ""),
        dpi=_non_negative_int(preview.get("dpi")),
        geometry_signature=str(preview.get("geometry_signature") or ""),
        export_ready=bool(preview.get("export_ready")),
        direct_multi_page=bool(page_aware and preview.get("direct_multi_page", True)),
        issues=tuple(dict.fromkeys(issues)),
    )



_TEXT = {
    "ru": {
        "tracks": "Треки",
        "curves": "Кривые",
        "overlays": "Интервалы",
        "pages": "Страницы",
        "page": "Страница {index} из {count}",
        "unavailable": "SVG-планшет недоступен.",
        "embed_error": "Не удалось встроить SVG-планшет ({error}).",
        "title": "Физический предпросмотр планшета",
    },
    "kk": {
        "tracks": "Тректер",
        "curves": "Қисықтар",
        "overlays": "Аралықтар",
        "pages": "Беттер",
        "page": "{count} беттің {index}-беті",
        "unavailable": "SVG планшеті қолжетімсіз.",
        "embed_error": "SVG планшетін ендіру мүмкін болмады ({error}).",
        "title": "Планшеттің физикалық preview-ы",
    },
    "en": {
        "tracks": "Tracks",
        "curves": "Curves",
        "overlays": "Overlays",
        "pages": "Pages",
        "page": "Page {index} of {count}",
        "unavailable": "SVG visualization is unavailable.",
        "embed_error": "Unable to embed the SVG visualization ({error}).",
        "title": "Physical visualization preview",
    },
}


def visualization_preview_summary_text(preview: NormalizedVisualizationPreview) -> str:
    text = _TEXT[preview.locale]
    return (
        f"{text['tracks']}: {preview.track_count} · "
        f"{text['curves']}: {preview.curve_count} · "
        f"{text['overlays']}: {preview.overlay_count} · "
        f"{text['pages']}: {preview.page_count}"
    )


def visualization_preview_page_label(index: int, count: int, locale: str) -> str:
    normalized = _locale(locale)
    return _TEXT[normalized]["page"].format(index=index, count=count)


def visualization_preview_message(key: str, locale: str, **values: object) -> str:
    normalized = _locale(locale)
    template = _TEXT[normalized].get(key, _TEXT["en"].get(key, key))
    return template.format(**values)


def visualization_preview_svgs(value: Mapping[str, Any] | None) -> tuple[str, ...]:
    return tuple(page.svg for page in normalize_visualization_preview(value).pages)



def _locale(value: Any, *, fallback: str = "ru") -> str:
    normalized_fallback = fallback if fallback in _TEXT else "ru"
    candidate = str(value or normalized_fallback).strip().lower()
    return candidate if candidate in _TEXT else normalized_fallback


def _positive_int(value: Any, fallback: int) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError):
        return fallback
    return result if result > 0 else fallback


def _non_negative_int(value: Any) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, result)


def _non_negative_float(value: Any) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, result)


__all__ = [
    "NormalizedVisualizationPreview",
    "VisualizationPreviewPage",
    "normalize_visualization_preview",
    "visualization_preview_message",
    "visualization_preview_page_label",
    "visualization_preview_summary_text",
    "visualization_preview_svgs",
]
