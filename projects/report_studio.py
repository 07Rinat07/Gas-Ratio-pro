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

# ---------------------------------------------------------------------------
# Stage 132: Advanced Report Studio Professional
# ---------------------------------------------------------------------------

REPORT_CONTENT_BLOCK_TYPES = {
    "paragraph",
    "table",
    "image",
    "plot",
    "statistics",
    "interpretation",
    "calculation",
    "page_break",
}
REPORT_JOB_STATUSES = {"queued", "running", "completed", "failed", "cancelled"}


@dataclass(frozen=True)
class ReportContentBlock:
    id: str
    section_id: str
    block_type: str = "paragraph"
    title: str = ""
    content: str = ""
    source_id: str = ""
    order: int = 0
    options: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class ReportPackage:
    id: str
    name: str
    template_id: str
    project_id: str
    well_id: str = ""
    blocks: tuple[ReportContentBlock, ...] = ()
    variables: Mapping[str, Any] | None = None
    created_at: str = ""
    updated_at: str = ""


@dataclass(frozen=True)
class ReportValidationIssue:
    severity: str
    code: str
    message: str
    object_id: str = ""


@dataclass(frozen=True)
class ReportRenderPreview:
    title: str
    page_size: str
    orientation: str
    sections: int
    blocks: int
    estimated_pages: int
    table_of_contents: tuple[dict[str, Any], ...]


def _block_to_dict(block: ReportContentBlock) -> dict[str, Any]:
    return {**block.__dict__, "options": dict(block.options or {})}


def _package_to_dict(package: ReportPackage) -> dict[str, Any]:
    return {
        **package.__dict__,
        "blocks": [_block_to_dict(block) for block in package.blocks],
        "variables": dict(package.variables or {}),
    }


def _block_from_mapping(row: Mapping[str, Any]) -> ReportContentBlock:
    block_type = _clean_choice(row.get("block_type"), REPORT_CONTENT_BLOCK_TYPES, "Тип блока", "paragraph")
    return ReportContentBlock(
        id=_safe_id(str(row.get("id") or row.get("title") or "block"), "block"),
        section_id=_safe_id(str(row.get("section_id") or "summary"), "summary"),
        block_type=block_type,
        title=_clean_text(row.get("title"), "Заголовок блока", max_length=180),
        content=_clean_text(row.get("content"), "Содержимое блока", max_length=8000),
        source_id=_clean_text(row.get("source_id"), "Источник блока", max_length=180),
        order=int(row.get("order") or 0),
        options=row.get("options") if isinstance(row.get("options"), Mapping) else {},
    )


def normalize_report_blocks(blocks: Sequence[ReportContentBlock | Mapping[str, Any]] | None) -> tuple[ReportContentBlock, ...]:
    result: list[ReportContentBlock] = []
    for index, block in enumerate(blocks or ()):  # no default content blocks
        if isinstance(block, ReportContentBlock):
            item = block
        elif isinstance(block, Mapping):
            item = _block_from_mapping(block)
        else:
            raise TypeError("Блок отчета должен быть ReportContentBlock или mapping.")
        if item.block_type not in REPORT_CONTENT_BLOCK_TYPES:
            raise ValueError(f"Неизвестный тип блока отчета: {item.block_type}.")
        order = item.order if item.order else (index + 1) * 10
        result.append(ReportContentBlock(**{**item.__dict__, "order": int(order), "options": dict(item.options or {})}))
    return tuple(sorted(result, key=lambda row: (row.order, row.section_id, row.title.lower())))


def _package_from_dict(row: Mapping[str, Any]) -> ReportPackage:
    return ReportPackage(
        id=_clean_text(row.get("id"), "ID пакета", required=True),
        name=_clean_text(row.get("name"), "Название пакета", required=True),
        template_id=_clean_text(row.get("template_id"), "Шаблон", required=True),
        project_id=_clean_text(row.get("project_id"), "Проект", max_length=140),
        well_id=_clean_text(row.get("well_id"), "Скважина", max_length=140),
        blocks=normalize_report_blocks(row.get("blocks") or ()),
        variables=row.get("variables") if isinstance(row.get("variables"), Mapping) else {},
        created_at=_clean_text(row.get("created_at"), "Дата создания", max_length=80),
        updated_at=_clean_text(row.get("updated_at"), "Дата изменения", max_length=80),
    )


