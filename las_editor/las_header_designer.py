from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Any, Iterable, Mapping, Sequence

from las_editor.header_editor import (
    HeaderEditorIssue,
    LasHeaderCard,
    add_header_card,
    build_default_header_cards,
    header_editor_table_rows,
    make_header_card,
    render_las_header,
    update_header_card,
    validate_header_cards,
)
from las_editor.las_creator import LasCurveSpec, normalize_las_mnemonic, normalize_las_unit
from las_editor.depth_grid import build_safe_las_filename
from projects.project_explorer_foundation import (
    OperationJournalEntry,
    OperationStatus,
    build_operation_entry,
)

LAS_HEADER_DESIGNER_SCHEMA = "gas-ratio-pro.las-header-designer.v2"


class HeaderDesignerSection(str, Enum):
    VERSION = "Version"
    WELL = "Well"
    CURVE = "Curve"
    PARAMETER = "Parameter"


@dataclass(frozen=True)
class HeaderDesignerField:
    """One UI-ready field shown by Header Designer 2.0."""

    section: HeaderDesignerSection
    mnemonic: str
    title: str
    required: bool = False
    protected: bool = False
    value: str = ""
    unit: str = ""
    description: str = ""
    help_text: str = ""


@dataclass(frozen=True)
class HeaderDesignerUpdate:
    """A single user-requested header card change."""

    section: str
    mnemonic: str
    field: str
    value: Any
    reason: str = "manual"


@dataclass(frozen=True)
class LasHeaderDesignerSession:
    """Renderer-independent state for Header Designer 2.0."""

    schema: str
    cards: tuple[LasHeaderCard, ...]
    source_object_id: str = ""
    result_object_id: str = ""
    las_version: str = "2.0"
    ascii_section: str = ""
    history: tuple[Any, ...] = ()


@dataclass(frozen=True)
class LasHeaderDesignerPreview:
    """Validated preview displayed before saving a header update."""

    session: LasHeaderDesignerSession
    header_text: str
    issues: tuple[HeaderEditorIssue, ...]
    journal_entry: OperationJournalEntry
    section_rows: tuple[dict[str, Any], ...]
    card_rows: tuple[dict[str, Any], ...]
    field_rows: tuple[dict[str, Any], ...]
    can_finalize: bool


@dataclass(frozen=True)
class LasHeaderDesignerFinalizeResult:
    """Safe-copy result for a confirmed header update."""

    filename: str
    las_text: str
    las_bytes: bytes
    preview: LasHeaderDesignerPreview
    journal_entry: OperationJournalEntry


_REQUIRED_FIELDS: tuple[tuple[str, str, str], ...] = (
    ("Version", "VERS", "LAS version"),
    ("Version", "WRAP", "Line wrapping flag"),
    ("Well", "STRT", "Start depth"),
    ("Well", "STOP", "Stop depth"),
    ("Well", "STEP", "Depth step"),
    ("Well", "NULL", "Null value"),
    ("Curve", "DEPT", "Depth curve"),
)

_WELL_RECOMMENDED: tuple[tuple[str, str], ...] = (
    ("WELL", "Well name"),
    ("FLD", "Field"),
    ("COMP", "Company"),
    ("LOC", "Location"),
    ("CTRY", "Country"),
    ("DATE", "Logging date"),
    ("API", "API number"),
    ("UWI", "Unique well identifier"),
    ("SRVC", "Service company"),
)


def _normalize_section(section: str) -> HeaderDesignerSection:
    raw = str(section or "").strip().replace("~", "").lower()
    if raw.startswith("v"):
        return HeaderDesignerSection.VERSION
    if raw.startswith("w"):
        return HeaderDesignerSection.WELL
    if raw.startswith("c"):
        return HeaderDesignerSection.CURVE
    if raw.startswith("p"):
        return HeaderDesignerSection.PARAMETER
    raise ValueError(f"Unsupported LAS header section: {section!r}")


