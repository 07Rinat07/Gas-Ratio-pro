from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

import pandas as pd

from las_editor.las_creator import (
    DEFAULT_NULL_VALUE,
    LasCreationResult,
    LasCreationSpec,
    LasCurveSpec,
    build_las_creation_spec,
    builtin_las_templates,
    create_las_document,
    get_las_template_curves,
    normalize_las_mnemonic,
    validate_las_creation,
)

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
