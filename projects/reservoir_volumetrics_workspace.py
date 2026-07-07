from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median, pstdev
from typing import Any, Iterable, Sequence

from projects.project_manager import append_project_history
from projects.repository import DEFAULT_PROJECT_ID, DEFAULT_PROJECTS_ROOT, safe_project_id

RESERVOIR_VOLUMETRICS_FILE_NAME = "reservoir_volumetrics_workspace.json"
ESTIMATE_CASES = {"low", "base", "high"}
VOLUME_UNITS = {"m3", "mmbbl", "bbl", "mcf", "bcm"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _project_dir(root: Any, project_id: str) -> Path:
    return Path(root) / safe_project_id(project_id)


def _workspace_path(root: Any, project_id: str) -> Path:
    return _project_dir(root, project_id) / RESERVOIR_VOLUMETRICS_FILE_NAME


def _clean_text(value: Any, label: str, *, required: bool = False, max_length: int = 180) -> str:
    text = "" if value is None else str(value).strip()
    if required and not text:
        raise ValueError(f"{label}: значение обязательно.")
    if len(text) > max_length:
        raise ValueError(f"{label}: максимум {max_length} символов.")
    return text


def _to_float(value: Any, label: str, *, required: bool = False, default: float | None = None) -> float | None:
    if value is None or value == "":
        if required:
            raise ValueError(f"{label}: значение обязательно.")
        return default
    if isinstance(value, str):
        value = value.strip().replace(",", ".")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label}: ожидается число.") from exc
    if number != number or number in (float("inf"), float("-inf")):
        raise ValueError(f"{label}: значение должно быть конечным числом.")
    return round(number, 10)


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


@dataclass(frozen=True)
class VolumetricCell:
    cell_id: str
    zone: str
    bulk_volume: float
    porosity: float
    water_saturation: float
    net_flag: bool = True
    pay_flag: bool = True
    oil_saturation: float | None = None
    gas_saturation: float | None = None
    formation_volume_factor_oil: float = 1.2
    formation_volume_factor_gas: float = 0.005
    recovery_factor: float = 0.25
    case: str = "base"


@dataclass(frozen=True)
class VolumetricCutoffs:
    min_porosity: float = 0.0
    max_water_saturation: float = 1.0
    require_net_flag: bool = True
    require_pay_flag: bool = False


@dataclass(frozen=True)
class ZoneVolumetricSummary:
    zone: str
    case: str
    cell_count: int
    brv: float
    nrv: float
    pv: float
    hcpv: float
    ooip_stb: float
    ogip_scf: float
    recoverable_oil_stb: float
    recoverable_gas_scf: float
    average_porosity: float
    average_water_saturation: float
    net_gross: float


@dataclass(frozen=True)
class ReservoirVolumetricsJob:
    job_id: str
    name: str
    case: str = "base"
    cutoffs: dict[str, Any] = field(default_factory=dict)
    contact_set: str = ""
    source: str = "property_modeling_workspace"
    status: str = "draft"
    created_at: str = ""
    note: str = ""


@dataclass(frozen=True)
class ReservoirVolumetricsManifest:
    project_id: str
    generated_at: str
    job_count: int
    zone_count: int
    total_brv: float
    total_nrv: float
    total_pv: float
    total_hcpv: float
    total_ooip_stb: float
    total_ogip_scf: float
    warnings: tuple[str, ...] = ()


