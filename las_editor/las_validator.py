from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd

from las_editor.ascii_data_editor import validate_ascii_data
from las_editor.header_editor import (
    LasHeaderCard,
    build_header_manifest,
    make_header_card,
    validate_header_cards,
)
from las_editor.las_creator import LAS_MANDATORY_SECTIONS, DEFAULT_NULL_VALUE, normalize_las_mnemonic

LAS_VALIDATOR_STORAGE_KEY = "las_validator"
MANDATORY_HEADER_SECTIONS: tuple[str, ...] = ("Version", "Well", "Curve", "Parameter")
REQUIRED_CURVE_MNEMONICS: tuple[str, ...] = ("DEPT",)
DEPTH_MNEMONICS: tuple[str, ...] = ("DEPT", "DEPTH", "MD", "TVD")


@dataclass(frozen=True)
class LasValidationFinding:
    """One normalized LAS validation finding.

    Severity levels are deliberately simple so the same object can be shown in
    Streamlit tables, exported to JSON or rendered into a text quality report.
    """

    severity: str
    code: str
    message: str
    section: str = ""
    mnemonic: str = ""
    row: int | None = None
    column: str = ""
    recommendation: str = ""


@dataclass(frozen=True)
class LasValidationReport:
    """Full validation result for a LAS document or an editable LAS workspace."""

    status: str
    checked_at: str
    findings: tuple[LasValidationFinding, ...]
    summary: dict[str, Any]
    sections_present: tuple[str, ...] = ()
    diagnostics: tuple[str, ...] = ()

    @property
    def is_valid(self) -> bool:
        return not any(item.severity == "error" for item in self.findings)

    @property
    def error_count(self) -> int:
        return sum(1 for item in self.findings if item.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for item in self.findings if item.severity == "warning")

    @property
    def info_count(self) -> int:
        return sum(1 for item in self.findings if item.severity == "info")


def _timestamp_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _normalize_section_token(section: object) -> str:
    raw = str(section or "").strip()
    if not raw:
        return ""
    raw = raw if raw.startswith("~") else f"~{raw}"
    head = raw.split()[0].strip().lower()
    aliases = {
        "~v": "~Version",
        "~version": "~Version",
        "~versions": "~Version",
        "~w": "~Well",
        "~well": "~Well",
        "~c": "~Curve",
        "~curve": "~Curve",
        "~curves": "~Curve",
        "~p": "~Parameter",
        "~parameter": "~Parameter",
        "~parameters": "~Parameter",
        "~a": "~ASCII",
        "~ascii": "~ASCII",
        "~other": "~Other",
    }
    return aliases.get(head, raw.split()[0])


def detect_las_sections(las_text: str) -> tuple[str, ...]:
    """Detect LAS section headers from raw LAS text."""

    sections: list[str] = []
    for line in str(las_text or "").splitlines():
        stripped = line.strip()
        if not stripped.startswith("~"):
            continue
        token = _normalize_section_token(stripped)
        if token and token not in sections:
            sections.append(token)
    return tuple(sections)


def validate_las_sections(sections: Iterable[str]) -> tuple[LasValidationFinding, ...]:
    present = {_normalize_section_token(section) for section in sections if _normalize_section_token(section)}
    findings: list[LasValidationFinding] = []
    for section in LAS_MANDATORY_SECTIONS:
        if section not in present:
            findings.append(
                LasValidationFinding(
                    "error",
                    "SECTION_MISSING",
                    f"Обязательная секция LAS отсутствует: {section}.",
                    section=section,
                    recommendation="Добавьте секцию перед сохранением или экспортом LAS-файла.",
                )
            )
    if "~Other" not in present:
        findings.append(
            LasValidationFinding(
                "info",
                "OTHER_SECTION_OPTIONAL",
                "Секция ~Other отсутствует. Это допустимо, но ее можно использовать для комментариев и истории обработки.",
                section="~Other",
            )
        )
    return tuple(findings)


def _coerce_cards(cards: Iterable[LasHeaderCard | Mapping[str, Any]]) -> tuple[LasHeaderCard, ...]:
    result: list[LasHeaderCard] = []
    for idx, card in enumerate(cards):
        if isinstance(card, LasHeaderCard):
            result.append(card)
        else:
            result.append(
                make_header_card(
                    str(card.get("section", "Well")),
                    str(card.get("mnemonic", card.get("name", "ITEM"))),
                    unit=str(card.get("unit", "")),
                    value=card.get("value", ""),
                    description=str(card.get("description", "")),
                    order=int(card.get("order", idx)),
                    protected=card.get("protected"),
                )
            )
    return tuple(result)


