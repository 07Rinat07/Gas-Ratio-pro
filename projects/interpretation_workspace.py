from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import pandas as pd

from projects.project_manager import append_project_history
from projects.repository import safe_project_id
from projects.well_cards import safe_well_id

PROJECT_INTERPRETATION_FILE_NAME = "interpretation_workspace.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _project_dir(root: Path | str, project_id: str) -> Path:
    return Path(root) / safe_project_id(project_id)


def _interpretation_path(root: Path | str, project_id: str) -> Path:
    return _project_dir(root, project_id) / PROJECT_INTERPRETATION_FILE_NAME


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


def _clean_text(value: Any, field_label: str, *, max_length: int = 180, required: bool = False) -> str:
    text = "" if value is None else str(value).strip()
    if required and not text:
        raise ValueError(f"{field_label}: значение обязательно.")
    if len(text) > max_length:
        raise ValueError(f"{field_label}: максимум {max_length} символов.")
    return text


def _safe_id(value: str, default: str = "interpretation") -> str:
    raw = _clean_text(value, "ID", max_length=140) or default
    normalized = re.sub(r"[^0-9A-Za-zА-Яа-я_-]+", "-", raw).strip("-_").lower() or default
    return safe_well_id(normalized)


@dataclass(frozen=True)
class InterpretationCutoffs:
    vsh_max: float = 0.45
    phie_min: float = 0.08
    sw_max: float = 0.65
    net_pay_min: float = 0.1


@dataclass(frozen=True)
class InterpretationRecord:
    id: str
    name: str
    source_type: str = "manual"
    source_id: str = ""
    well_id: str = ""
    rows: int = 0
    reservoir_rows: int = 0
    net_pay_rows: int = 0
    created_at: str = ""


@dataclass(frozen=True)
class InterpretationSummary:
    rows: int
    reservoir_rows: int
    net_pay_rows: int
    average_vsh: float | None
    average_phie: float | None
    average_sw: float | None


def _series_or_constant(df: pd.DataFrame, name: str | float | int | None, default: float | None = None) -> pd.Series:
    if isinstance(name, str) and name in df.columns:
        return pd.to_numeric(df[name], errors="coerce")
    if isinstance(name, (int, float)):
        return pd.Series(float(name), index=df.index)
    if default is not None:
        return pd.Series(float(default), index=df.index)
    return pd.Series(pd.NA, index=df.index, dtype="float64")


def _safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    denominator = denominator.where(denominator != 0)
    return numerator.astype("float64") / denominator.astype("float64")


def calculate_vsh_from_gr(df: pd.DataFrame, gr_curve: str = "GR", *, gr_min: float | str = 30.0, gr_max: float | str = 150.0) -> pd.Series:
    if df is None or df.empty or gr_curve not in df.columns:
        return pd.Series(dtype="float64")
    gr = pd.to_numeric(df[gr_curve], errors="coerce")
    low = _series_or_constant(df, gr_min)
    high = _series_or_constant(df, gr_max)
    return _safe_divide(gr - low, high - low).clip(lower=0, upper=1)


def calculate_effective_porosity(df: pd.DataFrame, porosity_curve: str = "PHIT", vsh_curve: str = "VSH") -> pd.Series:
    if df is None or df.empty or porosity_curve not in df.columns:
        return pd.Series(dtype="float64")
    phit = pd.to_numeric(df[porosity_curve], errors="coerce")
    vsh = pd.to_numeric(df[vsh_curve], errors="coerce") if vsh_curve in df.columns else pd.Series(0.0, index=df.index)
    return (phit * (1 - vsh)).clip(lower=0)


def calculate_archie_sw(df: pd.DataFrame, resistivity_curve: str = "RT", porosity_curve: str = "PHIE", *, rw: float = 0.08, a: float = 1.0, m: float = 2.0, n: float = 2.0) -> pd.Series:
    if df is None or df.empty or resistivity_curve not in df.columns or porosity_curve not in df.columns:
        return pd.Series(dtype="float64")
    rt = pd.to_numeric(df[resistivity_curve], errors="coerce").where(lambda s: s > 0)
    phi = pd.to_numeric(df[porosity_curve], errors="coerce").where(lambda s: s > 0)
    sw = ((a * rw) / ((phi ** m) * rt)) ** (1 / n)
    return sw.clip(lower=0, upper=1)


