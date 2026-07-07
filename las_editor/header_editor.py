from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Sequence

from las_editor.las_creator import DEFAULT_NULL_VALUE, normalize_las_mnemonic, normalize_las_unit


SUPPORTED_HEADER_SECTIONS: tuple[str, ...] = ("Version", "Well", "Curve", "Parameter")
REQUIRED_WELL_ITEMS: tuple[str, ...] = ("STRT", "STOP", "STEP", "NULL")
REQUIRED_VERSION_ITEMS: tuple[str, ...] = ("VERS", "WRAP")
PROTECTED_HEADER_ITEMS: dict[str, tuple[str, ...]] = {
    "Version": REQUIRED_VERSION_ITEMS,
    "Well": REQUIRED_WELL_ITEMS,
    "Curve": ("DEPT",),
}
HEADER_EDITOR_STORAGE_KEY = "las_header_editor"


@dataclass(frozen=True)
class LasHeaderCard:
    """One normalized LAS header card.

    LAS header lines normally follow the pattern ``MNEM.UNIT value : description``.
    This class stores the card in a UI/API-friendly form so the editor can change
    metadata safely without touching ASCII log values.
    """

    section: str
    mnemonic: str
    unit: str = ""
    value: str = ""
    description: str = ""
    order: int = 0
    protected: bool = False


@dataclass(frozen=True)
class HeaderEditorHistoryEntry:
    action: str
    section: str
    mnemonic: str
    timestamp: str
    details: dict[str, Any]
    reason: str = "manual"
    source: str = "las_editor.header_editor"


@dataclass(frozen=True)
class HeaderEditorIssue:
    severity: str
    code: str
    message: str
    section: str = ""
    mnemonic: str = ""


@dataclass(frozen=True)
class HeaderEditorResult:
    cards: tuple[LasHeaderCard, ...]
    manifest: dict[str, dict[str, dict[str, Any]]]
    history: tuple[HeaderEditorHistoryEntry, ...]
    issues: tuple[HeaderEditorIssue, ...] = ()
    diagnostics: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


def _timestamp_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_section_name(section: object) -> str:
    raw = str(section or "").strip().replace("~", "").lower()
    aliases = {
        "v": "Version",
        "version": "Version",
        "versions": "Version",
        "w": "Well",
        "well": "Well",
        "well information": "Well",
        "c": "Curve",
        "curve": "Curve",
        "curves": "Curve",
        "curve information": "Curve",
        "p": "Parameter",
        "param": "Parameter",
        "parameter": "Parameter",
        "parameters": "Parameter",
    }
    if raw in aliases:
        return aliases[raw]
    title = raw.title()
    if title in SUPPORTED_HEADER_SECTIONS:
        return title
    raise ValueError(f"Unsupported LAS header section: {section!r}")


def _is_protected(section: str, mnemonic: str) -> bool:
    return normalize_las_mnemonic(mnemonic) in PROTECTED_HEADER_ITEMS.get(section, ())


def make_header_card(
    section: str,
    mnemonic: str,
    *,
    unit: str = "",
    value: object = "",
    description: str = "",
    order: int = 0,
    protected: bool | None = None,
) -> LasHeaderCard:
    normalized_section = normalize_section_name(section)
    normalized_mnemonic = normalize_las_mnemonic(mnemonic, fallback="ITEM")
    normalized_unit = normalize_las_unit(unit)
    return LasHeaderCard(
        section=normalized_section,
        mnemonic=normalized_mnemonic,
        unit=normalized_unit,
        value=str(value if value is not None else "").strip(),
        description=str(description or "").strip(),
        order=int(order),
        protected=_is_protected(normalized_section, normalized_mnemonic) if protected is None else bool(protected),
    )


def _coerce_card(raw: LasHeaderCard | Mapping[str, Any], *, fallback_order: int = 0) -> LasHeaderCard:
    if isinstance(raw, LasHeaderCard):
        return make_header_card(
            raw.section,
            raw.mnemonic,
            unit=raw.unit,
            value=raw.value,
            description=raw.description,
            order=raw.order,
            protected=raw.protected,
        )
    return make_header_card(
        str(raw.get("section", "Well")),
        str(raw.get("mnemonic", raw.get("name", "ITEM"))),
        unit=str(raw.get("unit", "")),
        value=raw.get("value", ""),
        description=str(raw.get("description", "")),
        order=int(raw.get("order", fallback_order)),
        protected=raw.get("protected"),
    )


