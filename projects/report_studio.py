from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import pandas as pd

from projects.project_manager import append_project_history
from projects.repository import safe_project_id
from projects.well_cards import safe_well_id

PROJECT_REPORT_STUDIO_FILE_NAME = "report_studio.json"
REPORT_EXPORT_FORMATS = {"pdf", "docx", "xlsx", "html", "png", "svg"}
REPORT_SECTION_TYPES = {"summary", "table", "chart", "plot", "image", "interpretation", "statistics", "calculation", "appendix"}
REPORT_PAGE_SIZES = {"A4", "A3", "Letter", "Legal"}
REPORT_ORIENTATIONS = {"portrait", "landscape"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _project_dir(root: Path | str, project_id: str) -> Path:
    return Path(root) / safe_project_id(project_id)


def _report_path(root: Path | str, project_id: str) -> Path:
    return _project_dir(root, project_id) / PROJECT_REPORT_STUDIO_FILE_NAME


def _json_read(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return default


def _json_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _clean_text(value: Any, field_label: str, *, max_length: int = 180, required: bool = False) -> str:
    text = "" if value is None else str(value).strip()
    if required and not text:
        raise ValueError(f"{field_label}: значение обязательно.")
    if len(text) > max_length:
        raise ValueError(f"{field_label}: максимум {max_length} символов.")
    return text


def _safe_id(value: str, default: str = "report") -> str:
    raw = _clean_text(value, "ID", max_length=140) or default
    normalized = re.sub(r"[^0-9A-Za-zА-Яа-я_-]+", "-", raw).strip("-_").lower() or default
    return safe_well_id(normalized)


def _clean_choice(value: Any, allowed: set[str], field_label: str, default: str) -> str:
    text = _clean_text(value, field_label, max_length=60).lower() or default
    if text not in allowed:
        raise ValueError(f"{field_label}: должно быть одним из: {', '.join(sorted(allowed))}.")
    return text


@dataclass(frozen=True)
class ReportSection:
    id: str
    title: str
    section_type: str = "summary"
    source_id: str = ""
    source_type: str = "manual"
    order: int = 0
    notes: str = ""


@dataclass(frozen=True)
class ReportTemplate:
    id: str
    name: str
    page_size: str = "A4"
    orientation: str = "portrait"
    formats: tuple[str, ...] = ("pdf", "html")
    sections: tuple[ReportSection, ...] = ()
    include_title_page: bool = True
    include_table_of_contents: bool = True
    include_watermark: bool = False
    created_at: str = ""
    updated_at: str = ""


@dataclass(frozen=True)
class ReportExportJob:
    id: str
    name: str
    template_id: str
    project_id: str
    well_id: str = ""
    formats: tuple[str, ...] = ("pdf",)
    status: str = "queued"
    output_prefix: str = ""
    created_at: str = ""


@dataclass(frozen=True)
class ReportStudioSummary:
    templates: int
    export_jobs: int
    sections: int
    available_formats: tuple[str, ...]


_DEFAULT_SECTIONS = (
    ReportSection(id="summary", title="Краткое резюме", section_type="summary", order=10),
    ReportSection(id="input-data", title="Исходные данные", section_type="table", order=20),
    ReportSection(id="plots", title="Планшеты и графики", section_type="plot", order=30),
    ReportSection(id="statistics", title="Статистика", section_type="statistics", order=40),
    ReportSection(id="interpretation", title="Интерпретация", section_type="interpretation", order=50),
    ReportSection(id="appendix", title="Приложения", section_type="appendix", order=90),
)


def _section_from_mapping(row: Mapping[str, Any]) -> ReportSection:
    return ReportSection(
        id=_safe_id(str(row.get("id") or row.get("title") or "section"), "section"),
        title=_clean_text(row.get("title"), "Название раздела", required=True),
        section_type=_clean_choice(row.get("section_type"), REPORT_SECTION_TYPES, "Тип раздела", "summary"),
        source_id=_clean_text(row.get("source_id"), "Источник", max_length=160),
        source_type=_clean_text(row.get("source_type"), "Тип источника", max_length=80) or "manual",
        order=int(row.get("order") or 0),
        notes=_clean_text(row.get("notes"), "Заметки", max_length=500),
    )


def normalize_report_sections(sections: Sequence[ReportSection | Mapping[str, Any]] | None) -> tuple[ReportSection, ...]:
    result: list[ReportSection] = []
    for index, section in enumerate(sections or _DEFAULT_SECTIONS):
        if isinstance(section, ReportSection):
            item = section
        elif isinstance(section, Mapping):
            item = _section_from_mapping(section)
        else:
            raise TypeError("Раздел отчета должен быть ReportSection или mapping.")
        if item.section_type not in REPORT_SECTION_TYPES:
            raise ValueError(f"Неизвестный тип раздела: {item.section_type}.")
        order = item.order if item.order else (index + 1) * 10
        result.append(ReportSection(**{**item.__dict__, "order": int(order)}))
    return tuple(sorted(result, key=lambda row: (row.order, row.title.lower())))


def normalize_report_formats(formats: Sequence[str] | None) -> tuple[str, ...]:
    selected = tuple(dict.fromkeys(str(item).lower().strip() for item in (formats or ("pdf", "html")) if str(item).strip()))
    invalid = [item for item in selected if item not in REPORT_EXPORT_FORMATS]
    if invalid:
        raise ValueError(f"Форматы отчета не поддерживаются: {', '.join(invalid)}.")
    return selected or ("pdf",)


def create_report_template(
    root: Path | str,
    project_id: str,
    name: str,
    *,
    page_size: str = "A4",
    orientation: str = "portrait",
    formats: Sequence[str] | None = None,
    sections: Sequence[ReportSection | Mapping[str, Any]] | None = None,
    include_title_page: bool = True,
    include_table_of_contents: bool = True,
    include_watermark: bool = False,
) -> ReportTemplate:
    clean_name = _clean_text(name, "Название шаблона", required=True)
    normalized_page_size = _clean_text(page_size, "Размер страницы", max_length=20).upper() or "A4"
    if normalized_page_size not in REPORT_PAGE_SIZES:
        raise ValueError(f"Размер страницы должен быть одним из: {', '.join(sorted(REPORT_PAGE_SIZES))}.")
    normalized_orientation = _clean_choice(orientation, REPORT_ORIENTATIONS, "Ориентация", "portrait")
    now = _utc_now()
    template = ReportTemplate(
        id=_safe_id(f"{clean_name}-{now}", "report-template"),
        name=clean_name,
        page_size=normalized_page_size,
        orientation=normalized_orientation,
        formats=normalize_report_formats(formats),
        sections=normalize_report_sections(sections),
        include_title_page=bool(include_title_page),
        include_table_of_contents=bool(include_table_of_contents),
        include_watermark=bool(include_watermark),
        created_at=now,
        updated_at=now,
    )
    payload = _json_read(_report_path(root, project_id), {"templates": [], "export_jobs": []})
    templates = payload.get("templates", []) if isinstance(payload, Mapping) else []
    templates.append(_template_to_dict(template))
    _json_write(_report_path(root, project_id), {**payload, "templates": templates})
    append_project_history(root, project_id, "report_template_created", f"Создан шаблон отчета {clean_name}")
    return template


def _template_to_dict(template: ReportTemplate) -> dict[str, Any]:
    return {
        **template.__dict__,
        "formats": list(template.formats),
        "sections": [section.__dict__ for section in template.sections],
    }


def _job_to_dict(job: ReportExportJob) -> dict[str, Any]:
    return {**job.__dict__, "formats": list(job.formats)}


def _template_from_dict(row: Mapping[str, Any]) -> ReportTemplate:
    return ReportTemplate(
        id=_clean_text(row.get("id"), "ID шаблона", required=True),
        name=_clean_text(row.get("name"), "Название шаблона", required=True),
        page_size=_clean_text(row.get("page_size"), "Размер страницы", max_length=20).upper() or "A4",
        orientation=_clean_choice(row.get("orientation"), REPORT_ORIENTATIONS, "Ориентация", "portrait"),
        formats=normalize_report_formats(row.get("formats") or ("pdf", "html")),
        sections=normalize_report_sections(row.get("sections") or _DEFAULT_SECTIONS),
        include_title_page=bool(row.get("include_title_page", True)),
        include_table_of_contents=bool(row.get("include_table_of_contents", True)),
        include_watermark=bool(row.get("include_watermark", False)),
        created_at=_clean_text(row.get("created_at"), "Дата создания", max_length=80),
        updated_at=_clean_text(row.get("updated_at"), "Дата изменения", max_length=80),
    )


def _job_from_dict(row: Mapping[str, Any]) -> ReportExportJob:
    return ReportExportJob(
        id=_clean_text(row.get("id"), "ID задания", required=True),
        name=_clean_text(row.get("name"), "Название задания", required=True),
        template_id=_clean_text(row.get("template_id"), "Шаблон", required=True),
        project_id=_clean_text(row.get("project_id"), "Проект", max_length=140),
        well_id=_clean_text(row.get("well_id"), "Скважина", max_length=140),
        formats=normalize_report_formats(row.get("formats") or ("pdf",)),
        status=_clean_text(row.get("status"), "Статус", max_length=40) or "queued",
        output_prefix=_clean_text(row.get("output_prefix"), "Префикс", max_length=180),
        created_at=_clean_text(row.get("created_at"), "Дата создания", max_length=80),
    )


def list_report_templates(root: Path | str, project_id: str) -> list[ReportTemplate]:
    payload = _json_read(_report_path(root, project_id), {"templates": []})
    rows = payload.get("templates", []) if isinstance(payload, Mapping) else []
    return [_template_from_dict(row) for row in rows if isinstance(row, Mapping)]


def get_report_template(root: Path | str, project_id: str, template_id: str) -> ReportTemplate | None:
    clean_id = _clean_text(template_id, "ID шаблона", required=True)
    for template in list_report_templates(root, project_id):
        if template.id == clean_id:
            return template
    return None


def create_report_export_job(
    root: Path | str,
    project_id: str,
    name: str,
    template_id: str,
    *,
    well_id: str = "",
    formats: Sequence[str] | None = None,
    output_prefix: str = "",
) -> ReportExportJob:
    clean_name = _clean_text(name, "Название экспорта", required=True)
    clean_template_id = _clean_text(template_id, "Шаблон", required=True)
    if get_report_template(root, project_id, clean_template_id) is None:
        raise ValueError("Шаблон отчета не найден.")
    now = _utc_now()
    job = ReportExportJob(
        id=_safe_id(f"{clean_name}-{now}", "report-export"),
        name=clean_name,
        template_id=clean_template_id,
        project_id=safe_project_id(project_id),
        well_id=_clean_text(well_id, "Скважина", max_length=140),
        formats=normalize_report_formats(formats),
        status="queued",
        output_prefix=build_report_output_prefix(clean_name, well_id=well_id),
        created_at=now,
    )
    if output_prefix:
        job = ReportExportJob(**{**job.__dict__, "output_prefix": build_report_output_prefix(output_prefix, well_id=well_id)})
    payload = _json_read(_report_path(root, project_id), {"templates": [], "export_jobs": []})
    jobs = payload.get("export_jobs", []) if isinstance(payload, Mapping) else []
    jobs.append(_job_to_dict(job))
    _json_write(_report_path(root, project_id), {**payload, "export_jobs": jobs})
    append_project_history(root, project_id, "report_export_queued", f"Подготовлен экспорт отчета {clean_name}")
    return job


def list_report_export_jobs(root: Path | str, project_id: str) -> list[ReportExportJob]:
    payload = _json_read(_report_path(root, project_id), {"export_jobs": []})
    rows = payload.get("export_jobs", []) if isinstance(payload, Mapping) else []
    return [_job_from_dict(row) for row in rows if isinstance(row, Mapping)]


def build_report_output_prefix(title: str, *, well_id: str = "") -> str:
    stem = _safe_id(title, "report")
    well = _safe_id(well_id, "") if well_id else ""
    date = datetime.now(timezone.utc).strftime("%Y%m%d")
    parts = [part for part in (well, stem, date) if part]
    return "_".join(parts) or f"report_{date}"


def build_report_export_manifest(template: ReportTemplate, job: ReportExportJob) -> dict[str, Any]:
    formats = normalize_report_formats(job.formats or template.formats)
    return {
        "job_id": job.id,
        "template_id": template.id,
        "title": job.name,
        "project_id": job.project_id,
        "well_id": job.well_id,
        "page": {"size": template.page_size, "orientation": template.orientation},
        "options": {
            "title_page": template.include_title_page,
            "table_of_contents": template.include_table_of_contents,
            "watermark": template.include_watermark,
        },
        "formats": list(formats),
        "outputs": [f"{job.output_prefix or build_report_output_prefix(job.name, well_id=job.well_id)}.{fmt}" for fmt in formats],
        "sections": [section.__dict__ for section in template.sections],
        "created_at": job.created_at or _utc_now(),
    }


def build_report_template_table(templates: Sequence[ReportTemplate]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ID": item.id,
                "Название": item.name,
                "Страница": item.page_size,
                "Ориентация": item.orientation,
                "Форматы": ", ".join(item.formats),
                "Разделов": len(item.sections),
                "Титульный": "да" if item.include_title_page else "нет",
                "Содержание": "да" if item.include_table_of_contents else "нет",
                "Watermark": "да" if item.include_watermark else "нет",
                "Обновлен": item.updated_at,
            }
            for item in templates
        ]
    )


def build_report_sections_table(sections: Sequence[ReportSection]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Порядок": item.order,
                "ID": item.id,
                "Раздел": item.title,
                "Тип": item.section_type,
                "Источник": item.source_id,
                "Тип источника": item.source_type,
                "Заметки": item.notes,
            }
            for item in normalize_report_sections(sections)
        ]
    )


def build_report_export_jobs_table(jobs: Sequence[ReportExportJob]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ID": item.id,
                "Название": item.name,
                "Шаблон": item.template_id,
                "Проект": item.project_id,
                "Скважина": item.well_id,
                "Форматы": ", ".join(item.formats),
                "Статус": item.status,
                "Префикс": item.output_prefix,
                "Создан": item.created_at,
            }
            for item in jobs
        ]
    )


def summarize_report_studio(root: Path | str, project_id: str) -> ReportStudioSummary:
    templates = list_report_templates(root, project_id)
    jobs = list_report_export_jobs(root, project_id)
    return ReportStudioSummary(
        templates=len(templates),
        export_jobs=len(jobs),
        sections=sum(len(template.sections) for template in templates),
        available_formats=tuple(sorted(REPORT_EXPORT_FORMATS)),
    )
