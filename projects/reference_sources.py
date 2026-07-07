from __future__ import annotations

import hashlib
import json
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from projects.project_manager import append_project_history
from projects.repository import safe_project_id

REFERENCE_SOURCES_DIR_NAME = "sources"
REFERENCE_REGISTRY_FILE_NAME = "source_registry.json"
SUPPORTED_SOURCE_EXTENSIONS = {".pdf"}
LOCAL_WINDOWS_PATH_PATTERN = re.compile(r"^[A-Za-z]:\\")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _project_dir(root: Path | str, project_id: str) -> Path:
    return Path(root) / safe_project_id(project_id)


def _sources_dir(root: Path | str, project_id: str) -> Path:
    return _project_dir(root, project_id) / REFERENCE_SOURCES_DIR_NAME


def _registry_path(root: Path | str, project_id: str) -> Path:
    return _sources_dir(root, project_id) / REFERENCE_REGISTRY_FILE_NAME


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


def _clean_text(value: Any, field_label: str, *, max_length: int = 500, required: bool = False) -> str:
    text = "" if value is None else str(value).strip()
    if required and not text:
        raise ValueError(f"{field_label}: значение обязательно.")
    if len(text) > max_length:
        raise ValueError(f"{field_label}: максимум {max_length} символов.")
    return text


def _safe_slug(value: Any, *, default: str = "source") -> str:
    text = _clean_text(value, "ID", max_length=220) or default
    text = text.lower().replace("ё", "е")
    normalized = "".join(ch if ch.isalnum() else "-" for ch in text)
    normalized = re.sub(r"-+", "-", normalized).strip("-")
    return normalized or default


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative_to_project(root: Path | str, project_id: str, path: Path) -> str:
    try:
        return path.relative_to(_project_dir(root, project_id)).as_posix()
    except ValueError:
        return path.as_posix()


def _compress_pdf(source_path: Path, target_path: Path) -> None:
    """Copy a PDF and apply lossless cleanup when PyMuPDF is available.

    The function never degrades readability intentionally. If the optimizer fails,
    the original PDF is copied as-is. This keeps the reference archive reliable.
    """
    target_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import fitz  # type: ignore

        document = fitz.open(source_path)
        document.save(target_path, garbage=4, deflate=True, clean=True)
        document.close()
        if not target_path.exists() or target_path.stat().st_size <= 0:
            shutil.copy2(source_path, target_path)
    except Exception:
        shutil.copy2(source_path, target_path)


@dataclass(frozen=True)
class ReferenceSource:
    """Registered evidence source stored inside a project package."""

    id: str
    title: str
    relative_path: str
    original_file_name: str
    source_type: str = "pdf"
    authors: tuple[str, ...] = ()
    year: str = ""
    description: str = ""
    used_for: tuple[str, ...] = ()
    pages: tuple[str, ...] = ()
    original_local_path: str = ""
    sha256: str = ""
    size_bytes: int = 0
    compressed: bool = True
    created_at: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ReferenceValidationIssue:
    severity: str
    code: str
    message: str
    source_id: str = ""
    recommendation: str = ""


@dataclass(frozen=True)
class ReferenceSourcesSummary:
    total: int
    pdf: int
    missing_files: int
    local_path_references: int
    size_bytes: int


def reference_source_to_dict(source: ReferenceSource) -> dict[str, Any]:
    return {
        "id": source.id,
        "title": source.title,
        "relative_path": source.relative_path,
        "original_file_name": source.original_file_name,
        "source_type": source.source_type,
        "authors": list(source.authors),
        "year": source.year,
        "description": source.description,
        "used_for": list(source.used_for),
        "pages": list(source.pages),
        "original_local_path": source.original_local_path,
        "sha256": source.sha256,
        "size_bytes": source.size_bytes,
        "compressed": source.compressed,
        "created_at": source.created_at,
        "metadata": dict(source.metadata),
    }