def _cell_from_dict(raw: dict[str, Any]) -> VolumetricCell:
    bulk_volume = _to_float(raw.get("bulk_volume"), "Bulk volume", required=True) or 0.0
    if bulk_volume < 0:
        raise ValueError("Bulk volume не может быть отрицательным.")
    porosity = _to_float(raw.get("porosity"), "Porosity", required=True) or 0.0
    water = _to_float(raw.get("water_saturation"), "Water saturation", required=True) or 0.0
    if not 0 <= porosity <= 1:
        raise ValueError("Porosity должен быть в диапазоне 0..1.")
    if not 0 <= water <= 1:
        raise ValueError("Water saturation должен быть в диапазоне 0..1.")
    oil = _to_float(raw.get("oil_saturation"), "Oil saturation")
    gas = _to_float(raw.get("gas_saturation"), "Gas saturation")
    case = _clean_text(raw.get("case", "base"), "Case", max_length=30).lower() or "base"
    if case not in ESTIMATE_CASES:
        raise ValueError(f"Case должен быть одним из: {', '.join(sorted(ESTIMATE_CASES))}.")
    return VolumetricCell(
        cell_id=_clean_text(raw.get("cell_id"), "Cell ID", required=True),
        zone=_clean_text(raw.get("zone"), "Zone", required=True),
        bulk_volume=bulk_volume,
        porosity=porosity,
        water_saturation=water,
        net_flag=bool(raw.get("net_flag", True)),
        pay_flag=bool(raw.get("pay_flag", True)),
        oil_saturation=oil,
        gas_saturation=gas,
        formation_volume_factor_oil=_to_float(raw.get("formation_volume_factor_oil", 1.2), "Bo", required=True) or 1.2,
        formation_volume_factor_gas=_to_float(raw.get("formation_volume_factor_gas", 0.005), "Bg", required=True) or 0.005,
        recovery_factor=_to_float(raw.get("recovery_factor", 0.25), "Recovery factor", required=True) or 0.25,
        case=case,
    )


def _cell_to_dict(cell: VolumetricCell) -> dict[str, Any]:
    return {
        "cell_id": cell.cell_id,
        "zone": cell.zone,
        "bulk_volume": cell.bulk_volume,
        "porosity": cell.porosity,
        "water_saturation": cell.water_saturation,
        "net_flag": cell.net_flag,
        "pay_flag": cell.pay_flag,
        "oil_saturation": cell.oil_saturation,
        "gas_saturation": cell.gas_saturation,
        "formation_volume_factor_oil": cell.formation_volume_factor_oil,
        "formation_volume_factor_gas": cell.formation_volume_factor_gas,
        "recovery_factor": cell.recovery_factor,
        "case": cell.case,
    }


def _job_to_dict(job: ReservoirVolumetricsJob) -> dict[str, Any]:
    return {
        "job_id": job.job_id,
        "name": job.name,
        "case": job.case,
        "cutoffs": dict(job.cutoffs),
        "contact_set": job.contact_set,
        "source": job.source,
        "status": job.status,
        "created_at": job.created_at,
        "note": job.note,
    }


def _job_from_dict(raw: dict[str, Any]) -> ReservoirVolumetricsJob:
    case = _clean_text(raw.get("case", "base"), "Case", max_length=30).lower() or "base"
    if case not in ESTIMATE_CASES:
        raise ValueError(f"Case должен быть одним из: {', '.join(sorted(ESTIMATE_CASES))}.")
    return ReservoirVolumetricsJob(
        job_id=_clean_text(raw.get("job_id"), "Job ID", required=True),
        name=_clean_text(raw.get("name"), "Название расчета", required=True),
        case=case,
        cutoffs=dict(raw.get("cutoffs") or {}),
        contact_set=_clean_text(raw.get("contact_set"), "Contact set", max_length=120),
        source=_clean_text(raw.get("source"), "Источник", max_length=180) or "property_modeling_workspace",
        status=_clean_text(raw.get("status"), "Статус", max_length=40) or "draft",
        created_at=_clean_text(raw.get("created_at"), "Дата", max_length=80),
        note=_clean_text(raw.get("note"), "Примечание", max_length=600),
    )


def _load_workspace(root: Any, project_id: str) -> dict[str, Any]:
    payload = _json_read(_workspace_path(root, project_id), {})
    if not isinstance(payload, dict):
        payload = {}
    payload.setdefault("jobs", [])
    payload.setdefault("last_manifest", {})
    return payload


def _save_workspace(root: Any, project_id: str, payload: dict[str, Any]) -> None:
    payload["updated_at"] = _now_iso()
    _json_write(_workspace_path(root, project_id), payload)


