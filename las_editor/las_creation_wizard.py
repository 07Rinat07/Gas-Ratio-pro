from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable

import pandas as pd

from las_editor.las_creator import (
    DEFAULT_NULL_VALUE,
    LasCreationResult,
    LasCreationSpec,
    LasCurveSpec,
    LasValidationIssue,
    build_las_creation_spec,
    builtin_las_templates,
    create_las_document,
    build_las_text,
    get_las_template_curves,
    normalize_las_mnemonic,
    validate_las_creation,
)


from projects.project_explorer_foundation import (
    OperationJournalEntry,
    OperationStatus,
    build_operation_entry,
)


class LasCreationMode(str, Enum):
    EMPTY = "empty"
    TEMPLATE = "template"
    FROM_LAS = "from_las"
    FROM_CSV = "from_csv"
    FROM_EXCEL = "from_excel"
    MANUAL = "manual"


def _normalize_creation_mode(value: object) -> LasCreationMode:
    raw = str(value.value if isinstance(value, Enum) else value or LasCreationMode.EMPTY.value).strip().lower()
    for mode in LasCreationMode:
        if raw == mode.value:
            return mode
    return LasCreationMode.EMPTY

LAS_CREATION_WIZARD_STORAGE_KEY = "las_creation_wizard"

LAS_CREATION_WIZARD_SCHEMA: dict[str, object] = {
    "workspace": "LAS Workspace",
    "module": "LAS Creation Wizard",
    "roadmap": "v5.0",
    "visible_without_loaded_las": True,
    "tools": [
        "New LAS",
        "Template Manager",
        "Header Builder",
        "Depth Generator",
        "Curve Library",
        "ASCII Builder",
        "Validate Before Save",
        "Save Working Copy",
        "Open Created LAS in Workspace",
    ],
}

DEFAULT_CURVE_LIBRARY: tuple[LasCurveSpec, ...] = (
    LasCurveSpec("GR", "API", "Gamma ray"),
    LasCurveSpec("SP", "MV", "Spontaneous potential"),
    LasCurveSpec("CALI", "IN", "Caliper"),
    LasCurveSpec("RHOB", "G/C3", "Bulk density"),
    LasCurveSpec("NPHI", "V/V", "Neutron porosity"),
    LasCurveSpec("DT", "US/F", "Sonic slowness"),
    LasCurveSpec("RT", "OHMM", "Deep resistivity"),
    LasCurveSpec("RILD", "OHMM", "Deep induction resistivity"),
    LasCurveSpec("RLLD", "OHMM", "Laterolog deep resistivity"),
    LasCurveSpec("MSFL", "OHMM", "Micro spherical focused log"),
    LasCurveSpec("C1", "PPM", "Methane"),
    LasCurveSpec("C2", "PPM", "Ethane"),
    LasCurveSpec("C3", "PPM", "Propane"),
    LasCurveSpec("TGAS", "PPM", "Total gas"),
)

@dataclass(frozen=True)
class LasWizardStep:
    code: str
    title: str
    required: bool = True
    complete: bool = False

@dataclass(frozen=True)
class LasCreationWizardDraft:
    well_name: str = ""
    start_depth: float | None = None
    stop_depth: float | None = None
    step: float | None = None
    template_name: str = "empty"
    curves: tuple[LasCurveSpec, ...] = field(default_factory=tuple)
    depth_unit: str = "M"
    null_value: float = DEFAULT_NULL_VALUE
    las_version: str = "2.0"
    mode: LasCreationMode = LasCreationMode.EMPTY
    source_las_text: str = ""
    source_dataframe: pd.DataFrame | None = None
    metadata: dict[str, object] = field(default_factory=dict)

@dataclass(frozen=True)
class LasCreationWizardResult:
    draft: LasCreationWizardDraft
    spec: LasCreationSpec | None
    document: LasCreationResult | None
    steps: tuple[LasWizardStep, ...]
    visible_tools: tuple[str, ...]
    can_save: bool
    issues: tuple[object, ...] = ()


