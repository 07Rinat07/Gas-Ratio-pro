from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

import pandas as pd

from las_editor.las_creator import (
    DEFAULT_NULL_VALUE,
    LasCreationSpec,
    LasCurveSpec,
    build_las_creation_spec,
    build_las_text,
    create_las_dataframe,
    get_las_template_curves,
    normalize_las_mnemonic,
    normalize_las_unit,
)
from las_editor.las_validator import LasValidationFinding, validate_las_ascii

LAS_SAFE_EXPORT_STORAGE_KEY = "las_safe_export"
LAS_TEMPLATE_STORAGE_KEY = "las_templates"
LAS_EXPORT_SCHEMA = "gas-ratio-pro.las-safe-export.v1"


@dataclass(frozen=True)
class LasTemplateProfile:
    """Reusable LAS creation/export template.

    The object is intentionally backend-only. Streamlit can render it as a
    table, but the model itself contains only stable data needed to create a
    valid LAS document: template identity, default metadata and curve specs.
    """

    name: str
    title: str
    description: str = ""
    curves: tuple[LasCurveSpec, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LasExportIssue:
    severity: str
    code: str
    message: str
    path: str = ""
    recommendation: str = ""


@dataclass(frozen=True)
class LasSafeExportManifest:
    """Renderer-independent manifest for safe LAS export."""

    schema: str
    status: str
    created_at: str
    target_path: str
    source_path: str = ""
    bytes_count: int = 0
    line_count: int = 0
    curve_count: int = 0
    row_count: int = 0
    overwrite_allowed: bool = False
    issues: tuple[LasExportIssue, ...] = ()
    validation_summary: dict[str, Any] = field(default_factory=dict)

    @property
    def is_ready(self) -> bool:
        return self.status == "ready" and not any(issue.severity == "error" for issue in self.issues)


_BUILTIN_TEMPLATE_PROFILES: dict[str, LasTemplateProfile] = {
    "empty": LasTemplateProfile(
        name="empty",
        title="Пустой LAS",
        description="Минимальный LAS-файл с глубиной без дополнительных кривых.",
        curves=get_las_template_curves("empty"),
    ),
    "mud_gas": LasTemplateProfile(
        name="mud_gas",
        title="Газовый каротаж",
        description="Шаблон для C1-C5 и суммарного газа.",
        curves=get_las_template_curves("mud_gas"),
        metadata={"service_company": "GAS RATIO PRO", "field": "Mud Gas Logging"},
    ),
    "petrophysics": LasTemplateProfile(
        name="petrophysics",
        title="Петрофизика",
        description="Базовый шаблон ГИС: GR, RHOB, NPHI, DT, RT, POR, SW.",
        curves=get_las_template_curves("petrophysics"),
        metadata={"service_company": "GAS RATIO PRO", "field": "Petrophysical Interpretation"},
    ),
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def builtin_las_template_profiles() -> tuple[LasTemplateProfile, ...]:
    """Return built-in professional LAS templates."""

    return tuple(_BUILTIN_TEMPLATE_PROFILES.values())


def get_las_template_profile(name: str) -> LasTemplateProfile:
    key = str(name or "empty").strip().lower()
    if key not in _BUILTIN_TEMPLATE_PROFILES:
        raise ValueError(f"Unknown LAS template profile: {name!r}")
    return _BUILTIN_TEMPLATE_PROFILES[key]


def create_las_spec_from_template(
    template_name: str,
    *,
    well_name: str,
    start_depth: float,
    stop_depth: float,
    step: float,
    curves: Iterable[LasCurveSpec | Mapping[str, Any] | str] = (),
    **metadata: Any,
) -> LasCreationSpec:
    """Create a LAS creation spec from a named profile plus optional overrides."""

    profile = get_las_template_profile(template_name)
    merged_metadata = dict(profile.metadata)
    merged_metadata.update(metadata)
    return build_las_creation_spec(
        well_name=well_name,
        start_depth=start_depth,
        stop_depth=stop_depth,
        step=step,
        template_name=profile.name,
        curves=curves,
        **merged_metadata,
    )


def las_template_table_rows(profiles: Iterable[LasTemplateProfile] | None = None) -> list[dict[str, Any]]:
    """Return UI-ready rows for template selection tables."""

    selected = tuple(profiles) if profiles is not None else builtin_las_template_profiles()
    rows: list[dict[str, Any]] = []
    for profile in selected:
        rows.append(
            {
                "name": profile.name,
                "title": profile.title,
                "description": profile.description,
                "curve_count": len(profile.curves),
                "curves": ", ".join(curve.mnemonic for curve in profile.curves),
            }
        )
    return rows


def _normalize_path(path: str | Path) -> Path:
    raw = str(path or "").strip()
    if not raw:
        raise ValueError("Export path is required.")
    result = Path(raw).expanduser()
    if result.suffix.lower() != ".las":
        result = result.with_suffix(".las")
    return result


def _same_file_path(first: Path, second: Path) -> bool:
    try:
        return first.resolve() == second.resolve()
    except OSError:
        return first.absolute() == second.absolute()


def validate_safe_export_request(
    target_path: str | Path,
    *,
    source_path: str | Path | None = None,
    allow_overwrite: bool = False,
) -> tuple[Path, tuple[LasExportIssue, ...]]:
    """Validate export destination without writing anything."""

    issues: list[LasExportIssue] = []
    target = _normalize_path(target_path)
    source = Path(source_path).expanduser() if source_path else None

    if source is not None and str(source).strip() and _same_file_path(target, source):
        issues.append(
            LasExportIssue(
                "error",
                "SOURCE_OVERWRITE_BLOCKED",
                "Нельзя сохранять новый LAS поверх исходного файла.",
                path=str(target),
                recommendation="Выберите новое имя файла или другую папку экспорта.",
            )
        )

    if target.exists() and not allow_overwrite:
        issues.append(
            LasExportIssue(
                "error",
                "TARGET_ALREADY_EXISTS",
                "Файл назначения уже существует, а перезапись отключена.",
                path=str(target),
                recommendation="Укажите новое имя файла или явно разрешите перезапись не исходного файла.",
            )
        )

    if target.parent and not target.parent.exists():
        issues.append(
            LasExportIssue(
                "warning",
                "PARENT_DIRECTORY_MISSING",
                "Папка назначения отсутствует и будет создана при экспорте.",
                path=str(target.parent),
            )
        )

    return target, tuple(issues)


def build_las_export_manifest(
    las_text: str,
    target_path: str | Path,
    *,
    source_path: str | Path | None = None,
    allow_overwrite: bool = False,
    dataframe: pd.DataFrame | None = None,
    validation_findings: Iterable[LasValidationFinding] = (),
) -> LasSafeExportManifest:
    """Build safe export manifest for preview/confirmation UI."""

    target, path_issues = validate_safe_export_request(target_path, source_path=source_path, allow_overwrite=allow_overwrite)
    findings = tuple(validation_findings)
    validation_errors = [f for f in findings if f.severity == "error"]
    issues = list(path_issues)
    for finding in validation_errors:
        issues.append(
            LasExportIssue(
                "error",
                finding.code,
                finding.message,
                recommendation=finding.recommendation,
            )
        )

    line_count = len(str(las_text or "").splitlines())
    bytes_count = len(str(las_text or "").encode("utf-8"))
    curve_count = int(len(dataframe.columns)) if dataframe is not None else 0
    row_count = int(len(dataframe)) if dataframe is not None else 0
    status = "blocked" if any(issue.severity == "error" for issue in issues) else "ready"

    return LasSafeExportManifest(
        schema=LAS_EXPORT_SCHEMA,
        status=status,
        created_at=_utc_now(),
        target_path=str(target),
        source_path=str(source_path or ""),
        bytes_count=bytes_count,
        line_count=line_count,
        curve_count=curve_count,
        row_count=row_count,
        overwrite_allowed=allow_overwrite,
        issues=tuple(issues),
        validation_summary={
            "errors": sum(1 for f in findings if f.severity == "error"),
            "warnings": sum(1 for f in findings if f.severity == "warning"),
            "info": sum(1 for f in findings if f.severity == "info"),
        },
    )


def export_las_text_safely(
    las_text: str,
    target_path: str | Path,
    *,
    source_path: str | Path | None = None,
    allow_overwrite: bool = False,
    create_parent: bool = True,
    dataframe: pd.DataFrame | None = None,
    validation_findings: Iterable[LasValidationFinding] = (),
) -> LasSafeExportManifest:
    """Write LAS text to a new target path only after safe-export validation."""

    manifest = build_las_export_manifest(
        las_text,
        target_path,
        source_path=source_path,
        allow_overwrite=allow_overwrite,
        dataframe=dataframe,
        validation_findings=validation_findings,
    )
    if not manifest.is_ready:
        return manifest

    target = Path(manifest.target_path)
    if create_parent:
        target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(str(las_text or ""), encoding="utf-8", newline="\n")
    return manifest


def export_las_document_safely(
    spec: LasCreationSpec,
    target_path: str | Path,
    *,
    dataframe: pd.DataFrame | None = None,
    source_path: str | Path | None = None,
    allow_overwrite: bool = False,
    create_parent: bool = True,
) -> LasSafeExportManifest:
    """Render and safely export a LAS document from a creation spec."""

    df = create_las_dataframe(spec) if dataframe is None else dataframe.copy()
    las_text = build_las_text(spec, df)
    ascii_findings = validate_las_ascii(
        df,
        expected_step=float(spec.step),
        start_depth=float(spec.start_depth),
        stop_depth=float(spec.stop_depth),
        null_value=getattr(spec, "null_value", DEFAULT_NULL_VALUE),
    )
    return export_las_text_safely(
        las_text,
        target_path,
        source_path=source_path,
        allow_overwrite=allow_overwrite,
        create_parent=create_parent,
        dataframe=df,
        validation_findings=ascii_findings,
    )


def export_issue_table_rows(issues: Iterable[LasExportIssue]) -> list[dict[str, Any]]:
    return [
        {
            "severity": issue.severity,
            "code": issue.code,
            "message": issue.message,
            "path": issue.path,
            "recommendation": issue.recommendation,
        }
        for issue in issues
    ]


def export_manifest_table(manifest: LasSafeExportManifest) -> list[dict[str, Any]]:
    return [
        {"name": "status", "value": manifest.status},
        {"name": "target_path", "value": manifest.target_path},
        {"name": "source_path", "value": manifest.source_path},
        {"name": "bytes_count", "value": manifest.bytes_count},
        {"name": "line_count", "value": manifest.line_count},
        {"name": "curve_count", "value": manifest.curve_count},
        {"name": "row_count", "value": manifest.row_count},
        {"name": "overwrite_allowed", "value": manifest.overwrite_allowed},
    ]