def create_reservoir_volumetrics_job(
    root: Any = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
    *,
    job_id: str,
    name: str,
    case: str = "base",
    cutoffs: dict[str, Any] | None = None,
    contact_set: str = "",
    source: str = "property_modeling_workspace",
    note: str = "",
) -> ReservoirVolumetricsJob:
    safe_id = safe_project_id(project_id)
    payload = _load_workspace(root, safe_id)
    jobs = [_job_from_dict(item) for item in payload.get("jobs", []) if isinstance(item, dict)]
    clean_job_id = _clean_text(job_id, "Job ID", required=True)
    if any(job.job_id == clean_job_id for job in jobs):
        raise ValueError(f"Расчет '{clean_job_id}' уже существует.")
    job = ReservoirVolumetricsJob(
        job_id=clean_job_id,
        name=_clean_text(name, "Название расчета", required=True),
        case=_clean_text(case, "Case", max_length=30).lower() or "base",
        cutoffs=dict(cutoffs or {}),
        contact_set=_clean_text(contact_set, "Contact set", max_length=120),
        source=_clean_text(source, "Источник", max_length=180) or "property_modeling_workspace",
        status="ready",
        created_at=_now_iso(),
        note=_clean_text(note, "Примечание", max_length=600),
    )
    if job.case not in ESTIMATE_CASES:
        raise ValueError(f"Case должен быть одним из: {', '.join(sorted(ESTIMATE_CASES))}.")
    jobs.append(job)
    payload["jobs"] = [_job_to_dict(item) for item in jobs]
    _save_workspace(root, safe_id, payload)
    append_project_history(root, safe_id, "reservoir_volumetrics_job_created", f"Created reservoir volumetrics job: {job.name}", object_type="reservoir_volumetrics", object_id=job.job_id)
    return job


def list_reservoir_volumetrics_jobs(root: Any = DEFAULT_PROJECTS_ROOT, project_id: str = DEFAULT_PROJECT_ID) -> tuple[ReservoirVolumetricsJob, ...]:
    payload = _load_workspace(root, safe_project_id(project_id))
    return tuple(_job_from_dict(item) for item in payload.get("jobs", []) if isinstance(item, dict))


def build_cutoffs(raw: dict[str, Any] | VolumetricCutoffs | None = None) -> VolumetricCutoffs:
    if isinstance(raw, VolumetricCutoffs):
        return raw
    raw = raw or {}
    return VolumetricCutoffs(
        min_porosity=_to_float(raw.get("min_porosity", 0.0), "Min porosity", required=True) or 0.0,
        max_water_saturation=_to_float(raw.get("max_water_saturation", 1.0), "Max Sw", required=True) or 1.0,
        require_net_flag=bool(raw.get("require_net_flag", True)),
        require_pay_flag=bool(raw.get("require_pay_flag", False)),
    )


def cell_passes_cutoffs(cell: VolumetricCell, cutoffs: VolumetricCutoffs | dict[str, Any] | None = None) -> bool:
    cut = build_cutoffs(cutoffs)
    if cell.porosity < cut.min_porosity:
        return False
    if cell.water_saturation > cut.max_water_saturation:
        return False
    if cut.require_net_flag and not cell.net_flag:
        return False
    if cut.require_pay_flag and not cell.pay_flag:
        return False
    return True


