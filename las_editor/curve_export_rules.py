from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

import pandas as pd

from las_editor.curve_mnemonics import lookup_curve_mnemonic
from las_editor.curve_rename import normalize_curve_name
from las_editor.curve_units import UNIT_CONVERSIONS, normalize_curve_unit, suggest_curve_unit

EXPORT_CURVE_MODES: dict[str, str] = {
    "all": "All curves",
    "selected": "Selected curves",
    "source_only": "Source curves only",
    "calculated_only": "Calculated curves only",
}

DUPLICATE_EXPORT_STRATEGIES: dict[str, str] = {
    "rename": "Rename duplicate curves with numeric suffix",
    "exclude": "Exclude duplicate curves after the first occurrence",
    "keep": "Keep duplicate curve names as-is",
}

METADATA_RULE_ACTIONS: tuple[str, ...] = ("keep", "replace", "remove")


@dataclass(frozen=True)
class ExportRuleProfile:
    profile_id: str
    label: str
    description: str
    mnemonic_map: dict[str, str] = field(default_factory=dict)
    unit_map: dict[str, str] = field(default_factory=dict)
    metadata_rules: dict[str, dict[str, str]] = field(default_factory=dict)
    null_value: float = -999.25
    curve_mode: str = "all"
    duplicate_strategy: str = "rename"
    exclude_hidden: bool = True
    exclude_duplicate_candidates: bool = False


@dataclass(frozen=True)
class CurveExportPreviewRow:
    source_curve: str
    export_curve: str
    source_unit: str
    export_unit: str
    export: bool
    action: str
    message: str


@dataclass(frozen=True)
class CurveExportResult:
    data: pd.DataFrame
    preview: tuple[CurveExportPreviewRow, ...]
    curve_units: dict[str, str]
    well_metadata: dict[str, str]
    summary: dict[str, int | str]
    warnings: tuple[str, ...]
    references: dict[str, Any]


DEFAULT_EXPORT_PROFILES: dict[str, ExportRuleProfile] = {
    "default_las": ExportRuleProfile(
        profile_id="default_las",
        label="Default LAS",
        description="Safe LAS 2.0 export with canonical mnemonic review and duplicate-safe names.",
        mnemonic_map={},
        unit_map={},
        metadata_rules={"NULL": {"action": "replace", "value": "-999.25"}},
        null_value=-999.25,
    ),
    "petrel": ExportRuleProfile(
        profile_id="petrel",
        label="Petrel",
        description="Petrel-friendly export: canonical petrophysical mnemonics, metre depth and LAS-safe duplicates.",
        mnemonic_map={"DEPTH": "DEPT", "MD": "DEPT", "GAMMA": "GR", "GK": "GR", "DEN": "RHOB", "RHOZ": "RHOB", "PHIN": "NPHI"},
        unit_map={"depth": "m", "DEPT": "m", "MD": "m", "RHOB": "g_cm3", "NPHI": "v_v"},
        metadata_rules={"NULL": {"action": "replace", "value": "-999.25"}, "COMPANY": {"action": "keep"}},
        null_value=-999.25,
    ),
    "techlog": ExportRuleProfile(
        profile_id="techlog",
        label="Techlog",
        description="Techlog-oriented export with canonical curve names and conventional null value.",
        mnemonic_map={"DEPTH": "DEPT", "GAMMA": "GR", "DEN": "RHOB", "NPOR": "NPHI", "TOTAL_GAS": "TGAS"},
        unit_map={"depth": "m", "DEPT": "m", "TGAS": "percent"},
        metadata_rules={"NULL": {"action": "replace", "value": "-999.25"}},
        null_value=-999.25,
    ),
    "kingdom": ExportRuleProfile(
        profile_id="kingdom",
        label="Kingdom",
        description="Kingdom export preset with short LAS-safe mnemonics and duplicate suffixes.",
        mnemonic_map={"DEPTH": "DEPT", "GAMMA": "GR", "RDEEP": "RT", "TOTAL_GAS": "TGAS"},
        unit_map={"depth": "m", "DEPT": "m"},
        metadata_rules={"NULL": {"action": "replace", "value": "-999.25"}},
        null_value=-999.25,
    ),
    "user_custom": ExportRuleProfile(
        profile_id="user_custom",
        label="User Custom",
        description="User profile placeholder for project-specific export rules.",
        mnemonic_map={},
        unit_map={},
        metadata_rules={},
        null_value=-999.25,
    ),
}