def build_default_header_cards(
    *,
    well_name: str = "WELL",
    start_depth: float = 0.0,
    stop_depth: float = 0.0,
    step: float = 0.1,
    depth_unit: str = "M",
    null_value: float = DEFAULT_NULL_VALUE,
    las_version: str = "2.0",
    curves: Iterable[Mapping[str, Any] | str] = (),
    parameters: Mapping[str, Any] | None = None,
) -> tuple[LasHeaderCard, ...]:
    """Create a complete minimal professional LAS header card set."""

    unit = normalize_las_unit(depth_unit) or "M"
    cards: list[LasHeaderCard] = [
        make_header_card("Version", "VERS", value=las_version, description="CWLS LAS version", order=0),
        make_header_card("Version", "WRAP", value="NO", description="One line per depth step", order=1),
        make_header_card("Well", "STRT", unit=unit, value=start_depth, description="Start depth", order=0),
        make_header_card("Well", "STOP", unit=unit, value=stop_depth, description="Stop depth", order=1),
        make_header_card("Well", "STEP", unit=unit, value=step, description="Depth step", order=2),
        make_header_card("Well", "NULL", value=null_value, description="Null value", order=3),
        make_header_card("Well", "WELL", value=well_name, description="Well name", order=4),
        make_header_card("Curve", "DEPT", unit=unit, description="Depth", order=0),
    ]
    for index, curve in enumerate(curves, start=1):
        if isinstance(curve, str):
            cards.append(make_header_card("Curve", curve, description=curve, order=index))
        else:
            cards.append(
                make_header_card(
                    "Curve",
                    str(curve.get("mnemonic", curve.get("name", "CURVE"))),
                    unit=str(curve.get("unit", "")),
                    description=str(curve.get("description", "")),
                    order=index,
                )
            )
    for index, (key, value) in enumerate(dict(parameters or {}).items()):
        cards.append(make_header_card("Parameter", key, value=value, description="User parameter", order=index))
    return tuple(cards)


