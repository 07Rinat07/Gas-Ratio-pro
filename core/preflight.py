from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path

from ai.health import HttpGet, check_ai_runtime_status
from ai.model_profiles import load_ai_model_profile_catalog
from ai.settings import load_ai_settings
from palettes.config import load_palette_config


MIN_PYTHON_VERSION = (3, 11)
RUNTIME_MODULES: tuple[str, ...] = ("pandas", "numpy", "streamlit", "plotly", "openpyxl")
REQUIRED_PROJECT_FILES: tuple[str, ...] = (
    "app/streamlit_app.py",
    "config/ai.json",
    "config/ai_model_profiles.json",
    "config/palettes.json",
    "docs/local_model_profiles.md",
    "docs/formulas.md",
    "docs/user_guide.md",
    "examples/sample_gas_data.csv",
    "requirements.txt",
    "scripts/ai_models.py",
)


@dataclass(frozen=True)
class PreflightCheck:
    name: str
    status: str
    message: str


@dataclass(frozen=True)
class PreflightReport:
    checks: tuple[PreflightCheck, ...]

    @property
    def ok(self) -> bool:
        return all(check.status != "error" for check in self.checks)

    def as_dict(self) -> dict:
        return {
            "ok": self.ok,
            "checks": [
                {
                    "name": check.name,
                    "status": check.status,
                    "message": check.message,
                }
                for check in self.checks
            ],
        }


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _check_python_version() -> PreflightCheck:
    current = sys.version_info[:3]
    if current >= MIN_PYTHON_VERSION:
        return PreflightCheck(
            name="python",
            status="ok",
            message=f"Python {current[0]}.{current[1]}.{current[2]} подходит.",
        )

    return PreflightCheck(
        name="python",
        status="error",
        message=(
            f"Нужен Python {MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]}+, "
            f"текущая версия: {current[0]}.{current[1]}.{current[2]}."
        ),
    )


def _check_runtime_modules() -> PreflightCheck:
    missing = [module for module in RUNTIME_MODULES if importlib.util.find_spec(module) is None]
    if not missing:
        return PreflightCheck(
            name="dependencies",
            status="ok",
            message="Runtime-зависимости установлены.",
        )

    return PreflightCheck(
        name="dependencies",
        status="error",
        message="Не установлены зависимости: " + ", ".join(missing) + ". Выполните `pip install -r requirements.txt`.",
    )


def _check_required_files(root: Path) -> PreflightCheck:
    missing = [relative for relative in REQUIRED_PROJECT_FILES if not (root / relative).exists()]
    if not missing:
        return PreflightCheck(
            name="project_files",
            status="ok",
            message="Ключевые файлы проекта найдены.",
        )

    return PreflightCheck(
        name="project_files",
        status="error",
        message="Не найдены файлы: " + ", ".join(missing) + ".",
    )


def _check_palette_config(root: Path) -> PreflightCheck:
    try:
        config = load_palette_config(root / "config" / "palettes.json")
    except Exception as exc:
        return PreflightCheck(
            name="palette_config",
            status="error",
            message=f"Ошибка config/palettes.json: {exc}",
        )

    return PreflightCheck(
        name="palette_config",
        status="ok",
        message=f"Конфиг палеток загружен: {config.version}.",
    )


def _check_ai_model_profiles(root: Path) -> PreflightCheck:
    try:
        catalog = load_ai_model_profile_catalog(root / "config" / "ai_model_profiles.json")
    except Exception as exc:
        return PreflightCheck(
            name="ai_model_profiles",
            status="error",
            message=f"Ошибка config/ai_model_profiles.json: {exc}",
        )

    return PreflightCheck(
        name="ai_model_profiles",
        status="ok",
        message=f"Профили локальных AI-моделей загружены: {len(catalog.profiles)}.",
    )


def _check_ai_config(root: Path, http_get: HttpGet | None) -> PreflightCheck:
    try:
        settings = load_ai_settings(root / "config" / "ai.json")
    except Exception as exc:
        return PreflightCheck(
            name="ai_config",
            status="error",
            message=f"Ошибка config/ai.json: {exc}",
        )

    runtime_status = (
        check_ai_runtime_status(settings)
        if http_get is None
        else check_ai_runtime_status(settings, http_get=http_get)
    )
    return PreflightCheck(
        name="ai_runtime",
        status="ok" if runtime_status.ready else "error",
        message=runtime_status.message,
    )


def _check_logs_dir(root: Path) -> PreflightCheck:
    log_dir = root / "logs"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        probe = log_dir / ".preflight_write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except Exception as exc:
        return PreflightCheck(
            name="logs",
            status="error",
            message=f"Папка logs недоступна для записи: {exc}",
        )

    return PreflightCheck(
        name="logs",
        status="ok",
        message="Папка logs доступна для записи.",
    )


def run_preflight(
    root: str | Path | None = None,
    http_get: HttpGet | None = None,
) -> PreflightReport:
    resolved_root = Path(root) if root is not None else project_root()
    checks = (
        _check_python_version(),
        _check_required_files(resolved_root),
        _check_runtime_modules(),
        _check_palette_config(resolved_root),
        _check_ai_model_profiles(resolved_root),
        _check_ai_config(resolved_root, http_get=http_get),
        _check_logs_dir(resolved_root),
    )
    return PreflightReport(checks=checks)