def normalize_reference_source(raw: ReferenceSource | Mapping[str, Any]) -> ReferenceSource:
    if isinstance(raw, ReferenceSource):
        data = reference_source_to_dict(raw)
    elif isinstance(raw, Mapping):
        data = dict(raw)
    else:
        raise TypeError("Reference source должен быть ReferenceSource или mapping.")

    source_id = _safe_slug(data.get("id") or data.get("title") or data.get("original_file_name"))
    title = _clean_text(data.get("title") or source_id, "Название источника", max_length=300, required=True)
    relative_path = _clean_text(data.get("relative_path"), "Относительный путь", max_length=700, required=True)
    original_file_name = _clean_text(data.get("original_file_name") or Path(relative_path).name, "Имя файла", max_length=260)
    source_type = _clean_text(data.get("source_type") or Path(relative_path).suffix.lstrip("."), "Тип источника", max_length=40).lower() or "pdf"

    return ReferenceSource(
        id=source_id,
        title=title,
        relative_path=relative_path.replace("\\\\", "/"),
        original_file_name=original_file_name,
        source_type=source_type,
        authors=tuple(_clean_text(item, "Автор", max_length=160) for item in data.get("authors", ()) if _clean_text(item, "Автор", max_length=160)),
        year=_clean_text(data.get("year"), "Год", max_length=20),
        description=_clean_text(data.get("description"), "Описание", max_length=1200),
        used_for=tuple(_clean_text(item, "Назначение", max_length=240) for item in data.get("used_for", ()) if _clean_text(item, "Назначение", max_length=240)),
        pages=tuple(_clean_text(item, "Страницы", max_length=80) for item in data.get("pages", ()) if _clean_text(item, "Страницы", max_length=80)),
        original_local_path=_clean_text(data.get("original_local_path"), "Исходный локальный путь", max_length=700),
        sha256=_clean_text(data.get("sha256"), "SHA256", max_length=80),
        size_bytes=max(0, int(data.get("size_bytes") or 0)),
        compressed=bool(data.get("compressed", True)),
        created_at=_clean_text(data.get("created_at") or _utc_now(), "Дата", max_length=80),
        metadata=data.get("metadata", {}) if isinstance(data.get("metadata", {}), Mapping) else {},
    )


def list_reference_sources(root: Path | str, project_id: str) -> tuple[ReferenceSource, ...]:
    raw = _json_read(_registry_path(root, project_id), [])
    if not isinstance(raw, list):
        return ()
    sources: list[ReferenceSource] = []
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        try:
            sources.append(normalize_reference_source(item))
        except (TypeError, ValueError):
            continue
    return tuple(sources)


def save_reference_registry(root: Path | str, project_id: str, sources: Sequence[ReferenceSource | Mapping[str, Any]]) -> tuple[ReferenceSource, ...]:
    normalized = tuple(normalize_reference_source(item) for item in sources)
    seen: set[str] = set()
    unique: list[ReferenceSource] = []
    for source in normalized:
        if source.id in seen:
            continue
        seen.add(source.id)
        unique.append(source)
    _json_write(_registry_path(root, project_id), [reference_source_to_dict(item) for item in unique])
    return tuple(unique)


def add_pdf_reference_source(
    root: Path | str,
    project_id: str,
    source_pdf_path: Path | str,
    *,
    title: str = "",
    authors: Sequence[str] = (),
    year: str = "",
    description: str = "",
    used_for: Sequence[str] = (),
    pages: Sequence[str] = (),
    source_id: str = "",
    compress: bool = True,
) -> ReferenceSource:
    source_path = Path(source_pdf_path)
    if not source_path.exists() or not source_path.is_file():
        raise FileNotFoundError(f"PDF-источник не найден: {source_path}")
    if source_path.suffix.lower() not in SUPPORTED_SOURCE_EXTENSIONS:
        raise ValueError("Пока поддерживаются только PDF-источники.")

    clean_title = _clean_text(title or source_path.stem, "Название источника", max_length=300, required=True)
    clean_id = _safe_slug(source_id or clean_title)
    target_name = f"{clean_id}.pdf"
    target_path = _sources_dir(root, project_id) / target_name

    if compress:
        _compress_pdf(source_path, target_path)
    else:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)

    source = ReferenceSource(
        id=clean_id,
        title=clean_title,
        relative_path=_relative_to_project(root, project_id, target_path),
        original_file_name=source_path.name,
        source_type="pdf",
        authors=tuple(_clean_text(item, "Автор", max_length=160) for item in authors if _clean_text(item, "Автор", max_length=160)),
        year=_clean_text(year, "Год", max_length=20),
        description=_clean_text(description, "Описание", max_length=1200),
        used_for=tuple(_clean_text(item, "Назначение", max_length=240) for item in used_for if _clean_text(item, "Назначение", max_length=240)),
        pages=tuple(_clean_text(item, "Страницы", max_length=80) for item in pages if _clean_text(item, "Страницы", max_length=80)),
        original_local_path=str(source_path),
        sha256=_hash_file(target_path),
        size_bytes=target_path.stat().st_size,
        compressed=compress,
        created_at=_utc_now(),
    )

    existing = [item for item in list_reference_sources(root, project_id) if item.id != source.id]
    save_reference_registry(root, project_id, [source, *existing])
    append_project_history(
        root,
        project_id,
        "reference_source_added",
        f"Добавлен PDF-источник: {source.title}",
        object_type="reference_source",
        object_id=source.id,
    )
    return source