def create_report_package(
    root: Path | str,
    project_id: str,
    name: str,
    template_id: str,
    *,
    well_id: str = "",
    blocks: Sequence[ReportContentBlock | Mapping[str, Any]] | None = None,
    variables: Mapping[str, Any] | None = None,
) -> ReportPackage:
    clean_name = _clean_text(name, "Название пакета", required=True)
    clean_template_id = _clean_text(template_id, "Шаблон", required=True)
    if get_report_template(root, project_id, clean_template_id) is None:
        raise ValueError("Шаблон отчета не найден.")
    now = _utc_now()
    package = ReportPackage(
        id=_safe_id(f"{clean_name}-{now}", "report-package"),
        name=clean_name,
        template_id=clean_template_id,
        project_id=safe_project_id(project_id),
        well_id=_clean_text(well_id, "Скважина", max_length=140),
        blocks=normalize_report_blocks(blocks),
        variables=dict(variables or {}),
        created_at=now,
        updated_at=now,
    )
    payload = _json_read(_report_path(root, project_id), {"templates": [], "export_jobs": [], "packages": []})
    packages = payload.get("packages", []) if isinstance(payload, Mapping) else []
    packages.append(_package_to_dict(package))
    _json_write(_report_path(root, project_id), {**payload, "packages": packages})
    append_project_history(root, project_id, "report_package_created", f"Собран пакет отчета {clean_name}")
    return package


def list_report_packages(root: Path | str, project_id: str) -> list[ReportPackage]:
    payload = _json_read(_report_path(root, project_id), {"packages": []})
    rows = payload.get("packages", []) if isinstance(payload, Mapping) else []
    return [_package_from_dict(row) for row in rows if isinstance(row, Mapping)]


def get_report_package(root: Path | str, project_id: str, package_id: str) -> ReportPackage | None:
    clean_id = _clean_text(package_id, "ID пакета", required=True)
    for package in list_report_packages(root, project_id):
        if package.id == clean_id:
            return package
    return None


def validate_report_package(template: ReportTemplate, package: ReportPackage) -> tuple[ReportValidationIssue, ...]:
    section_ids = {section.id for section in template.sections}
    issues: list[ReportValidationIssue] = []
    if package.template_id != template.id:
        issues.append(ReportValidationIssue("error", "template_mismatch", "Пакет связан с другим шаблоном.", package.id))
    if not package.blocks:
        issues.append(ReportValidationIssue("warning", "empty_package", "Пакет отчета не содержит блоков.", package.id))
    for block in package.blocks:
        if block.section_id not in section_ids:
            issues.append(ReportValidationIssue("error", "unknown_section", f"Блок привязан к отсутствующему разделу: {block.section_id}.", block.id))
        if block.block_type in {"table", "image", "plot"} and not (block.source_id or block.content):
            issues.append(ReportValidationIssue("warning", "missing_source", "Для визуального/табличного блока не указан источник данных.", block.id))
        if block.block_type == "paragraph" and not block.content.strip():
            issues.append(ReportValidationIssue("warning", "empty_paragraph", "Текстовый блок не содержит текста.", block.id))
    return tuple(issues)


def build_report_validation_table(issues: Sequence[ReportValidationIssue]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Уровень": item.severity,
                "Код": item.code,
                "Сообщение": item.message,
                "Объект": item.object_id,
            }
            for item in issues
        ]
    )


def build_report_package_table(packages: Sequence[ReportPackage]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ID": item.id,
                "Название": item.name,
                "Шаблон": item.template_id,
                "Проект": item.project_id,
                "Скважина": item.well_id,
                "Блоков": len(item.blocks),
                "Переменных": len(item.variables or {}),
                "Обновлен": item.updated_at,
            }
            for item in packages
        ]
    )


def build_report_blocks_table(blocks: Sequence[ReportContentBlock]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Раздел": item.section_id,
                "Порядок": item.order,
                "ID": item.id,
                "Тип": item.block_type,
                "Заголовок": item.title,
                "Источник": item.source_id,
                "Символов": len(item.content),
            }
            for item in normalize_report_blocks(blocks)
        ]
    )