def validate_las_header(cards: Iterable[LasHeaderCard | Mapping[str, Any]]) -> tuple[LasValidationFinding, ...]:
    normalized = _coerce_cards(cards)
    findings: list[LasValidationFinding] = []

    for issue in validate_header_cards(normalized):
        findings.append(
            LasValidationFinding(
                issue.severity,
                issue.code,
                issue.message,
                section=issue.section,
                mnemonic=issue.mnemonic,
                recommendation="Проверьте карточку заголовка в LAS Header Editor.",
            )
        )

    manifest = build_header_manifest(normalized)
    for section in MANDATORY_HEADER_SECTIONS:
        if section not in manifest or not manifest[section]:
            findings.append(
                LasValidationFinding(
                    "error" if section != "Parameter" else "warning",
                    "HEADER_SECTION_EMPTY",
                    f"Секция заголовка {section} не содержит карточек.",
                    section=section,
                    recommendation="Заполните минимальные metadata секции.",
                )
            )

    curve_cards = manifest.get("Curve", {})
    for mnemonic in REQUIRED_CURVE_MNEMONICS:
        if mnemonic not in curve_cards:
            findings.append(
                LasValidationFinding(
                    "error",
                    "DEPTH_CURVE_CARD_MISSING",
                    f"В секции ~Curve отсутствует обязательная кривая глубины {mnemonic}.",
                    section="Curve",
                    mnemonic=mnemonic,
                    recommendation="Добавьте карточку DEPT в Header Editor или пересоздайте LAS через мастер.",
                )
            )

    seen: set[tuple[str, str]] = set()
    for card in normalized:
        key = (card.section, card.mnemonic)
        if key in seen:
            findings.append(
                LasValidationFinding(
                    "warning",
                    "DUPLICATE_HEADER_CARD",
                    f"Повторяющаяся карточка заголовка: {card.section}.{card.mnemonic}.",
                    section=card.section,
                    mnemonic=card.mnemonic,
                    recommendation="Оставьте одну актуальную карточку или переименуйте дубликат.",
                )
            )
        seen.add(key)

    return tuple(findings)


def _depth_column(df: pd.DataFrame) -> str | None:
    normalized = {normalize_las_mnemonic(column): str(column) for column in df.columns}
    for candidate in DEPTH_MNEMONICS:
        if candidate in normalized:
            return normalized[candidate]
    return None


def validate_curve_ascii_alignment(
    cards: Iterable[LasHeaderCard | Mapping[str, Any]],
    ascii_data: pd.DataFrame,
) -> tuple[LasValidationFinding, ...]:
    normalized = _coerce_cards(cards)
    curve_cards = [card for card in normalized if card.section == "Curve"]
    curve_mnemonics = {normalize_las_mnemonic(card.mnemonic) for card in curve_cards}
    data_columns = {normalize_las_mnemonic(column) for column in ascii_data.columns}

    findings: list[LasValidationFinding] = []
    for column in sorted(data_columns - curve_mnemonics):
        findings.append(
            LasValidationFinding(
                "warning",
                "ASCII_COLUMN_WITHOUT_CURVE_CARD",
                f"Колонка ASCII {column} отсутствует в секции ~Curve.",
                section="~ASCII",
                mnemonic=column,
                column=column,
                recommendation="Добавьте соответствующую карточку кривой в ~Curve.",
            )
        )
    for mnemonic in sorted(curve_mnemonics - data_columns):
        findings.append(
            LasValidationFinding(
                "warning",
                "CURVE_CARD_WITHOUT_ASCII_COLUMN",
                f"Кривая {mnemonic} описана в ~Curve, но отсутствует в ASCII-таблице.",
                section="Curve",
                mnemonic=mnemonic,
                recommendation="Добавьте колонку данных или удалите неиспользуемую карточку.",
            )
        )
    if len(curve_mnemonics) != len(curve_cards):
        findings.append(
            LasValidationFinding(
                "warning",
                "DUPLICATE_CURVE_MNEMONICS",
                "В секции ~Curve найдены повторяющиеся мнемоники кривых.",
                section="Curve",
                recommendation="Переименуйте дубликаты кривых через Curve Manager.",
            )
        )
    return tuple(findings)


def validate_las_ascii(
    ascii_data: pd.DataFrame,
    *,
    expected_step: float | None = None,
    start_depth: float | None = None,
    stop_depth: float | None = None,
    null_value: float = DEFAULT_NULL_VALUE,
) -> tuple[LasValidationFinding, ...]:
    findings: list[LasValidationFinding] = []
    for issue in validate_ascii_data(ascii_data, expected_step=expected_step, null_value=null_value):
        findings.append(
            LasValidationFinding(
                issue.severity,
                issue.code,
                issue.message,
                section="~ASCII",
                row=issue.row,
                column=issue.column,
                recommendation="Исправьте значения в ASCII Data Editor.",
            )
        )

    column = _depth_column(ascii_data)
    if column:
        depths = pd.to_numeric(ascii_data[column], errors="coerce").dropna()
        if not depths.empty:
            first = float(depths.iloc[0])
            last = float(depths.iloc[-1])
            if start_depth is not None and abs(first - float(start_depth)) > 1e-6:
                findings.append(
                    LasValidationFinding(
                        "warning",
                        "START_DEPTH_MISMATCH",
                        f"Первая глубина ASCII ({first:g}) не совпадает с STRT ({float(start_depth):g}).",
                        section="~ASCII",
                        column=column,
                        recommendation="Синхронизируйте STRT в заголовке или исправьте первую строку ASCII.",
                    )
                )
            if stop_depth is not None and abs(last - float(stop_depth)) > 1e-6:
                findings.append(
                    LasValidationFinding(
                        "warning",
                        "STOP_DEPTH_MISMATCH",
                        f"Последняя глубина ASCII ({last:g}) не совпадает с STOP ({float(stop_depth):g}).",
                        section="~ASCII",
                        column=column,
                        recommendation="Синхронизируйте STOP в заголовке или исправьте последнюю строку ASCII.",
                    )
                )
    return tuple(findings)