def build_header_manifest(cards: Iterable[LasHeaderCard | Mapping[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    manifest: dict[str, dict[str, dict[str, Any]]] = {section: {} for section in SUPPORTED_HEADER_SECTIONS}
    for idx, raw in enumerate(cards):
        card = _coerce_card(raw, fallback_order=idx)
        manifest.setdefault(card.section, {})[card.mnemonic] = {
            "section": card.section,
            "mnemonic": card.mnemonic,
            "unit": card.unit,
            "value": card.value,
            "description": card.description,
            "order": card.order,
            "protected": card.protected,
        }
    return manifest


def flatten_header_manifest(manifest: Mapping[str, Mapping[str, Mapping[str, Any]]]) -> tuple[LasHeaderCard, ...]:
    cards: list[LasHeaderCard] = []
    for section in SUPPORTED_HEADER_SECTIONS:
        section_items = manifest.get(section, {})
        for item in sorted(section_items.values(), key=lambda row: int(row.get("order", 0))):
            cards.append(_coerce_card(item))
    return tuple(cards)


def header_editor_table_rows(cards: Iterable[LasHeaderCard | Mapping[str, Any]]) -> tuple[dict[str, str], ...]:
    rows: list[dict[str, str]] = []
    for card in sorted((_coerce_card(item) for item in cards), key=lambda item: (SUPPORTED_HEADER_SECTIONS.index(item.section), item.order, item.mnemonic)):
        rows.append({
            "section": card.section,
            "order": str(card.order),
            "mnemonic": card.mnemonic,
            "unit": card.unit,
            "value": card.value,
            "description": card.description,
            "protected": "yes" if card.protected else "no",
        })
    return tuple(rows)


def _history(
    history: Sequence[HeaderEditorHistoryEntry],
    *,
    action: str,
    section: str,
    mnemonic: str,
    details: dict[str, Any],
    reason: str,
    source: str,
    timestamp: str | None,
) -> tuple[HeaderEditorHistoryEntry, ...]:
    return tuple(history) + (
        HeaderEditorHistoryEntry(
            action=action,
            section=section,
            mnemonic=mnemonic,
            timestamp=timestamp or _timestamp_utc(),
            details=dict(details),
            reason=reason or "manual",
            source=source or "las_editor.header_editor",
        ),
    )


def _cards_by_key(cards: Iterable[LasHeaderCard | Mapping[str, Any]]) -> dict[tuple[str, str], LasHeaderCard]:
    return {(_coerce_card(item).section, _coerce_card(item).mnemonic): _coerce_card(item) for item in cards}


def add_header_card(
    cards: Iterable[LasHeaderCard | Mapping[str, Any]],
    card: LasHeaderCard | Mapping[str, Any],
    *,
    history: Sequence[HeaderEditorHistoryEntry] = (),
    reason: str = "manual",
    source: str = "las_editor.header_editor",
    timestamp: str | None = None,
) -> HeaderEditorResult:
    current = _cards_by_key(cards)
    new_card = _coerce_card(card, fallback_order=len(current))
    key = (new_card.section, new_card.mnemonic)
    if key in current:
        raise ValueError(f"Header card already exists: {new_card.section}.{new_card.mnemonic}")
    current[key] = new_card
    updated_cards = tuple(sorted(current.values(), key=lambda item: (SUPPORTED_HEADER_SECTIONS.index(item.section), item.order, item.mnemonic)))
    issues = validate_header_cards(updated_cards)
    return HeaderEditorResult(
        cards=updated_cards,
        manifest=build_header_manifest(updated_cards),
        history=_history(history, action="add_header_card", section=new_card.section, mnemonic=new_card.mnemonic, details={"unit": new_card.unit, "value": new_card.value}, reason=reason, source=source, timestamp=timestamp),
        issues=issues,
        diagnostics=(f"LAS header card added: {new_card.section}.{new_card.mnemonic}.", "ASCII data were not modified."),
    )


def update_header_card(
    cards: Iterable[LasHeaderCard | Mapping[str, Any]],
    section: str,
    mnemonic: str,
    *,
    field: str,
    value: Any,
    history: Sequence[HeaderEditorHistoryEntry] = (),
    reason: str = "manual",
    source: str = "las_editor.header_editor",
    timestamp: str | None = None,
) -> HeaderEditorResult:
    normalized_section = normalize_section_name(section)
    normalized_mnemonic = normalize_las_mnemonic(mnemonic, fallback="ITEM")
    field_key = str(field).strip().lower().replace("-", "_").replace(" ", "_")
    if field_key not in {"unit", "value", "description", "order"}:
        raise ValueError(f"Unsupported LAS header field: {field_key}")
    current = _cards_by_key(cards)
    key = (normalized_section, normalized_mnemonic)
    if key not in current:
        raise ValueError(f"Header card was not found: {normalized_section}.{normalized_mnemonic}")
    old = current[key]
    data = {
        "section": old.section,
        "mnemonic": old.mnemonic,
        "unit": old.unit,
        "value": old.value,
        "description": old.description,
        "order": old.order,
        "protected": old.protected,
    }
    if field_key == "unit":
        data[field_key] = normalize_las_unit(value)
    elif field_key == "order":
        data[field_key] = int(value)
    else:
        data[field_key] = str(value if value is not None else "").strip()
    current[key] = _coerce_card(data)
    updated_cards = tuple(sorted(current.values(), key=lambda item: (SUPPORTED_HEADER_SECTIONS.index(item.section), item.order, item.mnemonic)))
    issues = validate_header_cards(updated_cards)
    return HeaderEditorResult(
        cards=updated_cards,
        manifest=build_header_manifest(updated_cards),
        history=_history(history, action="update_header_card", section=normalized_section, mnemonic=normalized_mnemonic, details={"field": field_key, "value": data[field_key]}, reason=reason, source=source, timestamp=timestamp),
        issues=issues,
        diagnostics=(f"LAS header card updated: {normalized_section}.{normalized_mnemonic}.{field_key}.", "Header-only operation completed safely."),
    )


def delete_header_card(
    cards: Iterable[LasHeaderCard | Mapping[str, Any]],
    section: str,
    mnemonic: str,
    *,
    history: Sequence[HeaderEditorHistoryEntry] = (),
    reason: str = "manual",
    source: str = "las_editor.header_editor",
    timestamp: str | None = None,
) -> HeaderEditorResult:
    normalized_section = normalize_section_name(section)
    normalized_mnemonic = normalize_las_mnemonic(mnemonic, fallback="ITEM")
    if _is_protected(normalized_section, normalized_mnemonic):
        raise ValueError(f"Protected mandatory LAS header card cannot be deleted: {normalized_section}.{normalized_mnemonic}")
    current = _cards_by_key(cards)
    key = (normalized_section, normalized_mnemonic)
    if key not in current:
        raise ValueError(f"Header card was not found: {normalized_section}.{normalized_mnemonic}")
    current.pop(key)
    updated_cards = tuple(sorted(current.values(), key=lambda item: (SUPPORTED_HEADER_SECTIONS.index(item.section), item.order, item.mnemonic)))
    issues = validate_header_cards(updated_cards)
    return HeaderEditorResult(
        cards=updated_cards,
        manifest=build_header_manifest(updated_cards),
        history=_history(history, action="delete_header_card", section=normalized_section, mnemonic=normalized_mnemonic, details={}, reason=reason, source=source, timestamp=timestamp),
        issues=issues,
        diagnostics=(f"LAS header card deleted from working copy: {normalized_section}.{normalized_mnemonic}.",),
    )


def validate_header_cards(cards: Iterable[LasHeaderCard | Mapping[str, Any]]) -> tuple[HeaderEditorIssue, ...]:
    manifest = build_header_manifest(cards)
    issues: list[HeaderEditorIssue] = []
    for mnemonic in REQUIRED_VERSION_ITEMS:
        if mnemonic not in manifest.get("Version", {}):
            issues.append(HeaderEditorIssue("error", "VERSION_ITEM_MISSING", f"Required ~Version item is missing: {mnemonic}.", "Version", mnemonic))
    for mnemonic in REQUIRED_WELL_ITEMS:
        if mnemonic not in manifest.get("Well", {}):
            issues.append(HeaderEditorIssue("error", "WELL_ITEM_MISSING", f"Required ~Well item is missing: {mnemonic}.", "Well", mnemonic))
    if "DEPT" not in manifest.get("Curve", {}):
        issues.append(HeaderEditorIssue("error", "DEPTH_CURVE_HEADER_MISSING", "Required ~Curve depth header item is missing: DEPT.", "Curve", "DEPT"))

    try:
        step = float(manifest.get("Well", {}).get("STEP", {}).get("value", "0"))
        if step <= 0:
            issues.append(HeaderEditorIssue("error", "STEP_INVALID", "STEP must be positive.", "Well", "STEP"))
    except (TypeError, ValueError):
        issues.append(HeaderEditorIssue("error", "STEP_INVALID", "STEP must be numeric.", "Well", "STEP"))

    try:
        start = float(manifest.get("Well", {}).get("STRT", {}).get("value", "0"))
        stop = float(manifest.get("Well", {}).get("STOP", {}).get("value", "0"))
        if start > stop:
            issues.append(HeaderEditorIssue("warning", "DEPTH_RANGE_REVERSED", "STRT is greater than STOP; depth direction may need reverse-depth handling.", "Well", "STRT"))
    except (TypeError, ValueError):
        issues.append(HeaderEditorIssue("error", "DEPTH_LIMIT_INVALID", "STRT/STOP values must be numeric.", "Well", "STRT"))

    return tuple(issues)


def render_header_section(section: str, cards: Iterable[LasHeaderCard | Mapping[str, Any]]) -> str:
    normalized_section = normalize_section_name(section)
    selected = sorted((_coerce_card(card) for card in cards if _coerce_card(card).section == normalized_section), key=lambda item: item.order)
    lines = [f"~{normalized_section}"]
    for card in selected:
        unit = f".{card.unit}" if card.unit else "."
        value = f" {card.value}" if card.value else ""
        description = f" : {card.description}" if card.description else ""
        lines.append(f"{card.mnemonic}{unit}{value}{description}")
    return "\n".join(lines)


def render_las_header(cards: Iterable[LasHeaderCard | Mapping[str, Any]]) -> str:
    coerced = tuple(_coerce_card(card) for card in cards)
    return "\n".join(render_header_section(section, coerced) for section in SUPPORTED_HEADER_SECTIONS) + "\n"
