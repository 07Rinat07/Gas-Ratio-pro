from __future__ import annotations

import hashlib
import json
import py_compile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from projects.project_manager import append_project_history
from projects.repository import safe_project_id

PROJECT_RELEASE_FILE_NAME = "release_candidate.json"
RELEASE_SCHEMA = "gas-ratio-pro.release-candidate.v1"
RELEASE_STATUSES = {"ok", "warning", "error", "skipped"}
RELEASE_GATES = {"source", "documentation", "tests", "configuration", "artifacts", "performance", "security", "release"}
DEFAULT_REQUIRED_FILES: tuple[str, ...] = (
    "README.md",
    "CHANGELOG.md",
    "requirements.txt",
    "app/streamlit_app.py",
    "docs/PROJECT_ROADMAP.md",
    "docs/PROJECT_STATUS.md",
    "docs/ARCHITECTURE.md",
    "docs/DOCUMENTATION_INDEX.md",
    "docs/setup.md",
    "docs/user_guide.md",
    "docs/troubleshooting.md",
)
DEFAULT_COMPILE_DIRS: tuple[str, ...] = (
    "app",
    "core",
    "projects",
    "importers",
    "exports",
    "las_editor",
    "las_correlation",
    "mapping",
    "palettes",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _project_dir(root: Path | str, project_id: str) -> Path:
    return Path(root) / safe_project_id(project_id)


def _release_path(root: Path | str, project_id: str) -> Path:
    return _project_dir(root, project_id) / PROJECT_RELEASE_FILE_NAME


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


def _clean_text(value: Any, field_label: str, *, max_length: int = 240, required: bool = False) -> str:
    text = "" if value is None else str(value).strip()
    if required and not text:
        raise ValueError(f"{field_label}: значение обязательно.")
    if len(text) > max_length:
        raise ValueError(f"{field_label}: максимум {max_length} символов.")
    return text


def _normalize_status(value: Any) -> str:
    text = _clean_text(value or "ok", "Статус", max_length=40).lower()
    if text not in RELEASE_STATUSES:
        raise ValueError(f"Статус должен быть одним из: {', '.join(sorted(RELEASE_STATUSES))}.")
    return text


def _normalize_gate(value: Any) -> str:
    text = _clean_text(value or "release", "Gate", max_length=80).lower()
    if text not in RELEASE_GATES:
        raise ValueError(f"Gate должен быть одним из: {', '.join(sorted(RELEASE_GATES))}.")
    return text


def _safe_id(prefix: str, parts: Sequence[Any]) -> str:
    source = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


@dataclass(frozen=True)
class ReleaseCheck:
    """One release-candidate quality gate check."""

    id: str
    name: str
    gate: str
    status: str
    message: str
    required: bool = True
    component: str = "core"
    created_at: str = ""
    details: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ReleaseSummary:
    checks: int
    ok: int
    warnings: int
    errors: int
    skipped: int
    required_errors: int
    release_ready: bool


def normalize_release_check(raw: ReleaseCheck | Mapping[str, Any]) -> ReleaseCheck:
    if isinstance(raw, ReleaseCheck):
        check = raw
    elif isinstance(raw, Mapping):
        name = _clean_text(raw.get("name"), "Название проверки", required=True)
        gate = _normalize_gate(raw.get("gate") or "release")
        status = _normalize_status(raw.get("status") or "ok")
        check = ReleaseCheck(
            id=_clean_text(raw.get("id"), "ID проверки", max_length=120) or _safe_id("rc-check", (name, gate, status)),
            name=name,
            gate=gate,
            status=status,
            message=_clean_text(raw.get("message") or status, "Сообщение", max_length=600),
            required=bool(raw.get("required", True)),
            component=_clean_text(raw.get("component") or "core", "Компонент", max_length=120),
            created_at=_clean_text(raw.get("created_at") or _utc_now(), "Дата", max_length=80),
            details=raw.get("details", {}) if isinstance(raw.get("details", {}), Mapping) else {},
        )
    else:
        raise TypeError("Release check должен быть ReleaseCheck или mapping.")

    return ReleaseCheck(
        id=_clean_text(check.id, "ID проверки", max_length=120, required=True),
        name=_clean_text(check.name, "Название проверки", required=True),
        gate=_normalize_gate(check.gate),
        status=_normalize_status(check.status),
        message=_clean_text(check.message, "Сообщение", max_length=600),
        required=bool(check.required),
        component=_clean_text(check.component or "core", "Компонент", max_length=120),
        created_at=_clean_text(check.created_at or _utc_now(), "Дата", max_length=80),
        details=check.details if isinstance(check.details, Mapping) else {},
    )


def release_check_to_dict(check: ReleaseCheck) -> dict[str, Any]:
    normalized = normalize_release_check(check)
    return {
        "id": normalized.id,
        "name": normalized.name,
        "gate": normalized.gate,
        "status": normalized.status,
        "message": normalized.message,
        "required": normalized.required,
        "component": normalized.component,
        "created_at": normalized.created_at,
        "details": dict(normalized.details),
    }


def summarize_release_checks(checks: Iterable[ReleaseCheck | Mapping[str, Any]]) -> ReleaseSummary:
    normalized = [normalize_release_check(check) for check in checks]
    errors = sum(1 for check in normalized if check.status == "error")
    required_errors = sum(1 for check in normalized if check.status == "error" and check.required)
    return ReleaseSummary(
        checks=len(normalized),
        ok=sum(1 for check in normalized if check.status == "ok"),
        warnings=sum(1 for check in normalized if check.status == "warning"),
        errors=errors,
        skipped=sum(1 for check in normalized if check.status == "skipped"),
        required_errors=required_errors,
        release_ready=required_errors == 0,
    )


def _file_check(root: Path, relative: str, *, required: bool = True) -> ReleaseCheck:
    path = root / relative
    if path.exists():
        return normalize_release_check({
            "name": f"Required file: {relative}",
            "gate": "source" if relative.endswith(".py") else "documentation",
            "status": "ok",
            "message": "Файл найден.",
            "required": required,
            "component": relative.split("/", 1)[0],
            "details": {"path": relative, "size_bytes": path.stat().st_size},
        })
    return normalize_release_check({
        "name": f"Required file: {relative}",
        "gate": "source" if relative.endswith(".py") else "documentation",
        "status": "error" if required else "warning",
        "message": "Файл отсутствует.",
        "required": required,
        "component": relative.split("/", 1)[0],
        "details": {"path": relative},
    })


def check_required_files(root: Path | str, required_files: Sequence[str] = DEFAULT_REQUIRED_FILES) -> tuple[ReleaseCheck, ...]:
    resolved = Path(root)
    return tuple(_file_check(resolved, relative) for relative in required_files)


def check_python_compile(root: Path | str, compile_dirs: Sequence[str] = DEFAULT_COMPILE_DIRS) -> ReleaseCheck:
    resolved = Path(root)
    python_files: list[Path] = []
    for relative_dir in compile_dirs:
        directory = resolved / relative_dir
        if directory.exists():
            python_files.extend(path for path in directory.rglob("*.py") if "__pycache__" not in path.parts)

    errors: list[str] = []
    for path in sorted(python_files):
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as exc:
            errors.append(f"{path.relative_to(resolved)}: {exc.msg}")

    if errors:
        return normalize_release_check({
            "name": "Python source compile",
            "gate": "source",
            "status": "error",
            "message": f"Найдены ошибки компиляции: {len(errors)}.",
            "component": "source",
            "details": {"files_checked": len(python_files), "errors": errors[:20]},
        })
    return normalize_release_check({
        "name": "Python source compile",
        "gate": "source",
        "status": "ok",
        "message": f"Python-файлы компилируются без ошибок: {len(python_files)}.",
        "component": "source",
        "details": {"files_checked": len(python_files)},
    })


def check_test_inventory(root: Path | str) -> ReleaseCheck:
    resolved = Path(root)
    tests_dir = resolved / "tests"
    test_files = sorted(tests_dir.glob("test_*.py")) if tests_dir.exists() else []
    if not tests_dir.exists():
        return normalize_release_check({
            "name": "Test inventory",
            "gate": "tests",
            "status": "error",
            "message": "Папка tests отсутствует.",
            "component": "tests",
        })
    status = "ok" if test_files else "warning"
    return normalize_release_check({
        "name": "Test inventory",
        "gate": "tests",
        "status": status,
        "message": f"Найдено pytest-файлов: {len(test_files)}.",
        "required": True,
        "component": "tests",
        "details": {"test_files": [path.name for path in test_files[:50]], "total": len(test_files)},
    })


def check_release_notes(root: Path | str, *, min_changelog_bytes: int = 200) -> ReleaseCheck:
    changelog = Path(root) / "CHANGELOG.md"
    if not changelog.exists():
        return normalize_release_check({"name": "Release notes", "gate": "documentation", "status": "error", "message": "CHANGELOG.md отсутствует.", "component": "docs"})
    size = changelog.stat().st_size
    status = "ok" if size >= min_changelog_bytes else "warning"
    return normalize_release_check({
        "name": "Release notes",
        "gate": "documentation",
        "status": status,
        "message": f"CHANGELOG.md подготовлен, размер {size} байт.",
        "component": "docs",
        "details": {"size_bytes": size, "min_size_bytes": min_changelog_bytes},
    })


def build_release_file_inventory(root: Path | str, *, max_files: int = 5000) -> dict[str, Any]:
    resolved = Path(root)
    files = [path for path in resolved.rglob("*") if path.is_file() and "__pycache__" not in path.parts]
    files = sorted(files)[:max_files]
    total_size = sum(path.stat().st_size for path in files)
    fingerprint_source = "\n".join(f"{path.relative_to(resolved).as_posix()}:{path.stat().st_size}" for path in files)
    return {
        "files": len(files),
        "total_size_bytes": total_size,
        "fingerprint": hashlib.sha256(fingerprint_source.encode("utf-8")).hexdigest(),
        "sample": [path.relative_to(resolved).as_posix() for path in files[:50]],
        "truncated": len(files) >= max_files,
    }


def run_release_candidate_audit(root: Path | str, *, required_files: Sequence[str] = DEFAULT_REQUIRED_FILES) -> tuple[ReleaseCheck, ...]:
    resolved = Path(root)
    checks: list[ReleaseCheck] = []
    checks.extend(check_required_files(resolved, required_files))
    checks.append(check_release_notes(resolved))
    checks.append(check_test_inventory(resolved))
    checks.append(check_python_compile(resolved))
    return tuple(checks)


def build_release_manifest(
    root: Path | str,
    *,
    version: str = "RC-1",
    checks: Iterable[ReleaseCheck | Mapping[str, Any]] | None = None,
    include_file_inventory: bool = True,
) -> dict[str, Any]:
    normalized_checks = [normalize_release_check(check) for check in (checks if checks is not None else run_release_candidate_audit(root))]
    summary = summarize_release_checks(normalized_checks)
    manifest = {
        "schema": RELEASE_SCHEMA,
        "version": _clean_text(version or "RC-1", "Версия", max_length=80),
        "generated_at": _utc_now(),
        "status": "release-ready" if summary.release_ready else "blocked",
        "summary": {
            "checks": summary.checks,
            "ok": summary.ok,
            "warnings": summary.warnings,
            "errors": summary.errors,
            "skipped": summary.skipped,
            "required_errors": summary.required_errors,
            "release_ready": summary.release_ready,
        },
        "checks": [release_check_to_dict(check) for check in normalized_checks],
        "checklist": build_release_checklist(),
    }
    if include_file_inventory:
        manifest["file_inventory"] = build_release_file_inventory(root)
    return manifest


def validate_release_manifest(manifest: Mapping[str, Any]) -> tuple[ReleaseCheck, ...]:
    checks: list[ReleaseCheck] = []
    schema = manifest.get("schema")
    checks.append(normalize_release_check({
        "name": "Manifest schema",
        "gate": "release",
        "status": "ok" if schema == RELEASE_SCHEMA else "error",
        "message": "Release manifest schema корректна." if schema == RELEASE_SCHEMA else "Некорректная schema release manifest.",
        "component": "release",
    }))
    raw_checks = manifest.get("checks", [])
    checks.append(normalize_release_check({
        "name": "Manifest checks",
        "gate": "release",
        "status": "ok" if isinstance(raw_checks, list) and raw_checks else "error",
        "message": f"В manifest записано проверок: {len(raw_checks) if isinstance(raw_checks, list) else 0}.",
        "component": "release",
    }))
    status = manifest.get("status")
    checks.append(normalize_release_check({
        "name": "Manifest status",
        "gate": "release",
        "status": "ok" if status in {"release-ready", "blocked"} else "error",
        "message": f"Статус manifest: {status}.",
        "component": "release",
    }))
    return tuple(checks)


def save_release_manifest(root: Path | str, project_id: str, manifest: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(manifest)
    payload.setdefault("schema", RELEASE_SCHEMA)
    payload.setdefault("generated_at", _utc_now())
    _json_write(_release_path(root, project_id), payload)
    append_project_history(
        root,
        project_id,
        "release_candidate_manifest_saved",
        f"Release Candidate manifest saved: {payload.get('status', 'unknown')}.",
        object_type="release_candidate",
        object_id=str(payload.get("version", "RC")),
    )
    return payload


def load_release_manifest(root: Path | str, project_id: str) -> dict[str, Any]:
    payload = _json_read(_release_path(root, project_id), {})
    return payload if isinstance(payload, dict) else {}


def build_release_checklist() -> list[dict[str, Any]]:
    return [
        {"gate": "source", "title": "Все Python-модули компилируются", "required": True},
        {"gate": "tests", "title": "Профильные pytest-наборы проходят", "required": True},
        {"gate": "documentation", "title": "README, CHANGELOG и Project Plan синхронизированы", "required": True},
        {"gate": "artifacts", "title": "Проверены LAS/PDF/PNG/SVG export adapters", "required": True},
        {"gate": "performance", "title": "Нет критических performance-регрессий", "required": True},
        {"gate": "security", "title": "Лицензирование не включено до финального этапа", "required": True},
        {"gate": "release", "title": "Release manifest сохранен и приложен к сборке", "required": True},
    ]


def build_release_check_table(checks: Iterable[ReleaseCheck | Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for check in checks:
        normalized = normalize_release_check(check)
        rows.append({
            "Gate": normalized.gate,
            "Проверка": normalized.name,
            "Статус": normalized.status,
            "Обязательно": "да" if normalized.required else "нет",
            "Компонент": normalized.component,
            "Сообщение": normalized.message,
        })
    return rows