def build_report_render_preview(template: ReportTemplate, package: ReportPackage) -> ReportRenderPreview:
    section_order = {section.id: index + 1 for index, section in enumerate(template.sections)}
    toc = tuple(
        {
            "level": 1,
            "order": section_order[section.id],
            "section_id": section.id,
            "title": section.title,
            "blocks": sum(1 for block in package.blocks if block.section_id == section.id),
        }
        for section in template.sections
    )
    text_units = sum(max(1, len(block.content) // 1800) for block in package.blocks if block.block_type == "paragraph")
    visual_units = sum(1 for block in package.blocks if block.block_type in {"table", "image", "plot", "statistics"})
    estimated_pages = max(1, (1 if template.include_title_page else 0) + (1 if template.include_table_of_contents else 0) + len(template.sections) // 3 + text_units + visual_units)
    return ReportRenderPreview(
        title=package.name,
        page_size=template.page_size,
        orientation=template.orientation,
        sections=len(template.sections),
        blocks=len(package.blocks),
        estimated_pages=estimated_pages,
        table_of_contents=toc,
    )


def build_report_render_manifest(template: ReportTemplate, package: ReportPackage, job: ReportExportJob | None = None) -> dict[str, Any]:
    formats = normalize_report_formats(job.formats if job else template.formats)
    preview = build_report_render_preview(template, package)
    return {
        "package_id": package.id,
        "template_id": template.id,
        "job_id": job.id if job else "",
        "title": package.name,
        "project_id": package.project_id,
        "well_id": package.well_id,
        "page": {"size": template.page_size, "orientation": template.orientation},
        "formats": list(formats),
        "preview": preview.__dict__,
        "sections": [section.__dict__ for section in template.sections],
        "blocks": [_block_to_dict(block) for block in package.blocks],
        "variables": dict(package.variables or {}),
        "validation": [issue.__dict__ for issue in validate_report_package(template, package)],
        "created_at": _utc_now(),
    }


def render_report_html(template: ReportTemplate, package: ReportPackage) -> str:
    """Build a deterministic lightweight HTML draft for preview/export tests.

    The function intentionally does not depend on Streamlit or external PDF engines.
    Professional binary export remains a later rendering-adapter responsibility.
    """
    sections = []
    blocks_by_section: dict[str, list[ReportContentBlock]] = {section.id: [] for section in template.sections}
    for block in normalize_report_blocks(package.blocks):
        blocks_by_section.setdefault(block.section_id, []).append(block)
    if template.include_title_page:
        sections.append(f"<section class='title-page'><h1>{package.name}</h1><p>{package.project_id}</p></section>")
    if template.include_table_of_contents:
        toc = "".join(f"<li>{section.title}</li>" for section in template.sections)
        sections.append(f"<nav class='toc'><h2>Содержание</h2><ol>{toc}</ol></nav>")
    for section in template.sections:
        content = [f"<section id='{section.id}'><h2>{section.title}</h2>"]
        for block in blocks_by_section.get(section.id, []):
            title = f"<h3>{block.title}</h3>" if block.title else ""
            if block.block_type == "paragraph":
                content.append(f"{title}<p>{block.content}</p>")
            elif block.block_type == "page_break":
                content.append("<div class='page-break'></div>")
            else:
                content.append(f"{title}<div class='block {block.block_type}' data-source='{block.source_id}'>{block.content}</div>")
        content.append("</section>")
        sections.append("".join(content))
    return "\n".join(["<!doctype html>", "<html><body>", *sections, "</body></html>"])


def update_report_export_job_status(root: Path | str, project_id: str, job_id: str, status: str) -> ReportExportJob:
    clean_job_id = _clean_text(job_id, "ID задания", required=True)
    clean_status = _clean_choice(status, REPORT_JOB_STATUSES, "Статус задания", "queued")
    payload = _json_read(_report_path(root, project_id), {"export_jobs": []})
    jobs = payload.get("export_jobs", []) if isinstance(payload, Mapping) else []
    updated: ReportExportJob | None = None
    new_jobs: list[dict[str, Any]] = []
    for row in jobs:
        if isinstance(row, Mapping) and row.get("id") == clean_job_id:
            new_row = {**dict(row), "status": clean_status}
            updated = _job_from_dict(new_row)
            new_jobs.append(new_row)
        else:
            new_jobs.append(dict(row) if isinstance(row, Mapping) else row)
    if updated is None:
        raise ValueError("Задание экспорта не найдено.")
    _json_write(_report_path(root, project_id), {**payload, "export_jobs": new_jobs})
    append_project_history(root, project_id, "report_export_status_updated", f"Статус экспорта {clean_job_id}: {clean_status}")
    return updated
