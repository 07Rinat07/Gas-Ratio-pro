from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
from datetime import date
import math
import re
from typing import Iterable

import pandas as pd

from las_editor.depth_grid import build_depth_grid


LAS_MANDATORY_SECTIONS: tuple[str, ...] = ("~Version", "~Well", "~Curve", "~Parameter", "~ASCII")
DEFAULT_NULL_VALUE = -999.25


@dataclass(frozen=True)
class LasCurveSpec:
    """Definition of one LAS curve used by the creation wizard.

    The wizard keeps the object deliberately small: mnemonic, unit,
    description and default value are enough to generate a valid LAS table.
    Extra metadata can be introduced later without changing the writer API.
    """

    mnemonic: str
    unit: str = ""
    description: str = ""
    default_value: float | int | str | None = None


@dataclass(frozen=True)
class LasCreationSpec:
    """Input model for creating a LAS file from scratch."""

    well_name: str
    start_depth: float
    stop_depth: float
    step: float
    depth_unit: str = "M"
    null_value: float = DEFAULT_NULL_VALUE
    las_version: str = "2.0"
    uwi: str = ""
    api: str = ""
    company: str = ""
    field: str = ""
    location: str = ""
    service_company: str = "GAS RATIO PRO"
    curves: tuple[LasCurveSpec, ...] = dataclass_field(default_factory=tuple)
    parameters: dict[str, str | int | float] = dataclass_field(default_factory=dict)


@dataclass(frozen=True)
class LasValidationIssue:
    severity: str
    code: str
    message: str


@dataclass(frozen=True)
class LasCreationResult:
    spec: LasCreationSpec
    data: pd.DataFrame
    las_text: str
    issues: tuple[LasValidationIssue, ...] = ()

    @property
    def las_bytes(self) -> bytes:
        return self.las_text.encode("utf-8")


_BUILTIN_TEMPLATES: dict[str, tuple[LasCurveSpec, ...]] = {
    "empty": (),
    "mud_gas": (
        LasCurveSpec("C1", "ppm", "Methane"),
        LasCurveSpec("C2", "ppm", "Ethane"),
        LasCurveSpec("C3", "ppm", "Propane"),
        LasCurveSpec("IC4", "ppm", "Iso-butane"),
        LasCurveSpec("NC4", "ppm", "Normal butane"),
        LasCurveSpec("IC5", "ppm", "Iso-pentane"),
        LasCurveSpec("NC5", "ppm", "Normal pentane"),
        LasCurveSpec("TGAS", "ppm", "Total gas"),
    ),
    "petrophysics": (
        LasCurveSpec("GR", "API", "Gamma ray"),
        LasCurveSpec("RHOB", "G/C3", "Bulk density"),
        LasCurveSpec("NPHI", "V/V", "Neutron porosity"),
        LasCurveSpec("DT", "US/F", "Sonic slowness"),
        LasCurveSpec("RT", "OHMM", "Deep resistivity"),
        LasCurveSpec("POR", "V/V", "Porosity"),
        LasCurveSpec("SW", "V/V", "Water saturation"),
    ),
}


def normalize_las_mnemonic(value: str, *, fallback: str = "CURVE") -> str:
    """Return a LAS-safe mnemonic.

    LAS mnemonic rules vary by vendor, but the safest portable baseline is an
    uppercase alphanumeric/underscore token that does not start with a digit.
    """

    name = re.sub(r"[^0-9A-Za-z_]+", "_", str(value or "").strip().upper()).strip("_")
    if not name:
        name = fallback
    if name[0].isdigit():
        name = f"C{name}"
    return name[:32]


def normalize_las_unit(value: str) -> str:
    unit = re.sub(r"[^0-9A-Za-z_/%-]+", "_", str(value or "").strip().upper()).strip("_")
    return unit[:16]


def builtin_las_templates() -> tuple[str, ...]:
    return tuple(_BUILTIN_TEMPLATES)


def get_las_template_curves(template_name: str) -> tuple[LasCurveSpec, ...]:
    key = str(template_name or "empty").strip().lower()
    if key not in _BUILTIN_TEMPLATES:
        raise ValueError(f"Unknown LAS template: {template_name!r}")
    return _BUILTIN_TEMPLATES[key]