def las_creation_visible_tools() -> tuple[str, ...]:
    """Return tools that must be visible even before a LAS file is loaded."""
    return tuple(LAS_CREATION_WIZARD_SCHEMA["tools"])


def curve_library_table_rows(curves: Iterable[LasCurveSpec] = DEFAULT_CURVE_LIBRARY) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for curve in curves:
        rows.append({
            "mnemonic": normalize_las_mnemonic(curve.mnemonic),
            "unit": curve.unit,
            "description": curve.description,
            "default_value": curve.default_value,
        })
    return rows


def template_table_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for name in builtin_las_templates():
        curves = get_las_template_curves(name)
        rows.append({
            "template": name,
            "curve_count": len(curves),
            "curves": ", ".join(curve.mnemonic for curve in curves) or "empty",
        })
    return rows


def build_las_creation_wizard_draft(
    *,
    well_name: str = "",
    start_depth: float | int | str | None = None,
    stop_depth: float | int | str | None = None,
    step: float | int | str | None = None,
    template_name: str = "empty",
    curves: Iterable[LasCurveSpec | dict[str, object] | str] = (),
    depth_unit: str = "M",
    null_value: float = DEFAULT_NULL_VALUE,
    las_version: str = "2.0",
    mode: LasCreationMode | str = LasCreationMode.EMPTY,
    source_las_text: str = "",
    source_dataframe: pd.DataFrame | None = None,
    **metadata: object,
) -> LasCreationWizardDraft:
    def to_optional_float(value: object) -> float | None:
        if value is None or str(value).strip() == "":
            return None
        return float(str(value).replace(",", "."))

    normalized_curves: list[LasCurveSpec] = []
    for item in curves:
        if isinstance(item, LasCurveSpec):
            normalized_curves.append(item)
        elif isinstance(item, dict):
            normalized_curves.append(
                LasCurveSpec(
                    str(item.get("mnemonic", "")),
                    str(item.get("unit", "")),
                    str(item.get("description", "")),
                    item.get("default_value"),
                )
            )
        else:
            normalized_curves.append(LasCurveSpec(str(item)))

    return LasCreationWizardDraft(
        well_name=str(well_name or "").strip(),
        start_depth=to_optional_float(start_depth),
        stop_depth=to_optional_float(stop_depth),
        step=to_optional_float(step),
        template_name=str(template_name or "empty").strip().lower(),
        curves=tuple(normalized_curves),
        depth_unit=str(depth_unit or "M").strip().upper() or "M",
        null_value=float(null_value),
        las_version=str(las_version or "2.0"),
        mode=_normalize_creation_mode(mode),
        source_las_text=str(source_las_text or ""),
        source_dataframe=source_dataframe.copy() if isinstance(source_dataframe, pd.DataFrame) else None,
        metadata=dict(metadata),
    )


def _wizard_steps(draft: LasCreationWizardDraft, document: LasCreationResult | None) -> tuple[LasWizardStep, ...]:
    has_header = bool(draft.well_name)
    has_depth = draft.start_depth is not None and draft.stop_depth is not None and draft.step is not None
    has_curves = bool(draft.curves or get_las_template_curves(draft.template_name))
    has_ascii = document is not None and isinstance(document.data, pd.DataFrame) and not document.data.empty
    is_valid = document is not None and not any(issue.severity == "error" for issue in document.issues)
    return (
        LasWizardStep("header", "Header Builder", complete=has_header),
        LasWizardStep("depth", "Depth Generator", complete=has_depth),
        LasWizardStep("curves", "Curve Library", complete=has_curves),
        LasWizardStep("ascii", "ASCII Builder", complete=has_ascii),
        LasWizardStep("validation", "Validate Before Save", complete=is_valid),
    )