def _header_numeric(manifest: Mapping[str, Mapping[str, Mapping[str, Any]]], section: str, mnemonic: str) -> float | None:
    try:
        value = manifest[section][mnemonic]["value"]
        return float(str(value).replace(",", "."))
    except Exception:
        return None


def validate_las_workspace(
    *,
    cards: Iterable[LasHeaderCard | Mapping[str, Any]],
    ascii_data: pd.DataFrame,
    sections: Iterable[str] | None = None,
    las_text: str | None = None,
    null_value: float | None = None,
) -> LasValidationReport:
    """Validate editable LAS workspace objects before export.

    The function does not write files and does not mutate the source DataFrame.
    It is designed for the UI layer: Header Editor + ASCII Editor + Curve Manager
    can call it before building a new LAS file.
    """

    normalized_cards = _coerce_cards(cards)
    present_sections = tuple(sections or (detect_las_sections(las_text or "") if las_text else LAS_MANDATORY_SECTIONS))
    manifest = build_header_manifest(normalized_cards)
    step = _header_numeric(manifest, "Well", "STEP")
    start = _header_numeric(manifest, "Well", "STRT")
    stop = _header_numeric(manifest, "Well", "STOP")
    header_null = _header_numeric(manifest, "Well", "NULL")
    effective_null = null_value if null_value is not None else (header_null if header_null is not None else DEFAULT_NULL_VALUE)

    findings = (
        *validate_las_sections(present_sections),
        *validate_las_header(normalized_cards),
        *validate_curve_ascii_alignment(normalized_cards, ascii_data),
        *validate_las_ascii(ascii_data, expected_step=step, start_depth=start, stop_depth=stop, null_value=float(effective_null)),
    )

    summary = build_validation_summary(findings, ascii_data=ascii_data, cards=normalized_cards, sections=present_sections)
    status = "failed" if summary["errors"] else ("warning" if summary["warnings"] else "passed")
    return LasValidationReport(
        status=status,
        checked_at=_timestamp_utc(),
        findings=tuple(findings),
        summary=summary,
        sections_present=tuple(_normalize_section_token(section) for section in present_sections),
        diagnostics=(
            "LAS validation completed in read-only mode.",
            "Исходный LAS-файл не изменялся.",
        ),
    )


def build_validation_summary(
    findings: Iterable[LasValidationFinding],
    *,
    ascii_data: pd.DataFrame | None = None,
    cards: Sequence[LasHeaderCard] = (),
    sections: Iterable[str] = (),
) -> dict[str, Any]:
    items = tuple(findings)
    summary = {
        "errors": sum(1 for item in items if item.severity == "error"),
        "warnings": sum(1 for item in items if item.severity == "warning"),
        "info": sum(1 for item in items if item.severity == "info"),
        "finding_count": len(items),
        "section_count": len(tuple(sections)),
        "header_card_count": len(cards),
        "ascii_row_count": 0 if ascii_data is None else int(len(ascii_data)),
        "ascii_curve_count": 0 if ascii_data is None else int(len(ascii_data.columns)),
    }
    summary["status"] = "failed" if summary["errors"] else ("warning" if summary["warnings"] else "passed")
    return summary


def validation_table_rows(findings: Iterable[LasValidationFinding]) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "severity": item.severity,
            "code": item.code,
            "section": item.section,
            "mnemonic": item.mnemonic,
            "row": item.row,
            "column": item.column,
            "message": item.message,
            "recommendation": item.recommendation,
        }
        for item in findings
    )


def render_validation_report(report: LasValidationReport) -> str:
    lines = [
        "# LAS Validation Report",
        "",
        f"Status: {report.status}",
        f"Checked at: {report.checked_at}",
        f"Errors: {report.error_count}",
        f"Warnings: {report.warning_count}",
        f"Info: {report.info_count}",
        "",
        "## Findings",
    ]
    if not report.findings:
        lines.append("No validation findings.")
    for idx, item in enumerate(report.findings, start=1):
        location = ", ".join(part for part in (item.section, item.mnemonic, item.column, f"row={item.row}" if item.row is not None else "") if part)
        lines.append(f"{idx}. [{item.severity.upper()}] {item.code}: {item.message}" + (f" ({location})" if location else ""))
        if item.recommendation:
            lines.append(f"   Recommendation: {item.recommendation}")
    return "\n".join(lines)