def _timestamp_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_export_profile_id(profile_id: object) -> str:
    value = str(profile_id or "default_las").strip().lower().replace(" ", "_").replace("-", "_")
    return value if value in DEFAULT_EXPORT_PROFILES else "default_las"


def available_export_profiles() -> tuple[str, ...]:
    return tuple(DEFAULT_EXPORT_PROFILES.keys())


def get_export_profile(profile_id: object = "default_las") -> ExportRuleProfile:
    return DEFAULT_EXPORT_PROFILES[normalize_export_profile_id(profile_id)]


def _profile_with_overrides(
    profile: ExportRuleProfile,
    *,
    mnemonic_map: Mapping[str, str] | None = None,
    unit_map: Mapping[str, str] | None = None,
    metadata_rules: Mapping[str, Mapping[str, str]] | None = None,
    null_value: float | None = None,
    curve_mode: str | None = None,
    duplicate_strategy: str | None = None,
    exclude_hidden: bool | None = None,
    exclude_duplicate_candidates: bool | None = None,
) -> ExportRuleProfile:
    merged_mnemonics = dict(profile.mnemonic_map)
    for key, value in dict(mnemonic_map or {}).items():
        source = normalize_curve_name(key)
        target = normalize_curve_name(value)
        if source and target:
            merged_mnemonics[source] = target

    merged_units = dict(profile.unit_map)
    for key, value in dict(unit_map or {}).items():
        key_text = normalize_curve_name(key) or str(key).strip().lower()
        unit = normalize_curve_unit(value)
        if key_text and unit:
            merged_units[key_text] = unit

    merged_metadata = {str(key).upper(): dict(value) for key, value in profile.metadata_rules.items()}
    for key, rule in dict(metadata_rules or {}).items():
        normalized_key = str(key).strip().upper()
        action = str(dict(rule).get("action", "keep")).strip().lower()
        if normalized_key and action in METADATA_RULE_ACTIONS:
            merged_metadata[normalized_key] = {"action": action, "value": str(dict(rule).get("value", ""))}

    return ExportRuleProfile(
        profile_id=profile.profile_id,
        label=profile.label,
        description=profile.description,
        mnemonic_map=merged_mnemonics,
        unit_map=merged_units,
        metadata_rules=merged_metadata,
        null_value=float(profile.null_value if null_value is None else null_value),
        curve_mode=curve_mode if curve_mode in EXPORT_CURVE_MODES else profile.curve_mode,
        duplicate_strategy=duplicate_strategy if duplicate_strategy in DUPLICATE_EXPORT_STRATEGIES else profile.duplicate_strategy,
        exclude_hidden=profile.exclude_hidden if exclude_hidden is None else bool(exclude_hidden),
        exclude_duplicate_candidates=profile.exclude_duplicate_candidates if exclude_duplicate_candidates is None else bool(exclude_duplicate_candidates),
    )


def _safe_export_name(value: object) -> str:
    name = normalize_curve_name(value)
    if not name:
        return "CURVE"
    if name[0].isdigit():
        name = f"C{name}"
    return name[:32]


def _canonical_export_name(curve: str, profile: ExportRuleProfile, aliases: Mapping[str, str] | None) -> str:
    normalized = normalize_curve_name(curve)
    alias_value = normalize_curve_name(dict(aliases or {}).get(curve, ""))
    for candidate in (normalized, alias_value):
        if candidate and candidate in profile.mnemonic_map:
            return _safe_export_name(profile.mnemonic_map[candidate])
    record = lookup_curve_mnemonic(alias_value or normalized)
    return _safe_export_name(profile.mnemonic_map.get(record.canonical, record.canonical))


def _resolve_source_unit(curve: str, unit_overrides: Mapping[str, str] | None) -> str:
    if curve in dict(unit_overrides or {}):
        return normalize_curve_unit(dict(unit_overrides or {})[curve])
    return suggest_curve_unit(curve)


def _resolve_target_unit(curve: str, export_curve: str, source_unit: str, profile: ExportRuleProfile) -> str:
    for key in (normalize_curve_name(curve), normalize_curve_name(export_curve), lookup_curve_mnemonic(curve).group):
        if key in profile.unit_map:
            return normalize_curve_unit(profile.unit_map[key])
    return source_unit