def run_las_creation_wizard(draft: LasCreationWizardDraft) -> LasCreationWizardResult:
    """Build a LAS document from a wizard draft without touching existing LAS files."""
    spec: LasCreationSpec | None = None
    document: LasCreationResult | None = None
    issues: tuple[object, ...] = ()

    if draft.start_depth is not None and draft.stop_depth is not None and draft.step is not None:
        spec = build_las_creation_spec(
            well_name=draft.well_name or "WELL",
            start_depth=draft.start_depth,
            stop_depth=draft.stop_depth,
            step=draft.step,
            template_name=draft.template_name,
            curves=draft.curves,
            depth_unit=draft.depth_unit,
            null_value=draft.null_value,
            las_version=draft.las_version,
            **draft.metadata,
        )
        document = create_las_document(spec)
        issues = document.issues
    else:
        issues = ()

    steps = _wizard_steps(draft, document)
    can_save = document is not None and all(step.complete for step in steps if step.required)
    return LasCreationWizardResult(
        draft=draft,
        spec=spec,
        document=document,
        steps=steps,
        visible_tools=las_creation_visible_tools(),
        can_save=can_save,
        issues=issues,
    )


def build_las_creation_manifest(result: LasCreationWizardResult) -> dict[str, object]:
    return {
        "storage_key": LAS_CREATION_WIZARD_STORAGE_KEY,
        "workspace": LAS_CREATION_WIZARD_SCHEMA["workspace"],
        "module": LAS_CREATION_WIZARD_SCHEMA["module"],
        "visible_without_loaded_las": True,
        "visible_tools": list(result.visible_tools),
        "steps": [{"code": step.code, "title": step.title, "complete": step.complete} for step in result.steps],
        "can_save": result.can_save,
        "curve_count": 0 if result.document is None else max(0, len(result.document.data.columns) - 1),
        "row_count": 0 if result.document is None else len(result.document.data),
    }


@dataclass(frozen=True)
class SourceLasSummary:
    well_name: str
    start_depth: float | None
    stop_depth: float | None
    step: float | None
    depth_curve: str
    curves: tuple[LasCurveSpec, ...]

    @property
    def curve_count(self) -> int:
        return len(self.curves)


@dataclass(frozen=True)
class LasCreationWizardPreviewV2:
    draft: LasCreationWizardDraft
    spec: LasCreationSpec | None
    data: pd.DataFrame
    las_text: str
    issues: tuple[Any, ...]
    steps: tuple[LasWizardStep, ...]
    can_finalize: bool


@dataclass(frozen=True)
class LasCreationWizardFinalizeResult:
    filename: str
    las_text: str
    las_bytes: bytes
    preview: LasCreationWizardPreviewV2
    journal_entry: OperationJournalEntry


def las_creation_mode_rows() -> list[dict[str, str]]:
    return [
        {"mode": LasCreationMode.EMPTY.value, "title": "Empty LAS", "description": "Create a blank LAS file."},
        {"mode": LasCreationMode.TEMPLATE.value, "title": "From template", "description": "Create LAS from a built-in template."},
        {"mode": LasCreationMode.FROM_LAS.value, "title": "From LAS", "description": "Clone curve and depth structure from LAS."},
        {"mode": LasCreationMode.FROM_CSV.value, "title": "From CSV", "description": "Create LAS from tabular CSV data."},
        {"mode": LasCreationMode.FROM_EXCEL.value, "title": "From Excel", "description": "Create LAS from Excel data."},
        {"mode": LasCreationMode.MANUAL.value, "title": "Manual", "description": "Create LAS manually."},
    ]


def las_creation_template_rows() -> list[dict[str, object]]:
    return template_table_rows()


def _parse_las_curve_line(line: str) -> LasCurveSpec | None:
    text = str(line).strip()
    if not text or text.startswith("~") or "." not in text:
        return None
    left, _, description = text.partition(":")
    mnemonic_unit = left.strip().split(None, 1)[0]
    mnemonic, _, unit = mnemonic_unit.partition(".")
    mnemonic = normalize_las_mnemonic(mnemonic)
    if mnemonic in {"DEPT", "DEPTH"}:
        return None
    return LasCurveSpec(mnemonic=mnemonic, unit=unit.strip().upper(), description=description.strip() or mnemonic)