def compute_cell_volumes(cell: VolumetricCell, *, apply_cutoffs: bool = True, cutoffs: VolumetricCutoffs | dict[str, Any] | None = None) -> dict[str, float]:
    passes = cell_passes_cutoffs(cell, cutoffs) if apply_cutoffs else True
    brv = cell.bulk_volume
    nrv = brv if passes and cell.net_flag else 0.0
    pv = nrv * cell.porosity
    oil_sat = cell.oil_saturation if cell.oil_saturation is not None else max(0.0, 1.0 - cell.water_saturation - (cell.gas_saturation or 0.0))
    gas_sat = cell.gas_saturation if cell.gas_saturation is not None else 0.0
    hcpv = pv * max(0.0, 1.0 - cell.water_saturation)
    ooip_stb = 6.28981 * pv * oil_sat / max(cell.formation_volume_factor_oil, 1e-12)
    ogip_scf = 35.3147 * pv * gas_sat / max(cell.formation_volume_factor_gas, 1e-12)
    return {
        "brv": round(brv, 6),
        "nrv": round(nrv, 6),
        "pv": round(pv, 6),
        "hcpv": round(hcpv, 6),
        "ooip_stb": round(ooip_stb, 6),
        "ogip_scf": round(ogip_scf, 6),
        "recoverable_oil_stb": round(ooip_stb * cell.recovery_factor, 6),
        "recoverable_gas_scf": round(ogip_scf * cell.recovery_factor, 6),
    }


def summarize_volumetrics_by_zone(
    cells: Iterable[dict[str, Any] | VolumetricCell],
    *,
    cutoffs: VolumetricCutoffs | dict[str, Any] | None = None,
    case: str | None = None,
) -> tuple[ZoneVolumetricSummary, ...]:
    parsed = [item if isinstance(item, VolumetricCell) else _cell_from_dict(item) for item in cells]
    if case:
        parsed = [cell for cell in parsed if cell.case == case]
    zones = sorted({cell.zone for cell in parsed})
    summaries: list[ZoneVolumetricSummary] = []
    for zone in zones:
        zone_cells = [cell for cell in parsed if cell.zone == zone]
        totals = {key: 0.0 for key in ("brv", "nrv", "pv", "hcpv", "ooip_stb", "ogip_scf", "recoverable_oil_stb", "recoverable_gas_scf")}
        for cell in zone_cells:
            values = compute_cell_volumes(cell, cutoffs=cutoffs)
            for key in totals:
                totals[key] += values[key]
        porosities = [cell.porosity for cell in zone_cells]
        sw_values = [cell.water_saturation for cell in zone_cells]
        summaries.append(ZoneVolumetricSummary(
            zone=zone,
            case=case or (zone_cells[0].case if zone_cells else "base"),
            cell_count=len(zone_cells),
            brv=round(totals["brv"], 6),
            nrv=round(totals["nrv"], 6),
            pv=round(totals["pv"], 6),
            hcpv=round(totals["hcpv"], 6),
            ooip_stb=round(totals["ooip_stb"], 6),
            ogip_scf=round(totals["ogip_scf"], 6),
            recoverable_oil_stb=round(totals["recoverable_oil_stb"], 6),
            recoverable_gas_scf=round(totals["recoverable_gas_scf"], 6),
            average_porosity=round(mean(porosities), 6) if porosities else 0.0,
            average_water_saturation=round(mean(sw_values), 6) if sw_values else 0.0,
            net_gross=round(totals["nrv"] / totals["brv"], 6) if totals["brv"] else 0.0,
        ))
    return tuple(summaries)


def summarize_uncertainty(summaries: Sequence[ZoneVolumetricSummary]) -> dict[str, Any]:
    by_case: dict[str, dict[str, float]] = {}
    for summary in summaries:
        bucket = by_case.setdefault(summary.case, {"ooip_stb": 0.0, "ogip_scf": 0.0, "hcpv": 0.0})
        bucket["ooip_stb"] += summary.ooip_stb
        bucket["ogip_scf"] += summary.ogip_scf
        bucket["hcpv"] += summary.hcpv
    return {case: {key: round(value, 6) for key, value in values.items()} for case, values in sorted(by_case.items())}


def build_zone_volumetrics_table(summaries: Sequence[ZoneVolumetricSummary]) -> list[dict[str, Any]]:
    return [
        {
            "zone": item.zone,
            "case": item.case,
            "cells": item.cell_count,
            "BRV_m3": item.brv,
            "NRV_m3": item.nrv,
            "PV_m3": item.pv,
            "HCPV_m3": item.hcpv,
            "OOIP_stb": item.ooip_stb,
            "OGIP_scf": item.ogip_scf,
            "RF_oil_stb": item.recoverable_oil_stb,
            "RF_gas_scf": item.recoverable_gas_scf,
            "avg_phi": item.average_porosity,
            "avg_sw": item.average_water_saturation,
            "net_gross": item.net_gross,
        }
        for item in summaries
    ]