def _parse_header_line(line: str, section: HeaderDesignerSection, order: int) -> LasHeaderCard | None:
    text = str(line or "").strip()
    if not text or text.startswith("#") or text.startswith("~"):
        return None
    left, _sep, description = text.partition(":")
    mnemonic_part, dot, rest = left.partition(".")
    if not dot:
        return None
    mnemonic = normalize_las_mnemonic(mnemonic_part, fallback="ITEM")
    rest = rest.strip()
    unit = ""
    value = ""
    if rest:
        parts = rest.split(None, 1)
        if len(parts) == 1:
            # Ambiguous LAS card. In ~Curve it is usually a unit; elsewhere it
            # is usually a value. Keep the parser conservative and editable.
            if section == HeaderDesignerSection.CURVE:
                unit = normalize_las_unit(parts[0])
            else:
                value = parts[0]
        else:
            unit = normalize_las_unit(parts[0])
            value = parts[1].strip()
    return make_header_card(section.value, mnemonic, unit=unit, value=value, description=description.strip(), order=order)


def extract_ascii_section(las_text: str) -> str:
    """Return the original ~ASCII section, unchanged.

    Header Designer is a metadata editor. It must not modify measured curve
    values; therefore the original ASCII block is copied byte-for-byte at text
    line level into the safe-copy output.
    """

    lines = str(las_text or "").splitlines()
    for index, line in enumerate(lines):
        if line.strip().upper().startswith("~A"):
            return "\n".join(lines[index:]).rstrip() + "\n"
    return "~ASCII\n"


def parse_las_header_cards(las_text: str) -> tuple[LasHeaderCard, ...]:
    """Parse editable Version/Well/Curve/Parameter cards from LAS text."""

    cards: list[LasHeaderCard] = []
    current: HeaderDesignerSection | None = None
    order_by_section: dict[HeaderDesignerSection, int] = {section: 0 for section in HeaderDesignerSection}
    for raw in str(las_text or "").splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        if stripped.startswith("~"):
            marker = stripped[1:2].upper()
            if marker == "V":
                current = HeaderDesignerSection.VERSION
            elif marker == "W":
                current = HeaderDesignerSection.WELL
            elif marker == "C":
                current = HeaderDesignerSection.CURVE
            elif marker == "P":
                current = HeaderDesignerSection.PARAMETER
            elif marker == "A":
                break
            else:
                current = None
            continue
        if current is None:
            continue
        card = _parse_header_line(stripped, current, order_by_section[current])
        if card is not None:
            cards.append(card)
            order_by_section[current] += 1
    return tuple(cards)


def _ensure_required_cards(cards: Iterable[LasHeaderCard]) -> tuple[LasHeaderCard, ...]:
    current = {(card.section, card.mnemonic): card for card in cards}
    defaults = build_default_header_cards(well_name="WELL", start_depth=0.0, stop_depth=0.0, step=0.1)
    for card in defaults:
        if (card.section, card.mnemonic) in {(section, mnemonic) for section, mnemonic, _ in _REQUIRED_FIELDS}:
            current.setdefault((card.section, card.mnemonic), card)
    return tuple(sorted(current.values(), key=lambda item: (item.section, item.order, item.mnemonic)))