def summarize_source_las(source_las_text: str) -> SourceLasSummary:
    text = str(source_las_text or "")
    curves: list[LasCurveSpec] = []
    well_name = ""
    start_depth: float | None = None
    stop_depth: float | None = None
    step: float | None = None
    depth_curve = "DEPT"
    section = ""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        upper = line.upper()
        if upper.startswith("~"):
            section = upper
            continue
        if not line:
            continue
        if section.startswith("~WELL"):
            key = line.split(".", 1)[0].strip().upper()
            value_part = line.partition(":")[0].split(None, 1)
            value = value_part[1].strip() if len(value_part) > 1 else ""
            try:
                if key == "STRT":
                    start_depth = float(value)
                elif key == "STOP":
                    stop_depth = float(value)
                elif key == "STEP":
                    step = float(value)
                elif key == "WELL":
                    well_name = value
            except ValueError:
                pass
        elif section.startswith("~CURVE"):
            parsed = _parse_las_curve_line(line)
            if parsed is not None:
                curves.append(parsed)
            elif line.upper().startswith(("DEPT", "DEPTH")):
                depth_curve = "DEPT"
    return SourceLasSummary(well_name=well_name, start_depth=start_depth, stop_depth=stop_depth, step=step, depth_curve=depth_curve, curves=tuple(curves))