def build_las_creation_spec(
    *,
    well_name: str,
    start_depth,
    stop_depth,
    step,
    template_name: str = "empty",
    curves: Iterable[LasCurveSpec | dict[str, object] | str] = (),
    **metadata,
) -> LasCreationSpec:
    """Build a validated creation spec from UI-friendly values."""

    template_curves = list(get_las_template_curves(template_name))
    custom_curves: list[LasCurveSpec] = []
    for item in curves:
        if isinstance(item, LasCurveSpec):
            custom_curves.append(item)
        elif isinstance(item, dict):
            custom_curves.append(
                LasCurveSpec(
                    mnemonic=str(item.get("mnemonic", "")),
                    unit=str(item.get("unit", "")),
                    description=str(item.get("description", "")),
                    default_value=item.get("default_value"),
                )
            )
        else:
            custom_curves.append(LasCurveSpec(str(item)))

    curve_map: dict[str, LasCurveSpec] = {}
    for curve in [*template_curves, *custom_curves]:
        mnemonic = normalize_las_mnemonic(curve.mnemonic)
        if mnemonic == "DEPT":
            continue
        curve_map[mnemonic] = LasCurveSpec(
            mnemonic=mnemonic,
            unit=normalize_las_unit(curve.unit),
            description=curve.description or mnemonic,
            default_value=curve.default_value,
        )

    return LasCreationSpec(
        well_name=str(well_name or "WELL").strip() or "WELL",
        start_depth=float(str(start_depth).replace(",", ".")),
        stop_depth=float(str(stop_depth).replace(",", ".")),
        step=float(str(step).replace(",", ".")),
        depth_unit=normalize_las_unit(str(metadata.get("depth_unit", "M"))) or "M",
        null_value=float(str(metadata.get("null_value", DEFAULT_NULL_VALUE)).replace(",", ".")),
        las_version=str(metadata.get("las_version", "2.0") or "2.0"),
        uwi=str(metadata.get("uwi", "") or ""),
        api=str(metadata.get("api", "") or ""),
        company=str(metadata.get("company", "") or ""),
        field=str(metadata.get("field", "") or ""),
        location=str(metadata.get("location", "") or ""),
        service_company=str(metadata.get("service_company", "GAS RATIO PRO") or "GAS RATIO PRO"),
        curves=tuple(curve_map.values()),
        parameters=dict(metadata.get("parameters", {}) or {}),
    )


def create_las_dataframe(spec: LasCreationSpec) -> pd.DataFrame:
    depths = build_depth_grid(spec.start_depth, spec.stop_depth, spec.step)
    data: dict[str, list[object]] = {"DEPT": list(depths)}
    for curve in spec.curves:
        mnemonic = normalize_las_mnemonic(curve.mnemonic)
        default = curve.default_value
        values = [default for _ in depths]
        data[mnemonic] = values
    df = pd.DataFrame(data)
    df.attrs["las_units"] = {"DEPT": spec.depth_unit, **{normalize_las_mnemonic(c.mnemonic): c.unit for c in spec.curves}}
    df.attrs["las_null_value"] = spec.null_value
    return df


def add_las_curve(df: pd.DataFrame, curve: LasCurveSpec, *, null_value: float = DEFAULT_NULL_VALUE) -> pd.DataFrame:
    result = df.copy()
    mnemonic = normalize_las_mnemonic(curve.mnemonic)
    if mnemonic in result.columns:
        raise ValueError(f"Curve {mnemonic!r} already exists.")
    result[mnemonic] = curve.default_value if curve.default_value is not None else math.nan
    units = dict(result.attrs.get("las_units", {}))
    units[mnemonic] = normalize_las_unit(curve.unit)
    result.attrs.update(df.attrs)
    result.attrs["las_units"] = units
    result.attrs.setdefault("las_null_value", null_value)
    return result


def delete_las_curve(df: pd.DataFrame, mnemonic: str) -> pd.DataFrame:
    curve_name = normalize_las_mnemonic(mnemonic)
    if curve_name == "DEPT":
        raise ValueError("Depth curve cannot be deleted.")
    if curve_name not in df.columns:
        raise ValueError(f"Curve {curve_name!r} was not found.")
    result = df.drop(columns=[curve_name]).copy()
    units = dict(df.attrs.get("las_units", {}))
    units.pop(curve_name, None)
    result.attrs.update(df.attrs)
    result.attrs["las_units"] = units
    return result


def _format_value(value: object, null_value: float) -> str:
    if value is None or pd.isna(value):
        return f"{null_value:.10g}"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f"{float(value):.10g}"
    text = str(value).strip()
    return re.sub(r"\s+", "_", text) if text else f"{null_value:.10g}"


