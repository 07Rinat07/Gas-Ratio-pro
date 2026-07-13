from __future__ import annotations

"""Compact, project-scoped history of successful professional exports.

Only lightweight metadata is stored. Rendered binaries, dataframes, credentials,
and full engineering payloads are intentionally excluded.
"""

from dataclasses import dataclass
from hashlib import sha256
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Sequence

EXPORT_HISTORY_SCHEMA = "gas-ratio-pro/export-history/v3"
LEGACY_EXPORT_HISTORY_SCHEMAS = frozenset({
    "gas-ratio-pro/export-history/v1",
    "gas-ratio-pro/export-history/v2",
})
_ALLOWED_SECTIONS = frozenset({"plots", "visualizations", "results", "conclusion"})
_SAFE_ID = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass(frozen=True)
class ExportHistoryEntry:
    project_id: str
    file_name: str
    format_id: str
    format_label: str
    profile_id: str
    depth_top: float
    depth_bottom: float
    size_bytes: int
    request_signature: str = ""
    cache_hit: bool = False
    report_mode_id: str = "full_engineering"
    template_id: str = "engineering"
    report_title: str = "Gas Ratio Professional Report"
    sections: tuple[str, ...] = ("plots", "visualizations", "results", "conclusion")
    include_technical_appendix: bool = True
    show_page_chrome: bool = True
    print_mode: str = "Выбрать отдельно"
    data_revision: str = ""
    project_updated_at: str = ""
    created_at: str = ""

    def normalized(self) -> "ExportHistoryEntry":
        project_id = str(self.project_id or "").strip()
        file_name = Path(str(self.file_name or "").strip()).name
        if not project_id:
            raise ValueError("project_id is required")
        if not file_name:
            raise ValueError("file_name is required")
        top = float(self.depth_top)
        bottom = float(self.depth_bottom)
        if not _is_finite(top) or not _is_finite(bottom):
            raise ValueError("depth range must be finite")
        if top > bottom:
            top, bottom = bottom, top
        sections = tuple(item for item in self.sections if item in _ALLOWED_SECTIONS)
        return ExportHistoryEntry(
            project_id=project_id,
            file_name=file_name,
            format_id=str(self.format_id or "").strip().lower(),
            format_label=str(self.format_label or self.format_id or "").strip(),
            profile_id=str(self.profile_id or "").strip().lower(),
            depth_top=top,
            depth_bottom=bottom,
            size_bytes=max(0, int(self.size_bytes)),
            request_signature=str(self.request_signature or "").strip(),
            cache_hit=bool(self.cache_hit),
            report_mode_id=str(self.report_mode_id or "full_engineering").strip(),
            template_id=str(self.template_id or "engineering").strip(),
            report_title=str(self.report_title or "").strip() or "Gas Ratio Professional Report",
            sections=sections,
            include_technical_appendix=bool(self.include_technical_appendix),
            show_page_chrome=bool(self.show_page_chrome),
            print_mode=str(self.print_mode or "Выбрать отдельно").strip(),
            data_revision=str(self.data_revision or "").strip(),
            project_updated_at=str(self.project_updated_at or "").strip(),
            created_at=self.created_at or datetime.now(timezone.utc).isoformat(),
        )

    def to_dict(self) -> dict[str, Any]:
        value = self.normalized()
        return {
            "project_id": value.project_id,
            "file_name": value.file_name,
            "format_id": value.format_id,
            "format_label": value.format_label,
            "profile_id": value.profile_id,
            "depth_top": value.depth_top,
            "depth_bottom": value.depth_bottom,
            "size_bytes": value.size_bytes,
            "request_signature": value.request_signature,
            "cache_hit": value.cache_hit,
            "report": {
                "mode_id": value.report_mode_id,
                "template_id": value.template_id,
                "title": value.report_title,
                "sections": list(value.sections),
                "include_technical_appendix": value.include_technical_appendix,
                "show_page_chrome": value.show_page_chrome,
            },
            "print_mode": value.print_mode,
            "data_revision": value.data_revision,
            "project_updated_at": value.project_updated_at,
            "created_at": value.created_at,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ExportHistoryEntry":
        report = payload.get("report", {})
        if not isinstance(report, Mapping):
            report = {}
        return cls(
            project_id=str(payload.get("project_id", "")),
            file_name=str(payload.get("file_name", "")),
            format_id=str(payload.get("format_id", "")),
            format_label=str(payload.get("format_label", "")),
            profile_id=str(payload.get("profile_id", "")),
            depth_top=float(payload.get("depth_top", 0.0)),
            depth_bottom=float(payload.get("depth_bottom", 0.0)),
            size_bytes=int(payload.get("size_bytes", 0)),
            request_signature=str(payload.get("request_signature", "")),
            cache_hit=bool(payload.get("cache_hit", False)),
            report_mode_id=str(report.get("mode_id", "full_engineering")),
            template_id=str(report.get("template_id", "engineering")),
            report_title=str(report.get("title", "Gas Ratio Professional Report")),
            sections=tuple(str(item) for item in report.get("sections", ("plots", "visualizations", "results", "conclusion"))),
            include_technical_appendix=bool(report.get("include_technical_appendix", True)),
            show_page_chrome=bool(report.get("show_page_chrome", True)),
            print_mode=str(payload.get("print_mode", "Выбрать отдельно")),
            data_revision=str(payload.get("data_revision", "")),
            project_updated_at=str(payload.get("project_updated_at", "")),
            created_at=str(payload.get("created_at", "")),
        ).normalized()


    def repeat_payload(self) -> dict[str, Any]:
        """Return the complete safe configuration required to repeat this export."""

        value = self.normalized()
        return {
            "profile_id": value.profile_id,
            "format_id": value.format_id,
            "depth_top": value.depth_top,
            "depth_bottom": value.depth_bottom,
            "report_mode_id": value.report_mode_id,
            "template_id": value.template_id,
            "report_title": value.report_title,
            "sections": list(value.sections),
            "include_technical_appendix": value.include_technical_appendix,
            "show_page_chrome": value.show_page_chrome,
            "print_mode": value.print_mode,
        }


@dataclass(frozen=True)
class RepeatExportConfirmation:
    """Human-readable confirmation for rebuilding a historical export."""

    title: str
    lines: tuple[str, ...]
    stale: bool


def build_repeat_export_confirmation(
    entry: ExportHistoryEntry,
    *,
    comparison: "ExportRevisionComparison",
) -> RepeatExportConfirmation:
    """Build a safe preflight summary before a historical export is rebuilt."""

    value = entry.normalized()
    title = "Пересобрать отчёт по сохранённой конфигурации?"
    lines = (
        f"Файл: {value.file_name}",
        f"Формат: {value.format_label or value.format_id.upper()}",
        f"Профиль: {value.profile_id}",
        f"Диапазон: {value.depth_top:g}–{value.depth_bottom:g} м",
        f"Режим: {value.report_mode_id}",
        f"Шаблон: {value.template_id}",
        comparison.message,
    )
    return RepeatExportConfirmation(title=title, lines=lines, stale=comparison.stale)


@dataclass(frozen=True)
class ExportRevisionComparison:
    """Result of comparing historical export data with the active project data."""

    status: str
    message: str

    @property
    def stale(self) -> bool:
        return self.status == "stale"

    @property
    def comparable(self) -> bool:
        return self.status in {"current", "stale"}


def build_export_data_revision(
    *,
    project_id: str,
    source_signature: str,
    calculation_revision: int,
) -> str:
    """Build a lightweight revision fingerprint without hashing dataframe payloads."""

    payload = "|".join(
        (
            str(project_id or "").strip(),
            str(source_signature or "").strip(),
            str(max(0, int(calculation_revision))),
        )
    )
    if not payload.replace("|", ""):
        return ""
    return sha256(payload.encode("utf-8")).hexdigest()


def compare_export_data_revision(
    entry: ExportHistoryEntry,
    *,
    current_revision: str,
    current_project_updated_at: str = "",
) -> ExportRevisionComparison:
    """Compare a history entry with the active project revision.

    Legacy entries without a revision are reported as unknown instead of being
    treated as current. A stale result is advisory: the user may still restore
    the old configuration, but the file must be rendered again.
    """

    historical = entry.normalized()
    current = str(current_revision or "").strip()
    if not historical.data_revision:
        return ExportRevisionComparison(
            status="unknown",
            message="Для этой старой записи ревизия данных не сохранена.",
        )
    if not current:
        return ExportRevisionComparison(
            status="unknown",
            message="Текущую ревизию данных определить не удалось.",
        )
    if historical.data_revision == current:
        return ExportRevisionComparison(
            status="current",
            message="Конфигурация создана для текущей ревизии данных.",
        )
    changed_at = str(current_project_updated_at or "").strip()
    suffix = f" Проект обновлён: {changed_at}." if changed_at else ""
    return ExportRevisionComparison(
        status="stale",
        message=(
            "Данные проекта изменились после этого экспорта. Настройки можно "
            "восстановить, но отчёт необходимо сформировать заново." + suffix
        ),
    )

@dataclass(frozen=True)
class ExportHistoryFilter:
    """Renderer-neutral filters for the compact export history."""

    search: str = ""
    format_id: str = ""
    profile_id: str = ""

    def normalized(self) -> "ExportHistoryFilter":
        return ExportHistoryFilter(
            search=str(self.search or "").strip().casefold(),
            format_id=str(self.format_id or "").strip().lower(),
            profile_id=str(self.profile_id or "").strip().lower(),
        )


def filter_export_history(
    entries: Iterable[ExportHistoryEntry],
    filters: ExportHistoryFilter | None = None,
) -> tuple[ExportHistoryEntry, ...]:
    """Return history entries matching text, format and profile filters.

    The function does not mutate repository state and is safe to reuse from
    Streamlit, desktop or CLI shells.
    """

    value = (filters or ExportHistoryFilter()).normalized()
    result: list[ExportHistoryEntry] = []
    for raw_entry in entries:
        entry = raw_entry.normalized()
        if value.format_id and entry.format_id != value.format_id:
            continue
        if value.profile_id and entry.profile_id != value.profile_id:
            continue
        if value.search:
            haystack = " ".join(
                (entry.file_name, entry.format_label, entry.profile_id, entry.report_mode_id, entry.template_id, entry.report_title, entry.created_at)
            ).casefold()
            if value.search not in haystack:
                continue
        result.append(entry)
    return tuple(result)


class ExportHistoryRepository:
    def __init__(self, root_dir: Path | str, *, max_entries: int = 20) -> None:
        self.root_dir = Path(root_dir)
        self.max_entries = max(1, int(max_entries))

    def path_for(self, project_id: str) -> Path:
        safe_id = _SAFE_ID.sub("_", str(project_id or "").strip()).strip("._")
        if not safe_id:
            raise ValueError("project_id is required")
        return self.root_dir / safe_id / "export_history.json"

    def load(self, project_id: str) -> tuple[ExportHistoryEntry, ...]:
        target = self.path_for(project_id)
        if not target.exists():
            return ()
        payload = json.loads(target.read_text(encoding="utf-8"))
        schema = payload.get("schema") if isinstance(payload, Mapping) else None
        if not isinstance(payload, Mapping) or schema not in ({EXPORT_HISTORY_SCHEMA} | LEGACY_EXPORT_HISTORY_SCHEMAS):
            raise ValueError("unsupported export history schema")
        raw_entries = payload.get("entries", ())
        if not isinstance(raw_entries, Sequence) or isinstance(raw_entries, (str, bytes, bytearray)):
            raise ValueError("invalid export history payload")
        entries = tuple(ExportHistoryEntry.from_dict(item) for item in raw_entries if isinstance(item, Mapping))
        expected_project = str(project_id).strip()
        if any(item.project_id != expected_project for item in entries):
            raise ValueError("export history belongs to another project")
        return entries[: self.max_entries]

    def record(self, entry: ExportHistoryEntry) -> Path:
        value = entry.normalized()
        try:
            existing = list(self.load(value.project_id))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            existing = []
        deduplicated = [
            item for item in existing
            if not (
                item.request_signature
                and item.request_signature == value.request_signature
                and item.file_name == value.file_name
            )
        ]
        entries = [value, *deduplicated][: self.max_entries]
        target = self.path_for(value.project_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(
                {
                    "schema": EXPORT_HISTORY_SCHEMA,
                    "project_id": value.project_id,
                    "entries": [item.to_dict() for item in entries],
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ) + "\n",
            encoding="utf-8",
        )
        temporary.replace(target)
        return target

    def clear(self, project_id: str) -> bool:
        target = self.path_for(project_id)
        if not target.exists():
            return False
        target.unlink()
        return True


def _is_finite(value: float) -> bool:
    return value == value and value not in (float("inf"), float("-inf"))