def _source_las_dataframe(text: str) -> pd.DataFrame:
    summary = summarize_source_las(text)
    columns = ["DEPT", *[curve.mnemonic for curve in summary.curves]]
    rows: list[list[float]] = []
    in_ascii = False
    for raw_line in str(text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.upper().startswith("~ASCII"):
            in_ascii = True
            continue
        if line.startswith("~"):
            in_ascii = False
            continue
        if in_ascii:
            parts = line.split()
            if len(parts) >= len(columns):
                try:
                    rows.append([float(parts[i]) for i in range(len(columns))])
                except ValueError:
                    continue
    df = pd.DataFrame(rows, columns=columns)
    df.attrs["las_units"] = {"DEPT": "M", **{curve.mnemonic: curve.unit for curve in summary.curves}}
    return df


def _tabular_source_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame(columns=["DEPT"])
    result = df.copy()
    rename: dict[str, str] = {}
    for column in result.columns:
        normalized = normalize_las_mnemonic(str(column))
        if normalized in {"DEPTH", "MD", "DEPTH_M", "DEPTHM"}:
            rename[column] = "DEPT"
        else:
            rename[column] = normalized
    result = result.rename(columns=rename)
    if "DEPT" not in result.columns:
        first = result.columns[0]
        result = result.rename(columns={first: "DEPT"})
    return result


def _spec_from_dataframe(draft: LasCreationWizardDraft, df: pd.DataFrame) -> LasCreationSpec:
    depth = pd.to_numeric(df["DEPT"], errors="coerce").dropna()
    if depth.empty:
        start = draft.start_depth if draft.start_depth is not None else 0.0
        stop = draft.stop_depth if draft.stop_depth is not None else start
        step = draft.step if draft.step is not None else 0.5
    else:
        start = float(depth.iloc[0])
        stop = float(depth.iloc[-1])
        diffs = depth.diff().dropna()
        positive = diffs[diffs > 0]
        step = float(positive.iloc[0]) if not positive.empty else (draft.step or 0.5)
    curves = [LasCurveSpec(str(col), str(df.attrs.get("las_units", {}).get(col, "")), str(col)) for col in df.columns if col != "DEPT"]
    return build_las_creation_spec(
        well_name=draft.well_name or "WELL",
        start_depth=start,
        stop_depth=stop,
        step=step,
        curves=curves,
        depth_unit=draft.depth_unit,
        null_value=draft.null_value,
        las_version=draft.las_version,
        **draft.metadata,
    )


def build_las_creation_wizard_preview_v2(draft: LasCreationWizardDraft) -> LasCreationWizardPreviewV2:
    mode = _normalize_creation_mode(draft.mode)
    if mode == LasCreationMode.FROM_LAS and draft.source_las_text:
        data = _source_las_dataframe(draft.source_las_text)
        spec = _spec_from_dataframe(draft, data)
        las_text = build_las_text(spec, data)
        issues = validate_las_creation(spec, data, las_text)
    elif mode in {LasCreationMode.FROM_CSV, LasCreationMode.FROM_EXCEL} and isinstance(draft.source_dataframe, pd.DataFrame):
        data = _tabular_source_dataframe(draft.source_dataframe)
        spec = _spec_from_dataframe(draft, data)
        las_text = build_las_text(spec, data)
        issues = validate_las_creation(spec, data, las_text)
    else:
        if draft.start_depth is None or draft.stop_depth is None or draft.step is None:
            spec = None
            data = pd.DataFrame(columns=["DEPT"])
            las_text = ""
            issues = ()
        else:
            # Treat TEMPLATE mode as the selected template; EMPTY/MANUAL can also use explicit curves.
            template_name = draft.template_name if mode == LasCreationMode.TEMPLATE else draft.template_name
            spec = build_las_creation_spec(
                well_name=draft.well_name or "WELL",
                start_depth=draft.start_depth,
                stop_depth=draft.stop_depth,
                step=draft.step,
                template_name=template_name,
                curves=draft.curves,
                depth_unit=draft.depth_unit,
                null_value=draft.null_value,
                las_version=draft.las_version,
                **draft.metadata,
            )
            try:
                document = create_las_document(spec)
                data = document.data
                las_text = document.las_text
                issues = document.issues
            except ValueError as exc:
                data = pd.DataFrame(columns=["DEPT", *[curve.mnemonic for curve in spec.curves]])
                las_text = ""
                code = "DEPTH_RANGE_INVALID" if spec.start_depth > spec.stop_depth else "LAS_CREATION_INVALID"
                issues = (LasValidationIssue("error", code, str(exc)),)
    fake_result = LasCreationResult(spec=spec, data=data, las_text=las_text, issues=tuple(issues)) if spec is not None else None
    steps = _wizard_steps(draft, fake_result)
    can_finalize = spec is not None and bool(las_text) and not any(getattr(issue, "severity", "") == "error" for issue in issues)
    return LasCreationWizardPreviewV2(draft=draft, spec=spec, data=data, las_text=las_text, issues=tuple(issues), steps=steps, can_finalize=can_finalize)


def finalize_las_creation_wizard(draft: LasCreationWizardDraft) -> LasCreationWizardFinalizeResult:
    preview = build_las_creation_wizard_preview_v2(draft)
    if not preview.can_finalize or preview.spec is None:
        raise ValueError("LAS creation preview has validation errors and cannot be finalized.")
    safe_well = normalize_las_mnemonic(preview.spec.well_name, fallback="WELL")
    filename = f"{safe_well}.las"
    journal = build_operation_entry(
        operation_type="las_creation",
        title="Create LAS working copy",
        status=OperationStatus.COMPLETED,
        creates_copy=True,
        can_undo=False,
        summary=f"Created LAS working copy {filename}.",
        details={"well_name": preview.spec.well_name, "row_count": len(preview.data), "curve_count": max(0, len(preview.data.columns) - 1)},
    )
    return LasCreationWizardFinalizeResult(
        filename=filename,
        las_text=preview.las_text,
        las_bytes=preview.las_text.encode("utf-8"),
        preview=preview,
        journal_entry=journal,
    )


def wizard_issue_rows(issues: Iterable[Any]) -> list[dict[str, object]]:
    return [
        {
            "severity": getattr(issue, "severity", "info"),
            "code": getattr(issue, "code", "INFO"),
            "message": getattr(issue, "message", str(issue)),
        }
        for issue in issues
    ]


def wizard_step_rows(draft_or_preview: LasCreationWizardDraft | LasCreationWizardPreviewV2) -> list[dict[str, object]]:
    if isinstance(draft_or_preview, LasCreationWizardPreviewV2):
        steps = draft_or_preview.steps
    else:
        steps = build_las_creation_wizard_preview_v2(draft_or_preview).steps
    return [{"code": step.code, "title": step.title, "required": step.required, "completed": step.complete} for step in steps]