def build_reservoir_volumetrics_manifest(
    summaries: Sequence[ZoneVolumetricSummary],
    *,
    project_id: str = DEFAULT_PROJECT_ID,
    job_count: int = 0,
) -> ReservoirVolumetricsManifest:
    warnings: list[str] = []
    if not summaries:
        warnings.append("Нет расчетных зон для объемной оценки.")
    return ReservoirVolumetricsManifest(
        project_id=safe_project_id(project_id),
        generated_at=_now_iso(),
        job_count=job_count,
        zone_count=len({item.zone for item in summaries}),
        total_brv=round(sum(item.brv for item in summaries), 6),
        total_nrv=round(sum(item.nrv for item in summaries), 6),
        total_pv=round(sum(item.pv for item in summaries), 6),
        total_hcpv=round(sum(item.hcpv for item in summaries), 6),
        total_ooip_stb=round(sum(item.ooip_stb for item in summaries), 6),
        total_ogip_scf=round(sum(item.ogip_scf for item in summaries), 6),
        warnings=tuple(warnings),
    )


def manifest_to_dict(manifest: ReservoirVolumetricsManifest) -> dict[str, Any]:
    return {
        "project_id": manifest.project_id,
        "generated_at": manifest.generated_at,
        "job_count": manifest.job_count,
        "zone_count": manifest.zone_count,
        "total_brv": manifest.total_brv,
        "total_nrv": manifest.total_nrv,
        "total_pv": manifest.total_pv,
        "total_hcpv": manifest.total_hcpv,
        "total_ooip_stb": manifest.total_ooip_stb,
        "total_ogip_scf": manifest.total_ogip_scf,
        "warnings": list(manifest.warnings),
    }


def render_reservoir_volumetrics_markdown(
    summaries: Sequence[ZoneVolumetricSummary],
    *,
    manifest: ReservoirVolumetricsManifest | None = None,
    title: str = "Reservoir Volumetrics Workspace",
) -> str:
    manifest = manifest or build_reservoir_volumetrics_manifest(summaries)
    lines = [f"# {title}", "", f"Generated: {manifest.generated_at}", "", "## Totals", ""]
    lines.extend([
        f"- BRV: {manifest.total_brv}",
        f"- NRV: {manifest.total_nrv}",
        f"- PV: {manifest.total_pv}",
        f"- HCPV: {manifest.total_hcpv}",
        f"- OOIP, stb: {manifest.total_ooip_stb}",
        f"- OGIP, scf: {manifest.total_ogip_scf}",
        "",
        "## Zones",
        "",
        "| Zone | Case | Cells | BRV | NRV | PV | HCPV | OOIP stb | OGIP scf | N/G |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for item in summaries:
        lines.append(f"| {item.zone} | {item.case} | {item.cell_count} | {item.brv} | {item.nrv} | {item.pv} | {item.hcpv} | {item.ooip_stb} | {item.ogip_scf} | {item.net_gross} |")
    if manifest.warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in manifest.warnings)
    return "\n".join(lines) + "\n"


def seed_reservoir_volumetrics_workspace(root: Any = DEFAULT_PROJECTS_ROOT, project_id: str = DEFAULT_PROJECT_ID) -> dict[str, Any]:
    safe_id = safe_project_id(project_id)
    payload = _load_workspace(root, safe_id)
    if not payload.get("jobs"):
        create_reservoir_volumetrics_job(root, safe_id, job_id="base-volumetrics", name="Base Reservoir Volumetrics", case="base")
        payload = _load_workspace(root, safe_id)
    payload["last_manifest"] = manifest_to_dict(build_reservoir_volumetrics_manifest((), project_id=safe_id, job_count=len(payload.get("jobs", []))))
    _save_workspace(root, safe_id, payload)
    return payload
