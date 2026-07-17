"""Renderer-neutral page chrome primitives for physical visualization pages.

The module owns headers, footers, page numbering and repeated legends in
physical page coordinates (points).  SVG/PDF renderers consume the same
primitive dictionaries and therefore do not recalculate page chrome geometry.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence


_PAGE_LABELS = {
    "ru": "Страница",
    "kk": "Бет",
    "en": "Page",
}

_LEGEND_LABELS = {
    "ru": "Легенда",
    "kk": "Шартты белгілер",
    "en": "Legend",
}

_DEFAULTS: dict[str, Any] = {
    "enabled": False,
    "locale": "ru",
    "title": "GAS RATIO PRO",
    "subtitle": "",
    "classification": "",
    "document_code": "",
    "footer_text": "GAS RATIO PRO",
    "show_page_number": True,
    "repeat_legend": True,
    "max_legend_items": 10,
    "header_height_pt": 38.0,
    "footer_height_pt": 20.0,
}


def resolve_page_chrome_options(value: object) -> dict[str, Any]:
    """Normalize a JSON-safe page chrome configuration."""

    if isinstance(value, bool):
        source: dict[str, Any] = {"enabled": value}
    elif isinstance(value, Mapping):
        source = dict(value)
    else:
        source = {}

    result = dict(_DEFAULTS)
    result.update(source)
    locale = str(result.get("locale") or "ru").strip().lower()
    result["locale"] = locale if locale in _PAGE_LABELS else "ru"
    result["enabled"] = bool(result.get("enabled", False))
    result["show_page_number"] = bool(result.get("show_page_number", True))
    result["repeat_legend"] = bool(result.get("repeat_legend", True))
    result["max_legend_items"] = max(0, _positive_int(result.get("max_legend_items"), 10))
    result["header_height_pt"] = max(0.0, _non_negative_float(result.get("header_height_pt"), 38.0))
    result["footer_height_pt"] = max(0.0, _non_negative_float(result.get("footer_height_pt"), 20.0))
    for key in ("title", "subtitle", "classification", "document_code", "footer_text"):
        result[key] = str(result.get(key) or "").strip()
    result["schema"] = "visualization.page.chrome.options"
    result["version"] = "1.0"
    result["renderer_neutral"] = True
    return result


def build_page_chrome_primitives(
    *,
    page_index: int,
    page_count: int,
    header_bounds: Mapping[str, Any] | None,
    footer_bounds: Mapping[str, Any] | None,
    legend_bounds: Mapping[str, Any] | None,
    legend_items: Sequence[Mapping[str, Any]] | None,
    options: Mapping[str, Any] | None,
    minimum_font_pt: float,
    minimum_line_width_pt: float,
) -> tuple[dict[str, Any], ...]:
    """Build page-space primitives shared by every export renderer."""

    cfg = resolve_page_chrome_options(options)
    if not cfg["enabled"]:
        return ()

    primitives: list[dict[str, Any]] = []
    header = _mapping(header_bounds)
    footer = _mapping(footer_bounds)
    legend = _mapping(legend_bounds)
    locale = str(cfg["locale"])
    font_floor = max(6.0, float(minimum_font_pt or 0.0))
    line_floor = max(0.25, float(minimum_line_width_pt or 0.0))

    if header:
        hx = _float(header.get("x"))
        hy = _float(header.get("y"))
        hw = _float(header.get("width"))
        hh = _float(header.get("height"))
        title = str(cfg.get("title") or "GAS RATIO PRO")
        subtitle = str(cfg.get("subtitle") or "")
        classification = str(cfg.get("classification") or "")
        document_code = str(cfg.get("document_code") or "")
        primitives.append(_line(
            f"page.{page_index}.chrome.header-rule",
            hx,
            hy + hh,
            hx + hw,
            hy + hh,
            stroke="#607d8b",
            stroke_width=line_floor,
        ))
        primitives.append(_text(
            f"page.{page_index}.chrome.title",
            hx,
            hy + max(font_floor + 2.0, 13.0),
            title,
            font_size=max(font_floor + 1.5, 9.0),
            font_weight=700,
        ))
        if subtitle:
            primitives.append(_text(
                f"page.{page_index}.chrome.subtitle",
                hx,
                hy + min(hh - 4.0, max(font_floor * 2.0 + 4.0, 25.0)),
                subtitle,
                font_size=font_floor,
                fill="#455a64",
            ))
        right_lines = [item for item in (classification, document_code) if item]
        for offset, text in enumerate(right_lines[:2]):
            primitives.append(_text(
                f"page.{page_index}.chrome.header-meta.{offset + 1}",
                hx + hw,
                hy + max(font_floor + 2.0, 12.0) + offset * (font_floor + 3.0),
                text,
                font_size=font_floor,
                font_weight=600 if offset == 0 else 400,
                fill="#455a64",
                text_anchor="end",
            ))

    if footer:
        fx = _float(footer.get("x"))
        fy = _float(footer.get("y"))
        fw = _float(footer.get("width"))
        footer_text = str(cfg.get("footer_text") or "GAS RATIO PRO")
        primitives.append(_line(
            f"page.{page_index}.chrome.footer-rule",
            fx,
            fy,
            fx + fw,
            fy,
            stroke="#90a4ae",
            stroke_width=line_floor,
        ))
        primitives.append(_text(
            f"page.{page_index}.chrome.footer-text",
            fx,
            fy + max(font_floor + 3.0, 11.0),
            footer_text,
            font_size=font_floor,
            fill="#546e7a",
        ))
        if cfg.get("show_page_number", True):
            page_text = f"{_PAGE_LABELS[locale]} {page_index} / {max(page_count, 1)}"
            primitives.append(_text(
                f"page.{page_index}.chrome.page-number",
                fx + fw,
                fy + max(font_floor + 3.0, 11.0),
                page_text,
                font_size=font_floor,
                font_weight=600,
                fill="#455a64",
                text_anchor="end",
            ))

    if legend and cfg.get("repeat_legend", True):
        items = [dict(item) for item in (legend_items or ()) if isinstance(item, Mapping)]
        max_items = int(cfg.get("max_legend_items") or 0)
        if max_items:
            items = items[:max_items]
        lx = _float(legend.get("x"))
        ly = _float(legend.get("y"))
        lw = _float(legend.get("width"))
        lh = _float(legend.get("height"))
        if items and lw > 0 and lh > 0:
            label_size = font_floor
            title_width = min(72.0, max(52.0, lw * 0.12))
            primitives.append(_text(
                f"page.{page_index}.chrome.legend-title",
                lx,
                ly + max(label_size + 3.0, 11.0),
                _LEGEND_LABELS[locale],
                font_size=label_size,
                font_weight=700,
                fill="#37474f",
            ))
            available = max(1.0, lw - title_width)
            slot_width = available / max(1, len(items))
            for item_index, item in enumerate(items):
                start_x = lx + title_width + item_index * slot_width
                center_y = ly + min(lh - 5.0, max(label_size + 2.0, lh / 2.0))
                color = str(item.get("color") or "#607d8b")
                label = str(item.get("label") or item.get("id") or "")
                unit = str(item.get("unit") or "")
                if unit:
                    label = f"{label} [{unit}]"
                label = _truncate(label, max(8, int(slot_width / max(label_size * 0.55, 1.0))))
                primitives.append(_line(
                    f"page.{page_index}.chrome.legend-swatch.{item_index + 1}",
                    start_x,
                    center_y,
                    start_x + min(18.0, max(8.0, slot_width * 0.22)),
                    center_y,
                    stroke=color,
                    stroke_width=max(line_floor, _positive_float(item.get("line_width"), 1.5)),
                ))
                primitives.append(_text(
                    f"page.{page_index}.chrome.legend-label.{item_index + 1}",
                    start_x + min(22.0, max(11.0, slot_width * 0.27)),
                    center_y + label_size * 0.35,
                    label,
                    font_size=label_size,
                    fill="#37474f",
                ))

    return tuple(primitives)


def _primitive(primitive_id: str, kind: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": primitive_id,
        "kind": kind,
        "z_index": 2000,
        "track_id": "",
        "clip_id": "",
        "visible": True,
        "printable": True,
        "coordinate_space": "page_pt",
        "payload": dict(payload),
    }


def _text(
    primitive_id: str,
    x: float,
    y: float,
    text: str,
    *,
    font_size: float,
    font_weight: int = 400,
    fill: str = "#263238",
    text_anchor: str = "start",
) -> dict[str, Any]:
    return _primitive(primitive_id, "text", {
        "x": x,
        "y": y,
        "text": text,
        "font_size": font_size,
        "font_weight": font_weight,
        "fill": fill,
        "text_anchor": text_anchor,
        "data_kind": "page_chrome",
    })


def _line(
    primitive_id: str,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    *,
    stroke: str,
    stroke_width: float,
) -> dict[str, Any]:
    return _primitive(primitive_id, "line", {
        "x1": x1,
        "y1": y1,
        "x2": x2,
        "y2": y2,
        "stroke": stroke,
        "stroke_width": stroke_width,
        "data_kind": "page_chrome",
    })


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _positive_float(value: object, default: float) -> float:
    parsed = _float(value, default)
    return parsed if parsed > 0 else default


def _non_negative_float(value: object, default: float) -> float:
    parsed = _float(value, default)
    return parsed if parsed >= 0 else default


def _positive_int(value: object, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _truncate(value: str, limit: int) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[: max(1, limit - 1)].rstrip() + "…"


__all__ = [
    "build_page_chrome_primitives",
    "resolve_page_chrome_options",
]