def build_las_text(spec: LasCreationSpec, df: pd.DataFrame | None = None) -> str:
    data = create_las_dataframe(spec) if df is None else df.copy()
    if "DEPT" not in data.columns:
        raise ValueError("LAS dataframe must contain DEPT depth column.")

    units = {"DEPT": spec.depth_unit, **dict(data.attrs.get("las_units", {}))}
    metadata_rows = [
        ("WELL", spec.well_name, "Well name"),
        ("UWI", spec.uwi, "Unique well identifier"),
        ("API", spec.api, "API number"),
        ("COMP", spec.company, "Company"),
        ("FLD", spec.field, "Field"),
        ("LOC", spec.location, "Location"),
        ("SRVC", spec.service_company, "Service company"),
    ]

    lines = [
        "~Version",
        f"VERS. {spec.las_version} : CWLS LAS version",
        "WRAP. NO : One line per depth step",
        "~Well",
        f"STRT.{spec.depth_unit} {spec.start_depth:.10g} : Start depth",
        f"STOP.{spec.depth_unit} {spec.stop_depth:.10g} : Stop depth",
        f"STEP.{spec.depth_unit} {spec.step:.10g} : Depth step",
        f"NULL. {spec.null_value:.10g} : Null value",
    ]
    for mnemonic, value, description in metadata_rows:
        if str(value).strip():
            lines.append(f"{mnemonic}. {str(value).strip()} : {description}")

    lines.append("~Curve")
    lines.append(f"DEPT.{spec.depth_unit} : Depth")
    for column in data.columns:
        if column == "DEPT":
            continue
        curve_name = normalize_las_mnemonic(column)
        unit = normalize_las_unit(units.get(column, ""))
        description = next((curve.description for curve in spec.curves if normalize_las_mnemonic(curve.mnemonic) == curve_name), curve_name)
        lines.append(f"{curve_name}.{unit} : {description}")

    lines.append("~Parameter")
    lines.append(f"CREATED. {date.today().isoformat()} : Created by GAS RATIO PRO LAS Creation Wizard")
    for key, value in spec.parameters.items():
        safe_key = normalize_las_mnemonic(key, fallback="PARAM")
        lines.append(f"{safe_key}. {value} : User parameter")

    lines.append("~ASCII")
    for _idx, row in data.iterrows():
        lines.append(" ".join(_format_value(row[column], spec.null_value) for column in data.columns))

    return "\n".join(lines) + "\n"


def validate_las_creation(spec: LasCreationSpec, df: pd.DataFrame | None = None, las_text: str | None = None) -> tuple[LasValidationIssue, ...]:
    issues: list[LasValidationIssue] = []
    if not spec.well_name.strip():
        issues.append(LasValidationIssue("error", "WELL_NAME_EMPTY", "Well name is required."))
    if spec.step <= 0:
        issues.append(LasValidationIssue("error", "STEP_INVALID", "Depth step must be positive."))
    if spec.start_depth > spec.stop_depth:
        issues.append(LasValidationIssue("error", "DEPTH_RANGE_INVALID", "Start depth cannot be greater than stop depth."))

    mnemonics = [normalize_las_mnemonic(c.mnemonic) for c in spec.curves]
    duplicates = sorted({m for m in mnemonics if mnemonics.count(m) > 1})
    for mnemonic in duplicates:
        issues.append(LasValidationIssue("error", "CURVE_DUPLICATE", f"Duplicate curve mnemonic: {mnemonic}."))

    data = df if df is not None else create_las_dataframe(spec)
    if "DEPT" not in data.columns:
        issues.append(LasValidationIssue("error", "DEPTH_MISSING", "DEPT column is required."))
    elif not pd.to_numeric(data["DEPT"], errors="coerce").is_monotonic_increasing:
        issues.append(LasValidationIssue("warning", "DEPTH_NOT_MONOTONIC", "Depth column is not monotonically increasing."))

    text = las_text if las_text is not None else build_las_text(spec, data)
    upper_text = text.upper()
    for section in LAS_MANDATORY_SECTIONS:
        if section.upper() not in upper_text:
            issues.append(LasValidationIssue("error", "SECTION_MISSING", f"Mandatory LAS section is missing: {section}."))
    return tuple(issues)


def create_las_document(spec: LasCreationSpec) -> LasCreationResult:
    data = create_las_dataframe(spec)
    las_text = build_las_text(spec, data)
    issues = validate_las_creation(spec, data, las_text)
    return LasCreationResult(spec=spec, data=data, las_text=las_text, issues=issues)