def validate_reference_sources(root: Path | str, project_id: str) -> tuple[ReferenceValidationIssue, ...]:
    issues: list[ReferenceValidationIssue] = []
    project_dir = _project_dir(root, project_id)
    for source in list_reference_sources(root, project_id):
        source_path = project_dir / source.relative_path
        if not source_path.exists():
            issues.append(
                ReferenceValidationIssue(
                    severity="error",
                    code="missing_file",
                    message=f"Файл источника отсутствует: {source.relative_path}",
                    source_id=source.id,
                    recommendation="Добавьте PDF в папку sources или обновите запись реестра.",
                )
            )
        if LOCAL_WINDOWS_PATH_PATTERN.match(source.relative_path) or LOCAL_WINDOWS_PATH_PATTERN.match(source.original_local_path):
            issues.append(
                ReferenceValidationIssue(
                    severity="warning",
                    code="local_windows_path",
                    message="В источнике найден локальный Windows-путь. В документации нужны относительные пути внутри проекта.",
                    source_id=source.id,
                    recommendation="Используйте путь вида sources/example.pdf.",
                )
            )
        if source.sha256 and source_path.exists() and _hash_file(source_path) != source.sha256:
            issues.append(
                ReferenceValidationIssue(
                    severity="warning",
                    code="hash_mismatch",
                    message=f"Контрольная сумма источника изменилась: {source.relative_path}",
                    source_id=source.id,
                    recommendation="Проверьте, был ли PDF заменен намеренно, затем обновите реестр.",
                )
            )
    return tuple(issues)


def summarize_reference_sources(root: Path | str, project_id: str) -> ReferenceSourcesSummary:
    sources = list_reference_sources(root, project_id)
    issues = validate_reference_sources(root, project_id)
    return ReferenceSourcesSummary(
        total=len(sources),
        pdf=sum(1 for item in sources if item.source_type == "pdf"),
        missing_files=sum(1 for item in issues if item.code == "missing_file"),
        local_path_references=sum(1 for item in issues if item.code == "local_windows_path"),
        size_bytes=sum(item.size_bytes for item in sources),
    )


def build_reference_source_table(root: Path | str, project_id: str) -> list[dict[str, Any]]:
    return [
        {
            "ID": source.id,
            "Название": source.title,
            "Авторы": ", ".join(source.authors),
            "Год": source.year,
            "Файл": source.relative_path,
            "Размер, КБ": round(source.size_bytes / 1024, 2),
            "Назначение": "; ".join(source.used_for),
        }
        for source in list_reference_sources(root, project_id)
    ]


def build_reference_validation_table(root: Path | str, project_id: str) -> list[dict[str, str]]:
    return [
        {
            "Уровень": issue.severity,
            "Код": issue.code,
            "Источник": issue.source_id,
            "Сообщение": issue.message,
            "Рекомендация": issue.recommendation,
        }
        for issue in validate_reference_sources(root, project_id)
    ]


def build_sources_markdown(root: Path | str, project_id: str) -> str:
    lines = ["# Реестр источников проекта", ""]
    for source in list_reference_sources(root, project_id):
        lines.append(f"## {source.title}")
        if source.authors:
            lines.append(f"- Авторы: {', '.join(source.authors)}")
        if source.year:
            lines.append(f"- Год: {source.year}")
        lines.append(f"- Файл: `{source.relative_path}`")
        if source.used_for:
            lines.append(f"- Используется для: {'; '.join(source.used_for)}")
        if source.description:
            lines.append(f"- Описание: {source.description}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