def build_las_header_designer_session(
    *,
    las_text: str = "",
    cards: Iterable[LasHeaderCard | Mapping[str, Any]] = (),
    source_object_id: str = "",
    result_object_id: str = "",
) -> LasHeaderDesignerSession:
    """Create a Header Designer session from LAS text or existing cards."""

    if cards:
        parsed = tuple(make_header_card(str(card.section), card.mnemonic, unit=card.unit, value=card.value, description=card.description, order=card.order, protected=card.protected) if isinstance(card, LasHeaderCard) else make_header_card(str(card.get("section", "Well")), str(card.get("mnemonic", "ITEM")), unit=str(card.get("unit", "")), value=card.get("value", ""), description=str(card.get("description", "")), order=int(card.get("order", 0)), protected=card.get("protected")) for card in cards)
        ascii_section = extract_ascii_section(las_text) if las_text else "~ASCII\n"
    elif las_text:
        parsed = parse_las_header_cards(las_text)
        ascii_section = extract_ascii_section(las_text)
    else:
        parsed = build_default_header_cards()
        ascii_section = "~ASCII\n"
    completed = _ensure_required_cards(parsed)
    version_card = next((card for card in completed if card.section == "Version" and card.mnemonic == "VERS"), None)
    return LasHeaderDesignerSession(
        schema=LAS_HEADER_DESIGNER_SCHEMA,
        cards=completed,
        source_object_id=source_object_id,
        result_object_id=result_object_id,
        las_version=(version_card.value if version_card else "2.0") or "2.0",
        ascii_section=ascii_section,
    )


def header_designer_required_field_rows(session: LasHeaderDesignerSession) -> tuple[dict[str, Any], ...]:
    manifest = {(card.section, card.mnemonic): card for card in session.cards}
    rows: list[dict[str, Any]] = []
    for section, mnemonic, title in _REQUIRED_FIELDS:
        card = manifest.get((section, mnemonic))
        rows.append(
            {
                "section": section,
                "mnemonic": mnemonic,
                "title": title,
                "present": card is not None,
                "value": card.value if card else "",
                "unit": card.unit if card else "",
                "protected": True,
            }
        )
    return tuple(rows)


def header_designer_well_field_rows(session: LasHeaderDesignerSession) -> tuple[dict[str, Any], ...]:
    manifest = {(card.section, card.mnemonic): card for card in session.cards}
    rows: list[dict[str, Any]] = []
    for mnemonic, title in _WELL_RECOMMENDED:
        card = manifest.get(("Well", mnemonic))
        rows.append(
            {
                "section": "Well",
                "mnemonic": mnemonic,
                "title": title,
                "present": card is not None,
                "value": card.value if card else "",
                "unit": card.unit if card else "",
                "description": card.description if card else title,
            }
        )
    return tuple(rows)


def header_designer_section_rows(session: LasHeaderDesignerSession) -> tuple[dict[str, Any], ...]:
    issues = validate_header_cards(session.cards)
    rows: list[dict[str, Any]] = []
    for section in HeaderDesignerSection:
        section_cards = [card for card in session.cards if card.section == section.value]
        section_issues = [issue for issue in issues if issue.section == section.value]
        rows.append(
            {
                "section": section.value,
                "card_count": len(section_cards),
                "error_count": sum(1 for issue in section_issues if issue.severity == "error"),
                "warning_count": sum(1 for issue in section_issues if issue.severity == "warning"),
            }
        )
    return tuple(rows)


def apply_header_designer_updates(
    session: LasHeaderDesignerSession,
    updates: Sequence[HeaderDesignerUpdate | Mapping[str, Any]],
) -> LasHeaderDesignerSession:
    """Apply UI field edits to the session without touching ASCII values."""

    cards = session.cards
    history = session.history
    for raw in updates:
        update = raw if isinstance(raw, HeaderDesignerUpdate) else HeaderDesignerUpdate(
            section=str(raw.get("section", "Well")),
            mnemonic=str(raw.get("mnemonic", "ITEM")),
            field=str(raw.get("field", "value")),
            value=raw.get("value", ""),
            reason=str(raw.get("reason", "manual")),
        )
        try:
            result = update_header_card(cards, update.section, update.mnemonic, field=update.field, value=update.value, history=history, reason=update.reason, source="las_editor.las_header_designer")
        except ValueError as exc:
            if "was not found" not in str(exc):
                raise
            # Header Designer may add optional cards such as COUNTRY/UWI from
            # the form. Missing cards are created as safe metadata rows.
            add_result = add_header_card(
                cards,
                make_header_card(update.section, update.mnemonic, value=update.value if update.field == "value" else "", unit=update.value if update.field == "unit" else "", description="User header field"),
                history=history,
                reason=update.reason,
                source="las_editor.las_header_designer",
            )
            cards = add_result.cards
            history = add_result.history
        else:
            cards = result.cards
            history = result.history
    return LasHeaderDesignerSession(
        schema=session.schema,
        cards=cards,
        source_object_id=session.source_object_id,
        result_object_id=session.result_object_id,
        las_version=next((card.value for card in cards if card.section == "Version" and card.mnemonic == "VERS"), session.las_version),
        ascii_section=session.ascii_section,
        history=tuple(history),
    )