def _convert_series(series: pd.Series, source_unit: str, target_unit: str) -> tuple[pd.Series, bool]:
    if source_unit == target_unit:
        return series.copy(), False
    factor = UNIT_CONVERSIONS.get((source_unit, target_unit))
    if factor is None:
        return series.copy(), False
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.notna().sum() == 0:
        return series.copy(), False
    converted = numeric * factor
    return converted, True


def _selected_export_curves(
    columns: Iterable[object],
    *,
    profile: ExportRuleProfile,
    selected_curves: Iterable[object] | None,
    hidden_curves: Iterable[object] | None,
) -> tuple[str, ...]:
    all_columns = tuple(str(column) for column in columns)
    selected = {str(item) for item in (all_columns if selected_curves is None else selected_curves)}
    hidden = {str(item) for item in hidden_curves or ()}
    result: list[str] = []
    for column in all_columns:
        if profile.curve_mode == "selected" and column not in selected:
            continue
        if profile.exclude_hidden and column in hidden:
            continue
        if profile.curve_mode == "calculated_only" and not column.upper().startswith(("CALC_", "RATIO_")):
            continue
        if profile.curve_mode == "source_only" and column.upper().startswith(("CALC_", "RATIO_")):
            continue
        result.append(column)
    return tuple(result)


def build_curve_export_preview(
    df: pd.DataFrame,
    *,
    profile_id: object = "default_las",
    selected_curves: Iterable[object] | None = None,
    aliases: Mapping[str, str] | None = None,
    unit_overrides: Mapping[str, str] | None = None,
    hidden_curves: Iterable[object] | None = None,
    mnemonic_map: Mapping[str, str] | None = None,
    unit_map: Mapping[str, str] | None = None,
    curve_mode: str | None = None,
    duplicate_strategy: str | None = None,
) -> tuple[CurveExportPreviewRow, ...]:
    profile = _profile_with_overrides(
        get_export_profile(profile_id),
        mnemonic_map=mnemonic_map,
        unit_map=unit_map,
        curve_mode=curve_mode,
        duplicate_strategy=duplicate_strategy,
    )
    export_curves = _selected_export_curves(df.columns, profile=profile, selected_curves=selected_curves, hidden_curves=hidden_curves)
    used_names: dict[str, int] = {}
    rows: list[CurveExportPreviewRow] = []
    for curve in [str(column) for column in df.columns]:
        should_export = curve in export_curves
        export_name = _canonical_export_name(curve, profile, aliases)
        source_unit = _resolve_source_unit(curve, unit_overrides)
        export_unit = _resolve_target_unit(curve, export_name, source_unit, profile)
        action_parts: list[str] = []
        if export_name != _safe_export_name(curve):
            action_parts.append("rename")
        if source_unit != export_unit:
            action_parts.append("convert_unit")
        if not should_export:
            rows.append(CurveExportPreviewRow(curve, export_name, source_unit, export_unit, False, "skip", "Кривая исключена правилами профиля."))
            continue
        if export_name in used_names and profile.duplicate_strategy == "exclude":
            rows.append(CurveExportPreviewRow(curve, export_name, source_unit, export_unit, False, "skip_duplicate", "Дубликат экспортного имени исключен."))
            continue
        if export_name in used_names and profile.duplicate_strategy == "rename":
            used_names[export_name] += 1
            export_name = _safe_export_name(f"{export_name}_{used_names[export_name]}")
            action_parts.append("deduplicate")
        else:
            used_names.setdefault(export_name, 1)
        rows.append(
            CurveExportPreviewRow(
                source_curve=curve,
                export_curve=export_name,
                source_unit=source_unit,
                export_unit=export_unit,
                export=True,
                action=" + ".join(action_parts) if action_parts else "keep",
                message="Кривая будет экспортирована.",
            )
        )
    return tuple(rows)


