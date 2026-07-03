from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path

from palettes.config import load_palette_config


MIN_PYTHON_VERSION = (3, 11)
RUNTIME_MODULES: tuple[str, ...] = ("pandas", "numpy", "streamlit", "plotly", "openpyxl")
STATIC_EXPORT_MODULE = "kaleido"
REQUIRED_PROJECT_FILES: tuple[str, ...] = (
    "app/streamlit_app.py",
    "config/palettes.json",
    "docs/project_plan.md",
    "docs/setup.md",
    "docs/user_guide.md",
    "docs/data_format.md",
    "docs/formulas.md",
    "docs/las_editor_plan.md",
    "docs/las_correlation_plan.md",
    "docs/mud_gas_analysis_literature.md",
    "docs/logging.md",
    "docs/palettes.md",
    "docs/troubleshooting.md",
    "examples/sample_gas_data.csv",
    "examples/sample_gas_data.las",
    "requirements.txt",
    "scripts/preflight.py",
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


def _check_static_export_module() -> PreflightCheck:
    if importlib.util.find_spec(STATIC_EXPORT_MODULE) is not None:
        return PreflightCheck(
            name="static_export",
            status="ok",
            message="PNG/PDF/SVG экспорт доступен.",
        )

    return PreflightCheck(
        name="static_export",
        status="warning",
        message=(
            "PNG/PDF/SVG экспорт недоступен без kaleido. "
            "Выполните `pip install -r requirements.txt`, если нужен статический экспорт графиков."
        ),
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


def run_preflight(root: str | Path | None = None) -> PreflightReport:
    resolved_root = Path(root) if root is not None else project_root()
    checks = (
        _check_python_version(),
        _check_required_files(resolved_root),
        _check_runtime_modules(),
        _check_static_export_module(),
        _check_palette_config(resolved_root),
        _check_logs_dir(resolved_root),
    )
    return PreflightReport(checks=checks)