def build_interpretation_workspace(
    df: pd.DataFrame,
    *,
    gr_curve: str = "GR",
    porosity_curve: str = "PHIT",
    resistivity_curve: str = "RT",
    gr_min: float | str = 30.0,
    gr_max: float | str = 150.0,
    cutoffs: InterpretationCutoffs | None = None,
) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    result = df.copy()
    if gr_curve in result.columns:
        result["VSH"] = calculate_vsh_from_gr(result, gr_curve, gr_min=gr_min, gr_max=gr_max)
    if porosity_curve in result.columns:
        result["PHIE"] = calculate_effective_porosity(result, porosity_curve, "VSH")
    if resistivity_curve in result.columns and "PHIE" in result.columns:
        result["SW"] = calculate_archie_sw(result, resistivity_curve, "PHIE")
    rules = cutoffs or InterpretationCutoffs()
    vsh_ok = result.get("VSH", pd.Series(pd.NA, index=result.index)).astype("float64") <= rules.vsh_max
    phie_ok = result.get("PHIE", pd.Series(pd.NA, index=result.index)).astype("float64") >= rules.phie_min
    sw_ok = result.get("SW", pd.Series(pd.NA, index=result.index)).astype("float64") <= rules.sw_max
    result["reservoir_flag"] = (vsh_ok & phie_ok).fillna(False)
    result["net_pay_flag"] = (vsh_ok & phie_ok & sw_ok).fillna(False)
    result["lithology_hint"] = result.get("VSH", pd.Series(pd.NA, index=result.index)).map(
        lambda value: "чистый коллектор" if pd.notna(value) and value <= 0.25 else ("глинистый интервал" if pd.notna(value) and value >= 0.55 else "смешанная зона")
    )
    return result


def summarize_interpretation_workspace(df: pd.DataFrame) -> InterpretationSummary:
    if df is None or df.empty:
        return InterpretationSummary(0, 0, 0, None, None, None)
    return InterpretationSummary(
        rows=int(len(df)),
        reservoir_rows=int(df.get("reservoir_flag", pd.Series(False, index=df.index)).fillna(False).sum()),
        net_pay_rows=int(df.get("net_pay_flag", pd.Series(False, index=df.index)).fillna(False).sum()),
        average_vsh=float(pd.to_numeric(df["VSH"], errors="coerce").mean()) if "VSH" in df.columns else None,
        average_phie=float(pd.to_numeric(df["PHIE"], errors="coerce").mean()) if "PHIE" in df.columns else None,
        average_sw=float(pd.to_numeric(df["SW"], errors="coerce").mean()) if "SW" in df.columns else None,
    )


def save_interpretation_record(
    root: Path | str,
    project_id: str,
    name: str,
    interpreted_df: pd.DataFrame,
    *,
    source_type: str = "manual",
    source_id: str = "",
    well_id: str = "",
) -> InterpretationRecord:
    clean_name = _clean_text(name, "Название интерпретации", required=True)
    summary = summarize_interpretation_workspace(interpreted_df)
    payload = _json_read(_interpretation_path(root, project_id), {"records": []})
    records = payload.get("records", []) if isinstance(payload, Mapping) else []
    record = InterpretationRecord(
        id=_safe_id(f"{clean_name}-{_utc_now()}", "interpretation"),
        name=clean_name,
        source_type=_clean_text(source_type, "Тип источника", max_length=60) or "manual",
        source_id=_clean_text(source_id, "Источник", max_length=140),
        well_id=_clean_text(well_id, "Скважина", max_length=140),
        rows=summary.rows,
        reservoir_rows=summary.reservoir_rows,
        net_pay_rows=summary.net_pay_rows,
        created_at=_utc_now(),
    )
    records.append(record.__dict__)
    _json_write(_interpretation_path(root, project_id), {"records": records})
    append_project_history(root, project_id, "interpretation_saved", f"Сохранена интерпретация {clean_name}")
    return record


def list_interpretation_records(root: Path | str, project_id: str) -> list[InterpretationRecord]:
    payload = _json_read(_interpretation_path(root, project_id), {"records": []})
    rows = payload.get("records", []) if isinstance(payload, Mapping) else []
    return [InterpretationRecord(**row) for row in rows if isinstance(row, Mapping)]
