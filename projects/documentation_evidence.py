from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from projects.reference_sources import _hash_file  # internal helper reused for deterministic source audit

SOURCE_REGISTRY_RELATIVE_PATH = Path("docs/sources/source_registry.json")
SOURCES_DIR_RELATIVE_PATH = Path("docs/sources")
DOCUMENTATION_EXTENSIONS = {".md", ".txt", ".rst"}
LOCAL_WINDOWS_PATH_RE = re.compile(r"[A-Za-z]:\\[^\s)`>\]\"']+")
SOURCE_PDF_REF_RE = re.compile(r"docs/sources/[A-Za-z0-9_./()\- ]+?\.pdf")


@dataclass(frozen=True)
class DocumentationEvidenceSource:
    """Normalized source entry from docs/sources/source_registry.json."""

    id: str
    title: str
    relative_path: str
    sha256: str = ""
    size_bytes: int = 0
    used_for: tuple[str, ...] = ()


@dataclass(frozen=True)
class DocumentationEvidenceReference:
    """A source reference found in a documentation file."""

    document_path: str
    source_path: str
    line_number: int
    line_text: str


@dataclass(frozen=True)
class DocumentationEvidenceIssue:
    """Audit issue used by UI tables and release checks."""

    severity: str
    code: str
    message: str
    document_path: str = ""
    source_path: str = ""
    line_number: int = 0
    recommendation: str = ""


@dataclass(frozen=True)
class DocumentationEvidenceSummary:
    """Compact audit summary for dashboards and preflight reports."""

    registered_sources: int
    existing_sources: int
    missing_sources: int
    source_references: int
    documents_scanned: int
    issues_total: int
    errors: int
    warnings: int
    local_paths: int
    unregistered_references: int
    orphan_sources: int


def _read_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return default


def _clean_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _as_tuple(values: Any) -> tuple[str, ...]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        return ()
    cleaned: list[str] = []
    for value in values:
        text = _clean_text(value)
        if text:
            cleaned.append(text)
    return tuple(cleaned)


