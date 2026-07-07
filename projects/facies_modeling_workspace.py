from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Iterable, Sequence

from projects.project_manager import append_project_history
from projects.repository import DEFAULT_PROJECT_ID, DEFAULT_PROJECTS_ROOT, safe_project_id

FACIES_MODELING_FILE_NAME = "facies_modeling_workspace.json"

DEFAULT_FACIES_PALETTE: dict[str, str] = {
    "sand": "#f2c94c",
    "shaly_sand": "#d9b36a",
    "shale": "#7f8c8d",
    "siltstone": "#b8a07e",
    "limestone": "#d5dbdb",
    "dolomite": "#c7b8ea",
    "coal": "#2f2f2f",
    "tight_reservoir": "#b0bec5",
    "fractured_reservoir": "#80cbc4",
    "undefined": "#eeeeee",
}

FACIES_MODELING_METHODS = {
    "manual",
    "indicator_statistics",
    "vertical_proportion_curve",
    "horizontal_trend",
    "sequential_indicator_foundation",
    "object_modeling_foundation",
    "rule_based_foundation",
}

TREND_TYPES = {"none", "vertical", "horizontal", "vertical_horizontal", "map", "formula"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _project_dir(root: Any, project_id: str) -> Path:
    return Path(root) / safe_project_id(project_id)


def _workspace_path(root: Any, project_id: str) -> Path:
    return _project_dir(root, project_id) / FACIES_MODELING_FILE_NAME


def _clean_text(value: Any, label: str, *, required: bool = False, max_length: int = 180) -> str:
    text = "" if value is None else str(value).strip()
    if required and not text:
        raise ValueError(f"{label}: значение обязательно.")
    if len(text) > max_length:
        raise ValueError(f"{label}: максимум {max_length} символов.")
    return text


def _clean_facies_code(value: Any) -> str:
    code = _clean_text(value, "Код фации", required=True, max_length=80).lower().replace(" ", "_")
    if not code.replace("_", "").replace("-", "").isalnum():
        raise ValueError("Код фации должен содержать буквы, цифры, '-' или '_'.")
    return code


def _clean_method(value: Any) -> str:
    method = _clean_text(value, "Метод моделирования", required=True, max_length=80).lower()
    if method not in FACIES_MODELING_METHODS:
        raise ValueError(f"Метод должен быть одним из: {', '.join(sorted(FACIES_MODELING_METHODS))}.")
    return method


def _clean_trend_type(value: Any) -> str:
    trend = _clean_text(value, "Тип тренда", max_length=80).lower() or "none"
    if trend not in TREND_TYPES:
        raise ValueError(f"Тип тренда должен быть одним из: {', '.join(sorted(TREND_TYPES))}.")
    return trend


def _to_float(value: Any, label: str, *, required: bool = False) -> float | None:
    if value is None:
        if required:
            raise ValueError(f"{label}: значение обязательно.")
        return None
    if isinstance(value, str):
        value = value.strip().replace(",", ".")
        if not value:
            if required:
                raise ValueError(f"{label}: значение обязательно.")
            return None
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
class FaciesDefinition:
    code: str
    name: str
    category: str = "reservoir"
    color: str = "#eeeeee"
    description: str = ""
    priority: int = 100
    is_reservoir: bool = False
    is_pay_candidate: bool = False


@dataclass(frozen=True)
class FaciesZoneSettings:
    zone_name: str
    top_depth: float | None = None
    base_depth: float | None = None
    allowed_facies: tuple[str, ...] = ()
    modeling_method: str = "indicator_statistics"
    trend_type: str = "none"
    horizontal_trend: str = ""
    vertical_trend: str = ""
    min_thickness: float | None = None
    max_thickness: float | None = None
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FaciesStatistics:
    facies_code: str
    sample_count: int
    proportion: float
    min_run: int
    max_run: int
    mean_run: float


@dataclass(frozen=True)
class VerticalProportionLayer:
    layer_index: int
    top_depth: float | None
    base_depth: float | None
    sample_count: int
    proportions: dict[str, float]


@dataclass(frozen=True)
class FaciesSimulationJob:
    name: str
    zone_name: str
    method: str
    input_property: str = "Facies"
    output_property: str = "Facies_model"
    parameters: dict[str, Any] = field(default_factory=dict)
    status: str = "planned"
    created_at: str = ""
    author: str = ""


@dataclass(frozen=True)
class FaciesModelingManifest:
    project_id: str
    generated_at: str
    facies_count: int
    zone_count: int
    job_count: int
    reservoir_facies_count: int
    warnings: tuple[str, ...] = ()


def _definition_to_dict(item: FaciesDefinition) -> dict[str, Any]:
    return {
        "code": item.code,
        "name": item.name,
        "category": item.category,
        "color": item.color,
        "description": item.description,
        "priority": int(item.priority),
        "is_reservoir": bool(item.is_reservoir),
        "is_pay_candidate": bool(item.is_pay_candidate),
    }


def _definition_from_dict(raw: dict[str, Any]) -> FaciesDefinition:
    return FaciesDefinition(
        code=_clean_facies_code(raw.get("code")),
        name=_clean_text(raw.get("name"), "Название фации", required=True),
        category=_clean_text(raw.get("category"), "Категория", max_length=80) or "reservoir",
        color=_clean_text(raw.get("color"), "Цвет", max_length=40) or DEFAULT_FACIES_PALETTE.get(_clean_facies_code(raw.get("code")), "#eeeeee"),
        description=_clean_text(raw.get("description"), "Описание", max_length=600),
        priority=int(_to_float(raw.get("priority", 100), "Приоритет", required=True) or 100),
        is_reservoir=bool(raw.get("is_reservoir", False)),
        is_pay_candidate=bool(raw.get("is_pay_candidate", False)),
    )


def _zone_to_dict(item: FaciesZoneSettings) -> dict[str, Any]:
    return {
        "zone_name": item.zone_name,
        "top_depth": item.top_depth,
        "base_depth": item.base_depth,
        "allowed_facies": list(item.allowed_facies),
        "modeling_method": item.modeling_method,
        "trend_type": item.trend_type,
        "horizontal_trend": item.horizontal_trend,
        "vertical_trend": item.vertical_trend,
        "min_thickness": item.min_thickness,
        "max_thickness": item.max_thickness,
        "parameters": dict(item.parameters),
    }


def _zone_from_dict(raw: dict[str, Any]) -> FaciesZoneSettings:
    allowed_raw = raw.get("allowed_facies") if isinstance(raw.get("allowed_facies"), list) else []
    top = _to_float(raw.get("top_depth"), "Кровля зоны")
    base = _to_float(raw.get("base_depth"), "Подошва зоны")
    if top is not None and base is not None and base <= top:
        raise ValueError("Подошва зоны должна быть глубже кровли.")
    return FaciesZoneSettings(
        zone_name=_clean_text(raw.get("zone_name"), "Название зоны", required=True),
        top_depth=top,
        base_depth=base,
        allowed_facies=tuple(_clean_facies_code(value) for value in allowed_raw),
        modeling_method=_clean_method(raw.get("modeling_method") or "indicator_statistics"),
        trend_type=_clean_trend_type(raw.get("trend_type") or "none"),
        horizontal_trend=_clean_text(raw.get("horizontal_trend"), "Горизонтальный тренд", max_length=260),
        vertical_trend=_clean_text(raw.get("vertical_trend"), "Вертикальный тренд", max_length=260),
        min_thickness=_to_float(raw.get("min_thickness"), "Минимальная мощность"),
        max_thickness=_to_float(raw.get("max_thickness"), "Максимальная мощность"),
        parameters=raw.get("parameters") if isinstance(raw.get("parameters"), dict) else {},
    )


def _job_to_dict(item: FaciesSimulationJob) -> dict[str, Any]:
    return {
        "name": item.name,
        "zone_name": item.zone_name,
        "method": item.method,
        "input_property": item.input_property,
        "output_property": item.output_property,
        "parameters": dict(item.parameters),
        "status": item.status,
        "created_at": item.created_at,
        "author": item.author,
    }


def _job_from_dict(raw: dict[str, Any]) -> FaciesSimulationJob:
    return FaciesSimulationJob(
        name=_clean_text(raw.get("name"), "Название задания", required=True),
        zone_name=_clean_text(raw.get("zone_name"), "Зона", required=True),
        method=_clean_method(raw.get("method") or "indicator_statistics"),
        input_property=_clean_text(raw.get("input_property"), "Входное свойство", max_length=120) or "Facies",
        output_property=_clean_text(raw.get("output_property"), "Выходное свойство", max_length=120) or "Facies_model",
        parameters=raw.get("parameters") if isinstance(raw.get("parameters"), dict) else {},
        status=_clean_text(raw.get("status"), "Статус", max_length=60) or "planned",
        created_at=_clean_text(raw.get("created_at"), "Дата", max_length=80),
        author=_clean_text(raw.get("author"), "Автор", max_length=120),
    )


def load_facies_modeling_workspace(root=DEFAULT_PROJECTS_ROOT, project_id: str = DEFAULT_PROJECT_ID) -> dict[str, Any]:
    default = {"facies": [], "zones": [], "simulation_jobs": [], "history": []}
    payload = _json_read(_workspace_path(root, project_id), default)
    if not isinstance(payload, dict):
        return default
    for key in default:
        if not isinstance(payload.get(key), list):
            payload[key] = []
    return payload


def list_facies_definitions(root=DEFAULT_PROJECTS_ROOT, project_id: str = DEFAULT_PROJECT_ID) -> tuple[FaciesDefinition, ...]:
    payload = load_facies_modeling_workspace(root, project_id)
    items: list[FaciesDefinition] = []
    for raw in payload.get("facies", []):
        if isinstance(raw, dict):
            try:
                items.append(_definition_from_dict(raw))
            except ValueError:
                continue
    return tuple(sorted(items, key=lambda item: (item.priority, item.code)))


def save_facies_definition(root, project_id: str, definition: FaciesDefinition | dict[str, Any], *, replace: bool = True) -> FaciesDefinition:
    normalized = _definition_from_dict(_definition_to_dict(definition) if isinstance(definition, FaciesDefinition) else definition)
    payload = load_facies_modeling_workspace(root, project_id)
    rows = payload.get("facies", [])
    exists = any(isinstance(row, dict) and str(row.get("code", "")).strip().lower() == normalized.code for row in rows)
    if exists and not replace:
        raise ValueError(f"Фация '{normalized.code}' уже существует.")
    rows = [row for row in rows if not (isinstance(row, dict) and str(row.get("code", "")).strip().lower() == normalized.code)]
    rows.append(_definition_to_dict(normalized))
    payload["facies"] = rows
    payload.setdefault("history", []).append({"event": "save_facies_definition", "code": normalized.code, "at": _now_iso()})
    _json_write(_workspace_path(root, project_id), payload)
    append_project_history(root, project_id, "facies_modeling.save_definition", f"Saved facies definition: {normalized.code}")
    return normalized


def list_facies_zones(root=DEFAULT_PROJECTS_ROOT, project_id: str = DEFAULT_PROJECT_ID) -> tuple[FaciesZoneSettings, ...]:
    payload = load_facies_modeling_workspace(root, project_id)
    zones: list[FaciesZoneSettings] = []
    for raw in payload.get("zones", []):
        if isinstance(raw, dict):
            try:
                zones.append(_zone_from_dict(raw))
            except ValueError:
                continue
    return tuple(sorted(zones, key=lambda item: (item.top_depth if item.top_depth is not None else 1e30, item.zone_name.lower())))


def save_facies_zone(root, project_id: str, zone: FaciesZoneSettings | dict[str, Any], *, replace: bool = True) -> FaciesZoneSettings:
    normalized = _zone_from_dict(_zone_to_dict(zone) if isinstance(zone, FaciesZoneSettings) else zone)
    payload = load_facies_modeling_workspace(root, project_id)
    rows = payload.get("zones", [])
    exists = any(isinstance(row, dict) and str(row.get("zone_name", "")).strip().lower() == normalized.zone_name.lower() for row in rows)
    if exists and not replace:
        raise ValueError(f"Зона '{normalized.zone_name}' уже существует.")
    rows = [row for row in rows if not (isinstance(row, dict) and str(row.get("zone_name", "")).strip().lower() == normalized.zone_name.lower())]
    rows.append(_zone_to_dict(normalized))
    payload["zones"] = rows
    payload.setdefault("history", []).append({"event": "save_facies_zone", "zone": normalized.zone_name, "at": _now_iso()})
    _json_write(_workspace_path(root, project_id), payload)
    append_project_history(root, project_id, "facies_modeling.save_zone", f"Saved facies zone: {normalized.zone_name}")
    return normalized


def list_facies_simulation_jobs(root=DEFAULT_PROJECTS_ROOT, project_id: str = DEFAULT_PROJECT_ID) -> tuple[FaciesSimulationJob, ...]:
    payload = load_facies_modeling_workspace(root, project_id)
    jobs: list[FaciesSimulationJob] = []
    for raw in payload.get("simulation_jobs", []):
        if isinstance(raw, dict):
            try:
                jobs.append(_job_from_dict(raw))
            except ValueError:
                continue
    return tuple(sorted(jobs, key=lambda item: (item.zone_name.lower(), item.name.lower())))


def save_facies_simulation_job(root, project_id: str, job: FaciesSimulationJob | dict[str, Any], *, replace: bool = True) -> FaciesSimulationJob:
    normalized = _job_from_dict(_job_to_dict(job) if isinstance(job, FaciesSimulationJob) else job)
    if not normalized.created_at:
        normalized = FaciesSimulationJob(**{**_job_to_dict(normalized), "created_at": _now_iso()})
    payload = load_facies_modeling_workspace(root, project_id)
    rows = payload.get("simulation_jobs", [])
    exists = any(isinstance(row, dict) and str(row.get("name", "")).strip().lower() == normalized.name.lower() for row in rows)
    if exists and not replace:
        raise ValueError(f"Задание '{normalized.name}' уже существует.")
    rows = [row for row in rows if not (isinstance(row, dict) and str(row.get("name", "")).strip().lower() == normalized.name.lower())]
    rows.append(_job_to_dict(normalized))
    payload["simulation_jobs"] = rows
    payload.setdefault("history", []).append({"event": "save_facies_simulation_job", "name": normalized.name, "at": _now_iso()})
    _json_write(_workspace_path(root, project_id), payload)
    append_project_history(root, project_id, "facies_modeling.save_job", f"Saved facies simulation job: {normalized.name}")
    return normalized


def normalize_facies_values(values: Sequence[Any]) -> tuple[str, ...]:
    result: list[str] = []
    for value in values:
        text = str(value).strip().lower().replace(" ", "_") if value is not None else "undefined"
        result.append(text or "undefined")
    return tuple(result)


def _run_lengths(values: Sequence[str], code: str) -> list[int]:
    runs: list[int] = []
    current = 0
    for value in values:
        if value == code:
            current += 1
        elif current:
            runs.append(current)
            current = 0
    if current:
        runs.append(current)
    return runs


def calculate_facies_statistics(values: Sequence[Any]) -> tuple[FaciesStatistics, ...]:
    normalized = normalize_facies_values(values)
    total = len(normalized)
    if total == 0:
        return ()
    rows: list[FaciesStatistics] = []
    for code in sorted(set(normalized)):
        count = normalized.count(code)
        runs = _run_lengths(normalized, code)
        rows.append(
            FaciesStatistics(
                facies_code=code,
                sample_count=count,
                proportion=round(count / total, 6),
                min_run=min(runs) if runs else 0,
                max_run=max(runs) if runs else 0,
                mean_run=round(mean(runs), 6) if runs else 0.0,
            )
        )
    return tuple(rows)


def build_vertical_proportion_curves(
    depths: Sequence[Any],
    facies_values: Sequence[Any],
    *,
    layer_count: int = 10,
) -> tuple[VerticalProportionLayer, ...]:
    if len(depths) != len(facies_values):
        raise ValueError("Количество глубин должно совпадать с количеством значений фаций.")
    if layer_count <= 0:
        raise ValueError("Количество слоев должно быть положительным.")
    pairs: list[tuple[float, str]] = []
    for depth, facies in zip(depths, facies_values):
        depth_value = _to_float(depth, "Глубина")
        if depth_value is not None:
            pairs.append((depth_value, normalize_facies_values([facies])[0]))
    if not pairs:
        return ()
    pairs.sort(key=lambda item: item[0])
    top = pairs[0][0]
    base = pairs[-1][0]
    if top == base:
        layer_count = 1
    step = (base - top) / layer_count if layer_count > 1 else 1.0
    layers: list[VerticalProportionLayer] = []
    all_codes = sorted({facies for _, facies in pairs})
    for index in range(layer_count):
        layer_top = top + step * index if layer_count > 1 else top
        layer_base = top + step * (index + 1) if layer_count > 1 else base
        if index == layer_count - 1:
            rows = [facies for depth, facies in pairs if layer_top <= depth <= layer_base]
        else:
            rows = [facies for depth, facies in pairs if layer_top <= depth < layer_base]
        sample_count = len(rows)
        proportions = {code: round(rows.count(code) / sample_count, 6) if sample_count else 0.0 for code in all_codes}
        layers.append(VerticalProportionLayer(index + 1, round(layer_top, 6), round(layer_base, 6), sample_count, proportions))
    return tuple(layers)


def build_facies_statistics_table(statistics: Iterable[FaciesStatistics]) -> list[dict[str, Any]]:
    return [
        {
            "facies": item.facies_code,
            "samples": item.sample_count,
            "proportion_pct": round(item.proportion * 100, 3),
            "min_run": item.min_run,
            "max_run": item.max_run,
            "mean_run": item.mean_run,
        }
        for item in statistics
    ]


def build_vertical_proportion_table(layers: Iterable[VerticalProportionLayer]) -> list[dict[str, Any]]:
    table: list[dict[str, Any]] = []
    for layer in layers:
        row: dict[str, Any] = {
            "layer": layer.layer_index,
            "top_depth": layer.top_depth,
            "base_depth": layer.base_depth,
            "samples": layer.sample_count,
        }
        for code, value in layer.proportions.items():
            row[f"{code}_pct"] = round(value * 100, 3)
        table.append(row)
    return table


def build_default_facies_modeling_seed(author: str = "") -> dict[str, Any]:
    definitions = [
        FaciesDefinition("sand", "Sand", "reservoir", DEFAULT_FACIES_PALETTE["sand"], "Clean reservoir sand.", 10, True, True),
        FaciesDefinition("shaly_sand", "Shaly Sand", "reservoir", DEFAULT_FACIES_PALETTE["shaly_sand"], "Reservoir sand with shale content.", 20, True, True),
        FaciesDefinition("shale", "Shale", "non_reservoir", DEFAULT_FACIES_PALETTE["shale"], "Seal or non-reservoir shale.", 30, False, False),
        FaciesDefinition("siltstone", "Siltstone", "mixed", DEFAULT_FACIES_PALETTE["siltstone"], "Fine-grained mixed facies.", 40, False, False),
        FaciesDefinition("limestone", "Limestone", "carbonate", DEFAULT_FACIES_PALETTE["limestone"], "Carbonate facies foundation.", 50, True, False),
        FaciesDefinition("dolomite", "Dolomite", "carbonate", DEFAULT_FACIES_PALETTE["dolomite"], "Dolomite facies foundation.", 60, True, False),
        FaciesDefinition("coal", "Coal", "non_reservoir", DEFAULT_FACIES_PALETTE["coal"], "Coal layer.", 70, False, False),
        FaciesDefinition("undefined", "Undefined", "unknown", DEFAULT_FACIES_PALETTE["undefined"], "Unclassified facies.", 999, False, False),
    ]
    zones = [
        FaciesZoneSettings("Zone-1", allowed_facies=("sand", "shaly_sand", "shale"), modeling_method="vertical_proportion_curve", trend_type="vertical_horizontal", min_thickness=0.2),
        FaciesZoneSettings("Zone-2", allowed_facies=("sand", "shale", "siltstone"), modeling_method="indicator_statistics", trend_type="vertical", min_thickness=0.2),
    ]
    jobs = [
        FaciesSimulationJob("Facies foundation job", "Zone-1", "vertical_proportion_curve", parameters={"source": "upscaled_well_logs"}, status="planned", created_at=_now_iso(), author=author)
    ]
    return {
        "facies": [_definition_to_dict(item) for item in definitions],
        "zones": [_zone_to_dict(item) for item in zones],
        "simulation_jobs": [_job_to_dict(item) for item in jobs],
        "history": [{"event": "seed_facies_modeling_workspace", "at": _now_iso()}],
    }


def seed_facies_modeling_workspace(root, project_id: str, *, author: str = "", overwrite: bool = False) -> dict[str, Any]:
    path = _workspace_path(root, project_id)
    if path.exists() and not overwrite:
        return load_facies_modeling_workspace(root, project_id)
    payload = build_default_facies_modeling_seed(author=author)
    _json_write(path, payload)
    append_project_history(root, project_id, "facies_modeling.seed", "Seeded facies modeling workspace")
    return payload


def build_facies_modeling_manifest(root=DEFAULT_PROJECTS_ROOT, project_id: str = DEFAULT_PROJECT_ID) -> FaciesModelingManifest:
    definitions = list_facies_definitions(root, project_id)
    zones = list_facies_zones(root, project_id)
    jobs = list_facies_simulation_jobs(root, project_id)
    warnings: list[str] = []
    if not definitions:
        warnings.append("Не задан реестр фаций.")
    if not zones:
        warnings.append("Не заданы зоны фациального моделирования.")
    if definitions and not any(item.is_reservoir for item in definitions):
        warnings.append("В реестре нет reservoir facies.")
    return FaciesModelingManifest(
        project_id=safe_project_id(project_id),
        generated_at=_now_iso(),
        facies_count=len(definitions),
        zone_count=len(zones),
        job_count=len(jobs),
        reservoir_facies_count=sum(1 for item in definitions if item.is_reservoir),
        warnings=tuple(warnings),
    )


def build_facies_definition_table(definitions: Iterable[FaciesDefinition]) -> list[dict[str, Any]]:
    return [
        {
            "code": item.code,
            "name": item.name,
            "category": item.category,
            "color": item.color,
            "priority": item.priority,
            "reservoir": item.is_reservoir,
            "pay_candidate": item.is_pay_candidate,
        }
        for item in definitions
    ]


def build_facies_zone_table(zones: Iterable[FaciesZoneSettings]) -> list[dict[str, Any]]:
    return [
        {
            "zone": item.zone_name,
            "top_depth": item.top_depth,
            "base_depth": item.base_depth,
            "allowed_facies": ", ".join(item.allowed_facies),
            "method": item.modeling_method,
            "trend": item.trend_type,
            "horizontal_trend": item.horizontal_trend,
            "vertical_trend": item.vertical_trend,
        }
        for item in zones
    ]


def render_facies_modeling_markdown(root=DEFAULT_PROJECTS_ROOT, project_id: str = DEFAULT_PROJECT_ID) -> str:
    definitions = list_facies_definitions(root, project_id)
    zones = list_facies_zones(root, project_id)
    jobs = list_facies_simulation_jobs(root, project_id)
    manifest = build_facies_modeling_manifest(root, project_id)
    lines = [
        "# Facies Modeling Workspace Report",
        "",
        f"Project: `{manifest.project_id}`",
        f"Generated: `{manifest.generated_at}`",
        "",
        "## Summary",
        f"- Facies definitions: {manifest.facies_count}",
        f"- Modeling zones: {manifest.zone_count}",
        f"- Simulation jobs: {manifest.job_count}",
        f"- Reservoir facies: {manifest.reservoir_facies_count}",
        "",
        "## Facies Registry",
        "| Code | Name | Category | Reservoir | Pay candidate | Priority |",
        "|---|---|---|---|---|---|",
    ]
    for item in definitions:
        lines.append(f"| {item.code} | {item.name} | {item.category} | {item.is_reservoir} | {item.is_pay_candidate} | {item.priority} |")
    lines.extend(["", "## Modeling Zones", "| Zone | Top | Base | Allowed facies | Method | Trend |", "|---|---|---|---|---|---|"])
    for zone in zones:
        lines.append(f"| {zone.zone_name} | {zone.top_depth} | {zone.base_depth} | {', '.join(zone.allowed_facies)} | {zone.modeling_method} | {zone.trend_type} |")
    lines.extend(["", "## Simulation Jobs", "| Name | Zone | Method | Input | Output | Status |", "|---|---|---|---|---|---|"])
    for job in jobs:
        lines.append(f"| {job.name} | {job.zone_name} | {job.method} | {job.input_property} | {job.output_property} | {job.status} |")
    if manifest.warnings:
        lines.extend(["", "## Warnings"])
        lines.extend(f"- {warning}" for warning in manifest.warnings)
    lines.extend([
        "",
        "## References",
        "- docs/sources/lab-4-property-cubes.pdf — методические основы фациального моделирования, VPC, трендов и кубов свойств.",
    ])
    return "\n".join(lines) + "\n"
