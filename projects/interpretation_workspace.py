from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Mapping, Sequence

import pandas as pd

from projects.project_manager import append_project_history
from projects.repository import safe_project_id
from projects.well_cards import safe_well_id

PROJECT_INTERPRETATION_FILE_NAME = "interpretation_workspace.json"
VSHMethod = Literal["linear", "larionov_tertiary", "larionov_older", "clavier", "steiber"]
PorosityMethod = Literal["density", "neutron", "sonic", "density_neutron", "effective"]
SaturationMethod = Literal["archie", "simandoux", "indonesia"]
PermeabilityMethod = Literal["timur", "coates"]


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
class PetrophysicalParameters:
    """Набор параметров для профессиональных петрофизических расчётов.

    Значения заданы инженерно-безопасными умолчаниями. Пользовательский интерфейс
    может подставлять фактические параметры по месторождению/скважине.
    """

    vsh_method: VSHMethod = "linear"
    gr_min: float | str = 30.0
    gr_max: float | str = 150.0
    density_matrix: float = 2.65
    density_fluid: float = 1.0
    sonic_matrix: float = 55.5
    sonic_fluid: float = 189.0
    rw: float = 0.08
    archie_a: float = 1.0
    archie_m: float = 2.0
    archie_n: float = 2.0
    rsh: float = 2.0
    timur_coefficient: float = 8581.0
    timur_phi_exponent: float = 4.4
    timur_sw_exponent: float = 2.0
    coates_constant: float = 100.0


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


@dataclass(frozen=True)
class NetPaySummary:
    rows: int
    reservoir_rows: int
    net_pay_rows: int
    gross_thickness: float
    reservoir_thickness: float
    net_pay_thickness: float
    ntg: float | None


def _series_or_constant(df: pd.DataFrame, name: str | float | int | None, default: float | None = None) -> pd.Series:
    if isinstance(name, str) and name in df.columns:
        return pd.to_numeric(df[name], errors="coerce")
    if isinstance(name, (int, float)):
        return pd.Series(float(name), index=df.index)
    if default is not None:
        return pd.Series(float(default), index=df.index)
    return pd.Series(pd.NA, index=df.index, dtype="float64")


def _safe_divide(numerator: pd.Series | float, denominator: pd.Series | float) -> pd.Series:
    numerator_series = numerator if isinstance(numerator, pd.Series) else pd.Series(float(numerator))
    denominator_series = denominator if isinstance(denominator, pd.Series) else pd.Series(float(denominator), index=numerator_series.index)
    denominator_series = denominator_series.where(denominator_series != 0)
    return numerator_series.astype("float64") / denominator_series.astype("float64")