def apply_curve_export_rules(
    df: pd.DataFrame,
    *,
    profile_id: object = "default_las",
    selected_curves: Iterable[object] | None = None,
    aliases: Mapping[str, str] | None = None,
    unit_overrides: Mapping[str, str] | None = None,
    hidden_curves: Iterable[object] | None = None,
    mnemonic_map: Mapping[str, str] | None = None,
    unit_map: Mapping[str, str] | None = None,
    metadata: Mapping[str, Any] | None = None,
    metadata_rules: Mapping[str, Mapping[str, str]] | None = None,
    null_value: float | None = None,
    curve_mode: str | None = None,
    duplicate_strategy: str | None = None,
    references: Mapping[str, Any] | None = None,
) -> CurveExportResult:
    if df is None or df.empty:
        raise ValueError("Нет данных LAS для применения правил экспорта.")

    profile = _profile_with_overrides(
        get_export_profile(profile_id),
        mnemonic_map=mnemonic_map,
        unit_map=unit_map,
        metadata_rules=metadata_rules,
        null_value=null_value,
        curve_mode=curve_mode,
        duplicate_strategy=duplicate_strategy,
    )
    preview = build_curve_export_preview(
        df,
        profile_id=profile.profile_id,
        selected_curves=selected_curves,
        aliases=aliases,
        unit_overrides=unit_overrides,
        hidden_curves=hidden_curves,
        mnemonic_map=profile.mnemonic_map,
        unit_map=profile.unit_map,
        curve_mode=profile.curve_mode,
        duplicate_strategy=profile.duplicate_strategy,
    )
    export_rows = [row for row in preview if row.export]
    if not export_rows:
        raise ValueError("Правила экспорта исключили все кривые.")

    export_df = pd.DataFrame(index=df.index)
    curve_units: dict[str, str] = {}
    warnings: list[str] = []
    renamed = 0
    converted = 0
    skipped = sum(1 for row in preview if not row.export)
    duplicates_resolved = 0

    for row in export_rows:
        series, did_convert = _convert_series(df[row.source_curve], row.source_unit, row.export_unit)
        export_df[row.export_curve] = series
        curve_units[row.export_curve] = row.export_unit
        renamed += int(row.source_curve != row.export_curve)
        converted += int(did_convert)
        duplicates_resolved += int("deduplicate" in row.action)
        if row.source_unit != row.export_unit and not did_convert:
            warnings.append(f"{row.source_curve}: нет безопасного коэффициента конвертации {row.source_unit} -> {row.export_unit}.")

    export_metadata = _apply_metadata_rules(metadata or {}, profile)
    export_metadata.setdefault("NULL", str(profile.null_value))
    summary: dict[str, int | str] = {
        "profile": profile.profile_id,
        "exported": len(export_df.columns),
        "renamed": renamed,
        "unit_converted": converted,
        "skipped": skipped,
        "duplicates_resolved": duplicates_resolved,
        "warnings": len(warnings),
    }
    updated_references = dict(references or {})
    updated_references["curve_export_rules"] = {
        "profile": profile.profile_id,
        "timestamp": _timestamp_utc(),
        "preview": [row.__dict__ for row in preview],
        "summary": summary,
        "curve_units": curve_units,
        "metadata": export_metadata,
    }
    return CurveExportResult(
        data=export_df,
        preview=preview,
        curve_units=curve_units,
        well_metadata=export_metadata,
        summary=summary,
        warnings=tuple(dict.fromkeys(warnings)),
        references=updated_references,
    )


def _apply_metadata_rules(metadata: Mapping[str, Any], profile: ExportRuleProfile) -> dict[str, str]:
    output = {str(key).upper(): str(value) for key, value in dict(metadata or {}).items() if value is not None}
    for key, rule in profile.metadata_rules.items():
        action = str(rule.get("action", "keep")).lower()
        if action == "remove":
            output.pop(key, None)
        elif action == "replace":
            output[key] = str(rule.get("value", ""))
        elif action == "keep":
            output.setdefault(key, str(rule.get("value", output.get(key, ""))))
    return {key: value for key, value in output.items() if str(value).strip()}


def curve_export_preview_rows(preview: Iterable[CurveExportPreviewRow]) -> tuple[dict[str, str], ...]:
    return tuple(
        {
            "source_curve": row.source_curve,
            "export_curve": row.export_curve,
            "source_unit": row.source_unit,
            "export_unit": row.export_unit,
            "export": "yes" if row.export else "no",
            "action": row.action,
            "message": row.message,
        }
        for row in preview
    )


def export_profile_rows() -> tuple[dict[str, str], ...]:
    return tuple(
        {
            "profile_id": profile.profile_id,
            "label": profile.label,
            "description": profile.description,
            "null_value": str(profile.null_value),
            "duplicate_strategy": profile.duplicate_strategy,
            "curve_mode": profile.curve_mode,
        }
        for profile in DEFAULT_EXPORT_PROFILES.values()
    )