def _relative(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _iter_document_files(root: Path) -> Iterable[Path]:
    docs_dir = root / "docs"
    if not docs_dir.exists():
        return ()
    return (
        path
        for path in docs_dir.rglob("*")
        if path.is_file()
        and path.suffix.lower() in DOCUMENTATION_EXTENSIONS
        and not any(part.startswith(".") for part in path.relative_to(root).parts)
    )


def load_documentation_evidence_sources(root: Path | str) -> tuple[DocumentationEvidenceSource, ...]:
    """Load and normalize the project source registry stored under docs/sources."""

    project_root = Path(root)
    raw = _read_json(project_root / SOURCE_REGISTRY_RELATIVE_PATH, [])
    if not isinstance(raw, list):
        return ()

    sources: list[DocumentationEvidenceSource] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        relative_path = _clean_text(item.get("relative_path")).replace("\\", "/")
        source_id = _clean_text(item.get("id")) or Path(relative_path).stem
        if not source_id or source_id in seen:
            continue
        seen.add(source_id)
        sources.append(
            DocumentationEvidenceSource(
                id=source_id,
                title=_clean_text(item.get("title")) or source_id,
                relative_path=relative_path,
                sha256=_clean_text(item.get("sha256")),
                size_bytes=max(0, int(item.get("size_bytes") or 0)),
                used_for=_as_tuple(item.get("used_for", ())),
            )
        )
    return tuple(sources)


def find_documentation_source_references(root: Path | str) -> tuple[DocumentationEvidenceReference, ...]:
    """Find relative PDF source references in text documentation."""

    project_root = Path(root)
    references: list[DocumentationEvidenceReference] = []
    for document in _iter_document_files(project_root):
        try:
            lines = document.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line_number, line in enumerate(lines, start=1):
            for match in SOURCE_PDF_REF_RE.finditer(line):
                references.append(
                    DocumentationEvidenceReference(
                        document_path=_relative(project_root, document),
                        source_path=match.group(0).strip(),
                        line_number=line_number,
                        line_text=line.strip()[:500],
                    )
                )
    return tuple(references)


def find_local_documentation_paths(root: Path | str) -> tuple[DocumentationEvidenceIssue, ...]:
    """Detect local Windows paths that must not appear in committed documentation."""

    project_root = Path(root)
    issues: list[DocumentationEvidenceIssue] = []
    for document in _iter_document_files(project_root):
        try:
            lines = document.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line_number, line in enumerate(lines, start=1):
            for match in LOCAL_WINDOWS_PATH_RE.finditer(line):
                issues.append(
                    DocumentationEvidenceIssue(
                        severity="error",
                        code="local_path_in_documentation",
                        message=f"В документации найден локальный путь: {match.group(0)}",
                        document_path=_relative(project_root, document),
                        line_number=line_number,
                        recommendation="Сохраните источник в docs/sources и замените ссылку на относительный путь.",
                    )
                )
    return tuple(issues)


def validate_documentation_evidence(root: Path | str) -> tuple[DocumentationEvidenceIssue, ...]:
    """Validate source files, registry consistency and documentation references."""

    project_root = Path(root)
    sources = load_documentation_evidence_sources(project_root)
    registered_paths = {source.relative_path for source in sources if source.relative_path}
    references = find_documentation_source_references(project_root)
    issues: list[DocumentationEvidenceIssue] = list(find_local_documentation_paths(project_root))

    registry_path = project_root / SOURCE_REGISTRY_RELATIVE_PATH
    if not registry_path.exists():
        issues.append(
            DocumentationEvidenceIssue(
                severity="error",
                code="source_registry_missing",
                message="Реестр источников docs/sources/source_registry.json отсутствует.",
                recommendation="Создайте source_registry.json и зарегистрируйте PDF-источники проекта.",
            )
        )

    for source in sources:
        source_path = project_root / source.relative_path
        if not source.relative_path.startswith("docs/sources/"):
            issues.append(
                DocumentationEvidenceIssue(
                    severity="warning",
                    code="source_outside_sources_dir",
                    message="Источник зарегистрирован вне docs/sources.",
                    source_path=source.relative_path,
                    recommendation="Храните доказательные PDF в docs/sources.",
                )
            )
        if not source_path.exists():
            issues.append(
                DocumentationEvidenceIssue(
                    severity="error",
                    code="registered_source_missing",
                    message=f"Зарегистрированный источник отсутствует: {source.relative_path}",
                    source_path=source.relative_path,
                    recommendation="Добавьте PDF в проект или удалите запись из реестра.",
                )
            )
            continue
        if source.sha256 and _hash_file(source_path) != source.sha256:
            issues.append(
                DocumentationEvidenceIssue(
                    severity="warning",
                    code="registered_source_hash_mismatch",
                    message=f"Контрольная сумма PDF изменилась: {source.relative_path}",
                    source_path=source.relative_path,
                    recommendation="Проверьте замену файла и обновите source_registry.json.",
                )
            )

    for reference in references:
        if reference.source_path not in registered_paths:
            issues.append(
                DocumentationEvidenceIssue(
                    severity="warning",
                    code="unregistered_source_reference",
                    message=f"Документация ссылается на PDF, которого нет в реестре: {reference.source_path}",
                    document_path=reference.document_path,
                    source_path=reference.source_path,
                    line_number=reference.line_number,
                    recommendation="Добавьте PDF в source_registry.json или исправьте ссылку.",
                )
            )
        if not (project_root / reference.source_path).exists():
            issues.append(
                DocumentationEvidenceIssue(
                    severity="error",
                    code="referenced_source_missing",
                    message=f"Документация ссылается на отсутствующий PDF: {reference.source_path}",
                    document_path=reference.document_path,
                    source_path=reference.source_path,
                    line_number=reference.line_number,
                    recommendation="Добавьте файл в docs/sources или исправьте ссылку.",
                )
            )

    source_dir = project_root / SOURCES_DIR_RELATIVE_PATH
    if source_dir.exists():
        for pdf_path in sorted(source_dir.glob("*.pdf")):
            relative_pdf = _relative(project_root, pdf_path)
            if relative_pdf not in registered_paths:
                issues.append(
                    DocumentationEvidenceIssue(
                        severity="warning",
                        code="orphan_source_file",
                        message=f"PDF лежит в docs/sources, но не зарегистрирован: {relative_pdf}",
                        source_path=relative_pdf,
                        recommendation="Добавьте файл в source_registry.json или удалите лишний PDF.",
                    )
                )

    return tuple(issues)


def summarize_documentation_evidence(root: Path | str) -> DocumentationEvidenceSummary:
    project_root = Path(root)
    sources = load_documentation_evidence_sources(project_root)
    references = find_documentation_source_references(project_root)
    issues = validate_documentation_evidence(project_root)
    source_dir = project_root / SOURCES_DIR_RELATIVE_PATH
    pdf_files = tuple(source_dir.glob("*.pdf")) if source_dir.exists() else ()
    registered_paths = {source.relative_path for source in sources}

    return DocumentationEvidenceSummary(
        registered_sources=len(sources),
        existing_sources=sum(1 for source in sources if (project_root / source.relative_path).exists()),
        missing_sources=sum(1 for issue in issues if issue.code in {"registered_source_missing", "referenced_source_missing"}),
        source_references=len(references),
        documents_scanned=sum(1 for _ in _iter_document_files(project_root)),
        issues_total=len(issues),
        errors=sum(1 for issue in issues if issue.severity == "error"),
        warnings=sum(1 for issue in issues if issue.severity == "warning"),
        local_paths=sum(1 for issue in issues if issue.code == "local_path_in_documentation"),
        unregistered_references=sum(1 for issue in issues if issue.code == "unregistered_source_reference"),
        orphan_sources=sum(1 for pdf in pdf_files if _relative(project_root, pdf) not in registered_paths),
    )


def build_documentation_evidence_source_table(root: Path | str) -> list[dict[str, Any]]:
    project_root = Path(root)
    return [
        {
            "ID": source.id,
            "Название": source.title,
            "Файл": source.relative_path,
            "Есть файл": (project_root / source.relative_path).exists(),
            "Размер, КБ": round(((project_root / source.relative_path).stat().st_size if (project_root / source.relative_path).exists() else source.size_bytes) / 1024, 2),
            "Используется для": "; ".join(source.used_for),
        }
        for source in load_documentation_evidence_sources(project_root)
    ]


def build_documentation_evidence_reference_table(root: Path | str) -> list[dict[str, Any]]:
    return [
        {
            "Документ": ref.document_path,
            "Строка": ref.line_number,
            "Источник": ref.source_path,
            "Фрагмент": ref.line_text,
        }
        for ref in find_documentation_source_references(root)
    ]


def build_documentation_evidence_issue_table(root: Path | str) -> list[dict[str, Any]]:
    return [
        {
            "Уровень": issue.severity,
            "Код": issue.code,
            "Документ": issue.document_path,
            "Строка": issue.line_number or "",
            "Источник": issue.source_path,
            "Сообщение": issue.message,
            "Рекомендация": issue.recommendation,
        }
        for issue in validate_documentation_evidence(root)
    ]


def build_documentation_evidence_manifest(root: Path | str) -> dict[str, Any]:
    summary = summarize_documentation_evidence(root)
    return {
        "summary": {
            "registered_sources": summary.registered_sources,
            "existing_sources": summary.existing_sources,
            "missing_sources": summary.missing_sources,
            "source_references": summary.source_references,
            "documents_scanned": summary.documents_scanned,
            "issues_total": summary.issues_total,
            "errors": summary.errors,
            "warnings": summary.warnings,
            "local_paths": summary.local_paths,
            "unregistered_references": summary.unregistered_references,
            "orphan_sources": summary.orphan_sources,
        },
        "sources": build_documentation_evidence_source_table(root),
        "references": build_documentation_evidence_reference_table(root),
        "issues": build_documentation_evidence_issue_table(root),
    }


def build_documentation_evidence_markdown(root: Path | str) -> str:
    summary = summarize_documentation_evidence(root)
    lines = [
        "# Documentation Evidence Audit",
        "",
        "## Summary",
        "",
        f"- Registered sources: {summary.registered_sources}",
        f"- Existing sources: {summary.existing_sources}",
        f"- Source references in docs: {summary.source_references}",
        f"- Documents scanned: {summary.documents_scanned}",
        f"- Issues: {summary.issues_total} (errors: {summary.errors}, warnings: {summary.warnings})",
        "",
        "## Issues",
        "",
    ]
    issues = validate_documentation_evidence(root)
    if not issues:
        lines.append("No documentation evidence issues found.")
    else:
        for issue in issues:
            location = issue.document_path
            if issue.line_number:
                location += f":{issue.line_number}"
            lines.append(f"- **{issue.severity} / {issue.code}** — {issue.message}")
            if location:
                lines.append(f"  - Location: `{location}`")
            if issue.source_path:
                lines.append(f"  - Source: `{issue.source_path}`")
            if issue.recommendation:
                lines.append(f"  - Recommendation: {issue.recommendation}")
    lines.append("")
    return "\n".join(lines)