def _clip01(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").clip(lower=0, upper=1)


def calculate_vsh_from_gr(
    df: pd.DataFrame,
    gr_curve: str = "GR",
    *,
    gr_min: float | str = 30.0,
    gr_max: float | str = 150.0,
    method: VSHMethod = "linear",
) -> pd.Series:
    """Calculate shale volume from gamma ray with common industry transforms.

    Supported methods:
    - linear: normalized GR index;
    - larionov_tertiary / larionov_older: Larionov corrections;
    - clavier: Clavier correction;
    - steiber: Steiber correction.
    """
    if df is None or df.empty or gr_curve not in df.columns:
        return pd.Series(dtype="float64")
    gr = pd.to_numeric(df[gr_curve], errors="coerce")
    low = _series_or_constant(df, gr_min)
    high = _series_or_constant(df, gr_max)
    igr = _clip01(_safe_divide(gr - low, high - low))

    if method == "linear":
        return igr
    if method == "larionov_tertiary":
        return _clip01(0.083 * ((2 ** (3.7 * igr)) - 1))
    if method == "larionov_older":
        return _clip01(0.33 * ((2 ** (2.0 * igr)) - 1))
    if method == "clavier":
        return _clip01(1.7 - ((3.38 - ((igr + 0.7) ** 2)) ** 0.5))
    if method == "steiber":
        return _clip01(_safe_divide(igr, 3 - (2 * igr)))
    raise ValueError(f"Неизвестный метод VSH: {method}")


def calculate_density_porosity(
    df: pd.DataFrame,
    density_curve: str = "RHOB",
    *,
    matrix_density: float = 2.65,
    fluid_density: float = 1.0,
) -> pd.Series:
    if df is None or df.empty or density_curve not in df.columns:
        return pd.Series(dtype="float64")
    rhob = pd.to_numeric(df[density_curve], errors="coerce")
    return _clip01(_safe_divide(matrix_density - rhob, matrix_density - fluid_density))


def calculate_sonic_porosity(
    df: pd.DataFrame,
    sonic_curve: str = "DT",
    *,
    matrix_transit_time: float = 55.5,
    fluid_transit_time: float = 189.0,
) -> pd.Series:
    if df is None or df.empty or sonic_curve not in df.columns:
        return pd.Series(dtype="float64")
    dt = pd.to_numeric(df[sonic_curve], errors="coerce")
    return _clip01(_safe_divide(dt - matrix_transit_time, fluid_transit_time - matrix_transit_time))


def calculate_neutron_porosity(df: pd.DataFrame, neutron_curve: str = "NPHI") -> pd.Series:
    if df is None or df.empty or neutron_curve not in df.columns:
        return pd.Series(dtype="float64")
    nphi = pd.to_numeric(df[neutron_curve], errors="coerce")
    # LAS часто содержит NPHI в долях, но иногда в процентах. Значения > 1 считаем процентами.
    nphi = nphi.where(nphi <= 1.5, nphi / 100.0)
    return _clip01(nphi)


def calculate_combined_density_neutron_porosity(
    df: pd.DataFrame,
    density_curve: str = "RHOB",
    neutron_curve: str = "NPHI",
    *,
    matrix_density: float = 2.65,
    fluid_density: float = 1.0,
) -> pd.Series:
    density_phi = calculate_density_porosity(df, density_curve, matrix_density=matrix_density, fluid_density=fluid_density)
    neutron_phi = calculate_neutron_porosity(df, neutron_curve)
    if density_phi.empty:
        return neutron_phi
    if neutron_phi.empty:
        return density_phi
    return _clip01(pd.concat([density_phi, neutron_phi], axis=1).mean(axis=1))


def calculate_effective_porosity(df: pd.DataFrame, porosity_curve: str = "PHIT", vsh_curve: str = "VSH") -> pd.Series:
    if df is None or df.empty or porosity_curve not in df.columns:
        return pd.Series(dtype="float64")
    phit = pd.to_numeric(df[porosity_curve], errors="coerce")
    vsh = pd.to_numeric(df[vsh_curve], errors="coerce") if vsh_curve in df.columns else pd.Series(0.0, index=df.index)
    return (phit * (1 - vsh)).clip(lower=0)


def calculate_porosity(
    df: pd.DataFrame,
    *,
    method: PorosityMethod = "effective",
    porosity_curve: str = "PHIT",
    vsh_curve: str = "VSH",
    density_curve: str = "RHOB",
    neutron_curve: str = "NPHI",
    sonic_curve: str = "DT",
    parameters: PetrophysicalParameters | None = None,
) -> pd.Series:
    params = parameters or PetrophysicalParameters()
    if method == "density":
        return calculate_density_porosity(df, density_curve, matrix_density=params.density_matrix, fluid_density=params.density_fluid)
    if method == "neutron":
        return calculate_neutron_porosity(df, neutron_curve)
    if method == "sonic":
        return calculate_sonic_porosity(df, sonic_curve, matrix_transit_time=params.sonic_matrix, fluid_transit_time=params.sonic_fluid)
    if method == "density_neutron":
        return calculate_combined_density_neutron_porosity(df, density_curve, neutron_curve, matrix_density=params.density_matrix, fluid_density=params.density_fluid)
    if method == "effective":
        return calculate_effective_porosity(df, porosity_curve, vsh_curve)
    raise ValueError(f"Неизвестный метод пористости: {method}")


def calculate_archie_sw(
    df: pd.DataFrame,
    resistivity_curve: str = "RT",
    porosity_curve: str = "PHIE",
    *,
    rw: float = 0.08,
    a: float = 1.0,
    m: float = 2.0,
    n: float = 2.0,
) -> pd.Series:
    if df is None or df.empty or resistivity_curve not in df.columns or porosity_curve not in df.columns:
        return pd.Series(dtype="float64")
    rt = pd.to_numeric(df[resistivity_curve], errors="coerce").where(lambda s: s > 0)
    phi = pd.to_numeric(df[porosity_curve], errors="coerce").where(lambda s: s > 0)
    sw = ((a * rw) / ((phi ** m) * rt)) ** (1 / n)
    return sw.clip(lower=0, upper=1)


def calculate_simandoux_sw(
    df: pd.DataFrame,
    resistivity_curve: str = "RT",
    porosity_curve: str = "PHIE",
    vsh_curve: str = "VSH",
    *,
    rw: float = 0.08,
    rsh: float = 2.0,
    a: float = 1.0,
    m: float = 2.0,
) -> pd.Series:
    if df is None or df.empty or resistivity_curve not in df.columns or porosity_curve not in df.columns:
        return pd.Series(dtype="float64")
    rt = pd.to_numeric(df[resistivity_curve], errors="coerce").where(lambda s: s > 0)
    phi = pd.to_numeric(df[porosity_curve], errors="coerce").where(lambda s: s > 0)
    vsh = pd.to_numeric(df[vsh_curve], errors="coerce").clip(lower=0, upper=1) if vsh_curve in df.columns else pd.Series(0.0, index=df.index)
    rsh_value = max(float(rsh), 1e-9)
    term = ((vsh / rsh_value) ** 2 + ((phi ** m) / (a * rw * rt))).pow(0.5)
    sw = _safe_divide(a * rw, 2 * (phi ** m)) * (term - (vsh / rsh_value)) * 2
    return _clip01(sw)


def calculate_indonesia_sw(
    df: pd.DataFrame,
    resistivity_curve: str = "RT",
    porosity_curve: str = "PHIE",
    vsh_curve: str = "VSH",
    *,
    rw: float = 0.08,
    rsh: float = 2.0,
    m: float = 2.0,
) -> pd.Series:
    if df is None or df.empty or resistivity_curve not in df.columns or porosity_curve not in df.columns:
        return pd.Series(dtype="float64")
    rt = pd.to_numeric(df[resistivity_curve], errors="coerce").where(lambda s: s > 0)
    phi = pd.to_numeric(df[porosity_curve], errors="coerce").where(lambda s: s > 0)
    vsh = pd.to_numeric(df[vsh_curve], errors="coerce").clip(lower=0, upper=1) if vsh_curve in df.columns else pd.Series(0.0, index=df.index)
    shale_term = (vsh ** (1 - (vsh / 2))) / (float(rsh) ** 0.5)
    rock_term = (phi ** (m / 2)) / (float(rw) ** 0.5)
    sw = _safe_divide(1 / (rt ** 0.5), shale_term + rock_term)
    return _clip01(sw)


def calculate_water_saturation(
    df: pd.DataFrame,
    *,
    method: SaturationMethod = "archie",
    resistivity_curve: str = "RT",
    porosity_curve: str = "PHIE",
    vsh_curve: str = "VSH",
    parameters: PetrophysicalParameters | None = None,
) -> pd.Series:
    params = parameters or PetrophysicalParameters()
    if method == "archie":
        return calculate_archie_sw(df, resistivity_curve, porosity_curve, rw=params.rw, a=params.archie_a, m=params.archie_m, n=params.archie_n)
    if method == "simandoux":
        return calculate_simandoux_sw(df, resistivity_curve, porosity_curve, vsh_curve, rw=params.rw, rsh=params.rsh, a=params.archie_a, m=params.archie_m)
    if method == "indonesia":
        return calculate_indonesia_sw(df, resistivity_curve, porosity_curve, vsh_curve, rw=params.rw, rsh=params.rsh, m=params.archie_m)
    raise ValueError(f"Неизвестный метод водонасыщенности: {method}")


def calculate_permeability(
    df: pd.DataFrame,
    *,
    method: PermeabilityMethod = "timur",
    porosity_curve: str = "PHIE",
    sw_curve: str = "SW",
    parameters: PetrophysicalParameters | None = None,
) -> pd.Series:
    if df is None or df.empty or porosity_curve not in df.columns or sw_curve not in df.columns:
        return pd.Series(dtype="float64")
    params = parameters or PetrophysicalParameters()
    phi = pd.to_numeric(df[porosity_curve], errors="coerce").where(lambda s: s > 0)
    sw = pd.to_numeric(df[sw_curve], errors="coerce").where(lambda s: s > 0)
    if method == "timur":
        return (params.timur_coefficient * (phi ** params.timur_phi_exponent) / (sw ** params.timur_sw_exponent)).clip(lower=0)
    if method == "coates":
        return (params.coates_constant * (phi ** 2) * (((1 - sw) / sw) ** 2)).clip(lower=0)
    raise ValueError(f"Неизвестный метод проницаемости: {method}")


def classify_lithology(vsh: float | None, porosity: float | None = None) -> str:
    if vsh is None or pd.isna(vsh):
        return "не определено"
    if vsh >= 0.65:
        return "глина"
    if vsh >= 0.45:
        return "глинистый песчаник"
    if vsh <= 0.20 and porosity is not None and pd.notna(porosity) and porosity >= 0.12:
        return "чистый коллектор"
    if vsh <= 0.35:
        return "песчаник/карбонат"
    return "смешанная литология"


def calculate_net_pay_summary(df: pd.DataFrame, depth_curve: str = "DEPT") -> NetPaySummary:
    if df is None or df.empty:
        return NetPaySummary(0, 0, 0, 0.0, 0.0, 0.0, None)
    rows = int(len(df))
    reservoir_rows = int(df.get("reservoir_flag", pd.Series(False, index=df.index)).fillna(False).sum())
    net_pay_rows = int(df.get("net_pay_flag", pd.Series(False, index=df.index)).fillna(False).sum())
    if depth_curve in df.columns and rows > 1:
        depth = pd.to_numeric(df[depth_curve], errors="coerce").dropna().sort_values()
        if len(depth) > 1:
            step = float(depth.diff().abs().dropna().median())
        else:
            step = 1.0
    else:
        step = 1.0
    gross = float(rows * step)
    reservoir = float(reservoir_rows * step)
    net = float(net_pay_rows * step)
    ntg = net / gross if gross else None
    return NetPaySummary(rows, reservoir_rows, net_pay_rows, gross, reservoir, net, ntg)


def build_interpretation_workspace(
    df: pd.DataFrame,
    *,
    gr_curve: str = "GR",
    porosity_curve: str = "PHIT",
    resistivity_curve: str = "RT",
    gr_min: float | str = 30.0,
    gr_max: float | str = 150.0,
    cutoffs: InterpretationCutoffs | None = None,
    parameters: PetrophysicalParameters | None = None,
    vsh_method: VSHMethod | None = None,
    porosity_method: PorosityMethod = "effective",
    saturation_method: SaturationMethod = "archie",
    permeability_method: PermeabilityMethod | None = None,
    density_curve: str = "RHOB",
    neutron_curve: str = "NPHI",
    sonic_curve: str = "DT",
) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    params = parameters or PetrophysicalParameters(gr_min=gr_min, gr_max=gr_max)
    result = df.copy()
    selected_vsh_method = vsh_method or params.vsh_method
    if gr_curve in result.columns:
        result["VSH"] = calculate_vsh_from_gr(result, gr_curve, gr_min=gr_min, gr_max=gr_max, method=selected_vsh_method)
    if porosity_method != "effective":
        result["PHIT_CALC"] = calculate_porosity(
            result,
            method=porosity_method,
            porosity_curve=porosity_curve,
            vsh_curve="VSH",
            density_curve=density_curve,
            neutron_curve=neutron_curve,
            sonic_curve=sonic_curve,
            parameters=params,
        )
        porosity_source = "PHIT_CALC"
    else:
        porosity_source = porosity_curve
    if porosity_source in result.columns:
        result["PHIE"] = calculate_effective_porosity(result, porosity_source, "VSH")
    if resistivity_curve in result.columns and "PHIE" in result.columns:
        result["SW"] = calculate_water_saturation(result, method=saturation_method, resistivity_curve=resistivity_curve, porosity_curve="PHIE", vsh_curve="VSH", parameters=params)
    if permeability_method and "PHIE" in result.columns and "SW" in result.columns:
        result["PERM"] = calculate_permeability(result, method=permeability_method, porosity_curve="PHIE", sw_curve="SW", parameters=params)
    rules = cutoffs or InterpretationCutoffs()
    vsh_ok = result.get("VSH", pd.Series(pd.NA, index=result.index)).astype("float64") <= rules.vsh_max
    phie_ok = result.get("PHIE", pd.Series(pd.NA, index=result.index)).astype("float64") >= rules.phie_min
    sw_ok = result.get("SW", pd.Series(pd.NA, index=result.index)).astype("float64") <= rules.sw_max
    result["reservoir_flag"] = (vsh_ok & phie_ok).fillna(False)
    result["net_pay_flag"] = (vsh_ok & phie_ok & sw_ok).fillna(False)
    result["lithology_hint"] = [
        classify_lithology(vsh, phie)
        for vsh, phie in zip(
            result.get("VSH", pd.Series(pd.NA, index=result.index)),
            result.get("PHIE", pd.Series(pd.NA, index=result.index)),
        )
    ]
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

# ---------------------------------------------------------------------------
# Interpretation Calculation Manager
# ---------------------------------------------------------------------------

PROJECT_INTERPRETATION_PRESETS_FILE_NAME = "interpretation_presets.json"
PROJECT_INTERPRETATION_RUNS_FILE_NAME = "interpretation_calculation_runs.json"
INTERPRETATION_DEFAULT_EXPORT_CURVES = ("VSH", "PHIE", "SW", "PERM", "reservoir_flag", "net_pay_flag", "lithology_hint")


@dataclass(frozen=True)
class InterpretationCalculationPreset:
    id: str
    name: str
    description: str = ""
    vsh_method: VSHMethod = "linear"
    porosity_method: PorosityMethod = "effective"
    saturation_method: SaturationMethod = "archie"
    permeability_method: PermeabilityMethod | str = "timur"
    parameters: dict[str, Any] | None = None
    cutoffs: dict[str, float] | None = None
    created_at: str = ""
    updated_at: str = ""


@dataclass(frozen=True)
class InterpretationCurvePreview:
    name: str
    unit: str = ""
    description: str = ""
    points: int = 0
    minimum: float | None = None
    maximum: float | None = None
    missing: int = 0


@dataclass(frozen=True)
class InterpretationCalculationRun:
    id: str
    name: str
    preset_id: str = ""
    source_type: str = "manual"
    source_id: str = ""
    well_id: str = ""
    status: str = "completed"
    rows: int = 0
    curves: tuple[str, ...] = ()
    validation_errors: tuple[str, ...] = ()
    validation_warnings: tuple[str, ...] = ()
    created_at: str = ""


@dataclass(frozen=True)
class InterpretationInputValidation:
    is_valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    available_curves: tuple[str, ...]
    missing_required_curves: tuple[str, ...]


def _preset_path(root: Path | str, project_id: str) -> Path:
    return _project_dir(root, project_id) / PROJECT_INTERPRETATION_PRESETS_FILE_NAME


def _runs_path(root: Path | str, project_id: str) -> Path:
    return _project_dir(root, project_id) / PROJECT_INTERPRETATION_RUNS_FILE_NAME


def _parameters_to_dict(parameters: PetrophysicalParameters | Mapping[str, Any] | None) -> dict[str, Any]:
    if parameters is None:
        return PetrophysicalParameters().__dict__.copy()
    if isinstance(parameters, PetrophysicalParameters):
        return parameters.__dict__.copy()
    return {str(key): value for key, value in parameters.items()}


def _cutoffs_to_dict(cutoffs: InterpretationCutoffs | Mapping[str, Any] | None) -> dict[str, float]:
    source = cutoffs.__dict__ if isinstance(cutoffs, InterpretationCutoffs) else (cutoffs or InterpretationCutoffs().__dict__)
    return {
        "vsh_max": float(source.get("vsh_max", InterpretationCutoffs.vsh_max)),
        "phie_min": float(source.get("phie_min", InterpretationCutoffs.phie_min)),
        "sw_max": float(source.get("sw_max", InterpretationCutoffs.sw_max)),
        "net_pay_min": float(source.get("net_pay_min", InterpretationCutoffs.net_pay_min)),
    }


def _parameters_from_mapping(values: Mapping[str, Any] | None) -> PetrophysicalParameters:
    defaults = PetrophysicalParameters().__dict__.copy()
    for key, value in (values or {}).items():
        if key in defaults:
            defaults[key] = value
    return PetrophysicalParameters(**defaults)


def _cutoffs_from_mapping(values: Mapping[str, Any] | None) -> InterpretationCutoffs:
    defaults = InterpretationCutoffs().__dict__.copy()
    for key, value in (values or {}).items():
        if key in defaults:
            defaults[key] = float(value)
    return InterpretationCutoffs(**defaults)


def default_interpretation_presets() -> tuple[InterpretationCalculationPreset, ...]:
    """Return built-in calculation scenarios for common petrophysical workflows."""
    now = _utc_now()
    base_parameters = _parameters_to_dict(PetrophysicalParameters())
    base_cutoffs = _cutoffs_to_dict(InterpretationCutoffs())
    return (
        InterpretationCalculationPreset(
            id="clean-sand-archie",
            name="Clean Sand Archie",
            description="Базовый сценарий для чистых терригенных коллекторов: Linear VSH, effective porosity, Archie SW.",
            vsh_method="linear",
            porosity_method="effective",
            saturation_method="archie",
            permeability_method="timur",
            parameters=base_parameters,
            cutoffs=base_cutoffs,
            created_at=now,
            updated_at=now,
        ),
        InterpretationCalculationPreset(
            id="shaly-sand-simandoux",
            name="Shaly Sand Simandoux",
            description="Сценарий для глинистых коллекторов: Clavier VSH и Simandoux water saturation.",
            vsh_method="clavier",
            porosity_method="effective",
            saturation_method="simandoux",
            permeability_method="coates",
            parameters={**base_parameters, "rsh": 2.5},
            cutoffs={**base_cutoffs, "vsh_max": 0.50, "sw_max": 0.75},
            created_at=now,
            updated_at=now,
        ),
        InterpretationCalculationPreset(
            id="density-neutron-indonesia",
            name="Density-Neutron Indonesia",
            description="Сценарий для расчёта пористости по RHOB/NPHI и насыщенности по Indonesia model.",
            vsh_method="larionov_older",
            porosity_method="density_neutron",
            saturation_method="indonesia",
            permeability_method="timur",
            parameters=base_parameters,
            cutoffs={**base_cutoffs, "phie_min": 0.06},
            created_at=now,
            updated_at=now,
        ),
    )


def _preset_from_mapping(row: Mapping[str, Any]) -> InterpretationCalculationPreset:
    return InterpretationCalculationPreset(
        id=_safe_id(str(row.get("id") or row.get("name") or "preset"), "preset"),
        name=_clean_text(row.get("name"), "Название пресета", required=True),
        description=_clean_text(row.get("description"), "Описание пресета", max_length=700),
        vsh_method=str(row.get("vsh_method") or "linear"),  # type: ignore[arg-type]
        porosity_method=str(row.get("porosity_method") or "effective"),  # type: ignore[arg-type]
        saturation_method=str(row.get("saturation_method") or "archie"),  # type: ignore[arg-type]
        permeability_method=str(row.get("permeability_method") or "timur"),
        parameters=_parameters_to_dict(row.get("parameters") if isinstance(row.get("parameters"), Mapping) else None),
        cutoffs=_cutoffs_to_dict(row.get("cutoffs") if isinstance(row.get("cutoffs"), Mapping) else None),
        created_at=_clean_text(row.get("created_at"), "Дата создания", max_length=80) or _utc_now(),
        updated_at=_clean_text(row.get("updated_at"), "Дата изменения", max_length=80) or _utc_now(),
    )


def list_interpretation_presets(root: Path | str, project_id: str, *, include_defaults: bool = True) -> list[InterpretationCalculationPreset]:
    payload = _json_read(_preset_path(root, project_id), {"presets": []})
    rows = payload.get("presets", []) if isinstance(payload, Mapping) else []
    presets = [_preset_from_mapping(row) for row in rows if isinstance(row, Mapping)]
    if include_defaults:
        default_presets = list(default_interpretation_presets())
        default_ids = {preset.id for preset in default_presets}
        presets = default_presets + [preset for preset in presets if preset.id not in default_ids]
    return presets


def save_interpretation_preset(
    root: Path | str,
    project_id: str,
    name: str,
    *,
    description: str = "",
    parameters: PetrophysicalParameters | Mapping[str, Any] | None = None,
    cutoffs: InterpretationCutoffs | Mapping[str, Any] | None = None,
    vsh_method: VSHMethod = "linear",
    porosity_method: PorosityMethod = "effective",
    saturation_method: SaturationMethod = "archie",
    permeability_method: PermeabilityMethod | str = "timur",
) -> InterpretationCalculationPreset:
    clean_name = _clean_text(name, "Название пресета", required=True)
    payload = _json_read(_preset_path(root, project_id), {"presets": []})
    rows = payload.get("presets", []) if isinstance(payload, Mapping) else []
    now = _utc_now()
    preset = InterpretationCalculationPreset(
        id=_safe_id(clean_name, "preset"),
        name=clean_name,
        description=_clean_text(description, "Описание пресета", max_length=700),
        vsh_method=vsh_method,
        porosity_method=porosity_method,
        saturation_method=saturation_method,
        permeability_method=permeability_method,
        parameters=_parameters_to_dict(parameters),
        cutoffs=_cutoffs_to_dict(cutoffs),
        created_at=now,
        updated_at=now,
    )
    filtered = [row for row in rows if not (isinstance(row, Mapping) and row.get("id") == preset.id)]
    filtered.append(preset.__dict__)
    _json_write(_preset_path(root, project_id), {"presets": filtered})
    append_project_history(root, project_id, "interpretation_preset_saved", f"Сохранен пресет интерпретации {clean_name}")
    return preset


def validate_interpretation_inputs(
    df: pd.DataFrame,
    *,
    gr_curve: str = "GR",
    porosity_curve: str = "PHIT",
    resistivity_curve: str = "RT",
    depth_curve: str = "DEPT",
    required_curves: Sequence[str] | None = None,
) -> InterpretationInputValidation:
    if df is None or df.empty:
        return InterpretationInputValidation(False, ("Таблица LAS пуста или не загружена.",), (), (), tuple(required_curves or ()))
    required = tuple(dict.fromkeys(required_curves or (gr_curve, porosity_curve, resistivity_curve)))
    available = tuple(str(column) for column in df.columns)
    missing = tuple(curve for curve in required if curve not in df.columns)
    errors = [f"Отсутствует обязательная кривая: {curve}." for curve in missing]
    warnings: list[str] = []
    if depth_curve in df.columns:
        depth = pd.to_numeric(df[depth_curve], errors="coerce").dropna()
        if depth.duplicated().any():
            warnings.append(f"Кривая глубины {depth_curve} содержит дубликаты.")
        if len(depth) > 1 and not (depth.is_monotonic_increasing or depth.is_monotonic_decreasing):
            warnings.append(f"Кривая глубины {depth_curve} не монотонна.")
    else:
        warnings.append(f"Кривая глубины {depth_curve} не найдена; толщины будут оцениваться по строкам.")
    for curve in required:
        if curve in df.columns:
            numeric = pd.to_numeric(df[curve], errors="coerce")
            if numeric.isna().all():
                errors.append(f"Кривая {curve} не содержит числовых значений.")
            elif numeric.isna().any():
                warnings.append(f"Кривая {curve} содержит пропуски: {int(numeric.isna().sum())}.")
    return InterpretationInputValidation(not errors, tuple(errors), tuple(warnings), available, missing)


def preview_interpreted_curves(df: pd.DataFrame, curves: Sequence[str] | None = None) -> tuple[InterpretationCurvePreview, ...]:
    selected = tuple(curves or INTERPRETATION_DEFAULT_EXPORT_CURVES)
    previews: list[InterpretationCurvePreview] = []
    descriptions = {
        "VSH": "Volume of shale",
        "PHIE": "Effective porosity",
        "SW": "Water saturation",
        "PERM": "Permeability",
        "reservoir_flag": "Reservoir interval flag",
        "net_pay_flag": "Net pay interval flag",
        "lithology_hint": "Lithology classification hint",
    }
    units = {"VSH": "v/v", "PHIE": "v/v", "SW": "v/v", "PERM": "mD"}
    for curve in selected:
        if df is None or df.empty or curve not in df.columns:
            continue
        series = df[curve]
        numeric = pd.to_numeric(series, errors="coerce")
        previews.append(
            InterpretationCurvePreview(
                name=curve,
                unit=units.get(curve, ""),
                description=descriptions.get(curve, curve),
                points=int(len(series)),
                minimum=float(numeric.min()) if numeric.notna().any() else None,
                maximum=float(numeric.max()) if numeric.notna().any() else None,
                missing=int(series.isna().sum()),
            )
        )
    return tuple(previews)


def export_interpreted_curves_to_dataframe(
    source_df: pd.DataFrame,
    interpreted_df: pd.DataFrame,
    *,
    curves: Sequence[str] | None = None,
    overwrite: bool = False,
) -> pd.DataFrame:
    """Merge calculated interpretation curves into a LAS-like dataframe.

    The function intentionally returns a new dataframe only. Actual LAS writing remains
    the responsibility of the LAS exporter so the original LAS file is never overwritten
    by the calculation manager.
    """
    if source_df is None or source_df.empty:
        return pd.DataFrame()
    result = source_df.copy()
    for curve in curves or INTERPRETATION_DEFAULT_EXPORT_CURVES:
        if interpreted_df is None or interpreted_df.empty or curve not in interpreted_df.columns:
            continue
        target_name = curve if overwrite or curve not in result.columns else f"{curve}_CALC"
        result[target_name] = interpreted_df[curve].values[: len(result)]
    return result


def _run_from_mapping(row: Mapping[str, Any]) -> InterpretationCalculationRun:
    return InterpretationCalculationRun(
        id=_safe_id(str(row.get("id") or row.get("name") or "run"), "run"),
        name=_clean_text(row.get("name"), "Название расчета", required=True),
        preset_id=_clean_text(row.get("preset_id"), "Пресет", max_length=140),
        source_type=_clean_text(row.get("source_type"), "Тип источника", max_length=80) or "manual",
        source_id=_clean_text(row.get("source_id"), "Источник", max_length=140),
        well_id=_clean_text(row.get("well_id"), "Скважина", max_length=140),
        status=_clean_text(row.get("status"), "Статус", max_length=80) or "completed",
        rows=int(row.get("rows") or 0),
        curves=tuple(str(item) for item in row.get("curves", ()) if str(item).strip()) if isinstance(row.get("curves", ()), Sequence) and not isinstance(row.get("curves"), str) else (),
        validation_errors=tuple(str(item) for item in row.get("validation_errors", ()) if str(item).strip()) if isinstance(row.get("validation_errors", ()), Sequence) and not isinstance(row.get("validation_errors"), str) else (),
        validation_warnings=tuple(str(item) for item in row.get("validation_warnings", ()) if str(item).strip()) if isinstance(row.get("validation_warnings", ()), Sequence) and not isinstance(row.get("validation_warnings"), str) else (),
        created_at=_clean_text(row.get("created_at"), "Дата создания", max_length=80) or _utc_now(),
    )


def list_interpretation_calculation_runs(root: Path | str, project_id: str) -> list[InterpretationCalculationRun]:
    payload = _json_read(_runs_path(root, project_id), {"runs": []})
    rows = payload.get("runs", []) if isinstance(payload, Mapping) else []
    return [_run_from_mapping(row) for row in rows if isinstance(row, Mapping)]


def run_interpretation_calculation(
    root: Path | str,
    project_id: str,
    name: str,
    df: pd.DataFrame,
    *,
    preset: InterpretationCalculationPreset | Mapping[str, Any] | None = None,
    source_type: str = "manual",
    source_id: str = "",
    well_id: str = "",
    gr_curve: str = "GR",
    porosity_curve: str = "PHIT",
    resistivity_curve: str = "RT",
    depth_curve: str = "DEPT",
) -> tuple[InterpretationCalculationRun, pd.DataFrame, tuple[InterpretationCurvePreview, ...]]:
    clean_name = _clean_text(name, "Название расчета", required=True)
    selected_preset = _preset_from_mapping(preset) if isinstance(preset, Mapping) else preset
    parameters = _parameters_from_mapping(selected_preset.parameters if selected_preset else None)
    cutoffs = _cutoffs_from_mapping(selected_preset.cutoffs if selected_preset else None)
    validation = validate_interpretation_inputs(df, gr_curve=gr_curve, porosity_curve=porosity_curve, resistivity_curve=resistivity_curve, depth_curve=depth_curve)
    if not validation.is_valid:
        run = InterpretationCalculationRun(
            id=_safe_id(f"{clean_name}-{_utc_now()}", "run"),
            name=clean_name,
            preset_id=selected_preset.id if selected_preset else "",
            source_type=source_type,
            source_id=source_id,
            well_id=well_id,
            status="failed",
            rows=0,
            validation_errors=validation.errors,
            validation_warnings=validation.warnings,
            created_at=_utc_now(),
        )
        _append_interpretation_run(root, project_id, run)
        return run, pd.DataFrame(), ()
    interpreted = build_interpretation_workspace(
        df,
        gr_curve=gr_curve,
        porosity_curve=porosity_curve,
        resistivity_curve=resistivity_curve,
        gr_min=parameters.gr_min,
        gr_max=parameters.gr_max,
        cutoffs=cutoffs,
        parameters=parameters,
        vsh_method=selected_preset.vsh_method if selected_preset else parameters.vsh_method,
        porosity_method=selected_preset.porosity_method if selected_preset else "effective",
        saturation_method=selected_preset.saturation_method if selected_preset else "archie",
        permeability_method=selected_preset.permeability_method if selected_preset else "timur",  # type: ignore[arg-type]
    )
    previews = preview_interpreted_curves(interpreted)
    run = InterpretationCalculationRun(
        id=_safe_id(f"{clean_name}-{_utc_now()}", "run"),
        name=clean_name,
        preset_id=selected_preset.id if selected_preset else "",
        source_type=_clean_text(source_type, "Тип источника", max_length=80) or "manual",
        source_id=_clean_text(source_id, "Источник", max_length=140),
        well_id=_clean_text(well_id, "Скважина", max_length=140),
        status="completed",
        rows=int(len(interpreted)),
        curves=tuple(preview.name for preview in previews),
        validation_warnings=validation.warnings,
        created_at=_utc_now(),
    )
    _append_interpretation_run(root, project_id, run)
    save_interpretation_record(root, project_id, clean_name, interpreted, source_type=source_type, source_id=source_id, well_id=well_id)
    append_project_history(root, project_id, "interpretation_calculation_run", f"Выполнен расчет интерпретации {clean_name}")
    return run, interpreted, previews


def _append_interpretation_run(root: Path | str, project_id: str, run: InterpretationCalculationRun) -> None:
    payload = _json_read(_runs_path(root, project_id), {"runs": []})
    rows = payload.get("runs", []) if isinstance(payload, Mapping) else []
    rows.append({**run.__dict__, "curves": list(run.curves), "validation_errors": list(run.validation_errors), "validation_warnings": list(run.validation_warnings)})
    _json_write(_runs_path(root, project_id), {"runs": rows[-200:]})