def build_las_header_designer_preview(session: LasHeaderDesignerSession) -> LasHeaderDesignerPreview:
    issues = validate_header_cards(session.cards)
    header_text = render_las_header(session.cards)
    can_finalize = not any(issue.severity == "error" for issue in issues)
    journal = build_operation_entry(
        operation_type="las_header_designer",
        title="Header Designer 2.0 safe-copy update",
        source_object_id=session.source_object_id,
        result_object_id=session.result_object_id,
        status=OperationStatus.PREVIEW,
        creates_copy=True,
        can_undo=True,
        summary="LAS header preview generated. ASCII curve values are preserved unchanged.",
        details={
            "schema": session.schema,
            "card_count": len(session.cards),
            "issue_count": len(issues),
            "ascii_preserved": True,
        },
    )
    return LasHeaderDesignerPreview(
        session=session,
        header_text=header_text,
        issues=issues,
        journal_entry=journal,
        section_rows=header_designer_section_rows(session),
        card_rows=header_editor_table_rows(session.cards),
        field_rows=header_designer_required_field_rows(session) + header_designer_well_field_rows(session),
        can_finalize=can_finalize,
    )


def header_designer_issue_rows(issues: Iterable[HeaderEditorIssue]) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "severity": issue.severity,
            "code": issue.code,
            "message": issue.message,
            "section": issue.section,
            "mnemonic": issue.mnemonic,
        }
        for issue in issues
    )


def _safe_result_filename(session: LasHeaderDesignerSession, filename: str = "") -> str:
    if filename:
        return build_safe_las_filename(filename, suffix="header_updated")
    well = next((card.value for card in session.cards if card.section == "Well" and card.mnemonic == "WELL" and card.value), "well")
    return build_safe_las_filename(f"{well}.las", suffix="header_updated")


def finalize_las_header_designer_update(
    session: LasHeaderDesignerSession,
    *,
    original_las_text: str = "",
    filename: str = "",
) -> LasHeaderDesignerFinalizeResult:
    """Create a new LAS copy with updated header and preserved ASCII data."""

    preview = build_las_header_designer_preview(session)
    if not preview.can_finalize:
        codes = ", ".join(issue.code for issue in preview.issues if issue.severity == "error")
        raise ValueError(f"LAS header cannot be finalized while validation errors exist: {codes}")
    ascii_section = extract_ascii_section(original_las_text) if original_las_text else session.ascii_section
    las_text = preview.header_text.rstrip() + "\n" + ascii_section
    result_filename = _safe_result_filename(session, filename)
    completed_journal = build_operation_entry(
        operation_type="las_header_designer",
        title="Header Designer 2.0 safe-copy update",
        source_object_id=session.source_object_id,
        result_object_id=session.result_object_id or result_filename,
        status=OperationStatus.COMPLETED,
        creates_copy=True,
        can_undo=True,
        summary=f"Header updated in new LAS copy: {result_filename}. ASCII curve values preserved unchanged.",
        details={
            "schema": session.schema,
            "filename": result_filename,
            "card_count": len(session.cards),
            "ascii_preserved": True,
            "original_not_modified": True,
        },
    )
    return LasHeaderDesignerFinalizeResult(
        filename=result_filename,
        las_text=las_text,
        las_bytes=las_text.encode("utf-8"),
        preview=preview,
        journal_entry=completed_journal,
    )
