from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

from projects.project_manager import append_project_history
from projects.repository import DEFAULT_PROJECT_ID, DEFAULT_PROJECTS_ROOT, safe_project_id

GEOSTATISTICS_FILE_NAME = "geostatistics_workspace.json"

VARIOGRAM_MODELS = {"spherical", "exponential", "gaussian", "linear", "nugget"}
VARIOGRAM_DIRECTIONS = {"omnidirectional", "azimuthal", "vertical", "horizontal"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _project_dir(root: Any, project_id: str) -> Path:
    return Path(root) / safe_project_id(project_id)


def _workspace_path(root: Any, project_id: str) -> Path:
    return _project_dir(root, project_id) / GEOSTATISTICS_FILE_NAME


def _clean_text(value: Any, label: str, *, required: bool = False, max_length: int = 180) -> str:
    text = "" if value is None else str(value).strip()
    if required and not text:
        raise ValueError(f"{label}: значение обязательно.")
    if len(text) > max_length:
        raise ValueError(f"{label}: максимум {max_length} символов.")
    return text


def _to_float(value: Any, label: str, *, required: bool = False, minimum: float | None = None) -> float | None:
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
    if not math.isfinite(number):
        raise ValueError(f"{label}: значение должно быть конечным числом.")
    if minimum is not None and number < minimum:
        raise ValueError(f"{label}: значение должно быть не меньше {minimum}.")
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
class SpatialSample:
    x: float
    y: float
    value: float
    z: float | None = None
    well: str = ""
    zone: str = ""


@dataclass(frozen=True)
class VariogramBin:
    lag_index: int
    lag_center: float
    lag_min: float
    lag_max: float
    pair_count: int
    gamma: float
    mean_distance: float


@dataclass(frozen=True)
class VariogramModelSpec:
    name: str
    model_type: str = "spherical"
    nugget: float = 0.0
    sill: float = 1.0
    range_major: float = 1000.0
    range_minor: float | None = None
    range_vertical: float | None = None
    azimuth: float = 0.0
    dip: float = 0.0
    property_name: str = ""
    zone_name: str = ""
    created_at: str = ""
    author: str = ""
    source: str = "experimental_variogram"
    fit_score: float | None = None


@dataclass(frozen=True)
class SearchEllipsoidSpec:
    name: str
    radius_major: float
    radius_minor: float
    radius_vertical: float
    azimuth: float = 0.0
    dip: float = 0.0
    min_neighbors: int = 1
    max_neighbors: int = 16
    sector_count: int = 1
    description: str = ""


@dataclass(frozen=True)
class GeostatisticsJob:
    name: str
    property_name: str
    zone_name: str = ""
    algorithm: str = "experimental_variogram"
    model_name: str = ""
    search_ellipsoid: str = ""
    status: str = "planned"
    parameters: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    author: str = ""


@dataclass(frozen=True)
class GeostatisticsManifest:
    project_id: str
    generated_at: str
    model_count: int
    ellipsoid_count: int
    job_count: int
    warnings: tuple[str, ...] = ()


def _sample_from_dict(raw: dict[str, Any]) -> SpatialSample:
    return SpatialSample(
        x=_to_float(raw.get("x"), "X", required=True) or 0.0,
        y=_to_float(raw.get("y"), "Y", required=True) or 0.0,
        z=_to_float(raw.get("z"), "Z"),
        value=_to_float(raw.get("value"), "Значение", required=True) or 0.0,
        well=_clean_text(raw.get("well"), "Скважина", max_length=120),
        zone=_clean_text(raw.get("zone"), "Зона", max_length=120),
    )


def normalize_spatial_samples(samples: Iterable[SpatialSample | dict[str, Any] | Sequence[Any]]) -> tuple[SpatialSample, ...]:
    result: list[SpatialSample] = []
    for row in samples:
        if isinstance(row, SpatialSample):
            sample = row
        elif isinstance(row, dict):
            sample = _sample_from_dict(row)
        else:
            values = list(row)
            if len(values) < 3:
                raise ValueError("Каждый sample должен содержать минимум X, Y и value.")
            sample = SpatialSample(
                x=_to_float(values[0], "X", required=True) or 0.0,
                y=_to_float(values[1], "Y", required=True) or 0.0,
                value=_to_float(values[2], "Значение", required=True) or 0.0,
                z=_to_float(values[3], "Z") if len(values) > 3 else None,
            )
        result.append(sample)
    if len(result) < 2:
        raise ValueError("Для геостатистики требуется минимум две точки.")
    return tuple(result)


def _distance(a: SpatialSample, b: SpatialSample, *, use_z: bool = False) -> float:
    dz = ((a.z or 0.0) - (b.z or 0.0)) if use_z and a.z is not None and b.z is not None else 0.0
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + dz**2)


def calculate_experimental_variogram(
    samples: Iterable[SpatialSample | dict[str, Any] | Sequence[Any]],
    *,
    lag_size: float,
    max_lag: float | None = None,
    use_z: bool = False,
) -> tuple[VariogramBin, ...]:
    normalized = normalize_spatial_samples(samples)
    lag_size = _to_float(lag_size, "Размер лага", required=True, minimum=0.000001) or 1.0
    pairs: list[tuple[float, float]] = []
    for index, left in enumerate(normalized):
        for right in normalized[index + 1 :]:
            distance = _distance(left, right, use_z=use_z)
            gamma = 0.5 * (left.value - right.value) ** 2
            pairs.append((distance, gamma))
    if not pairs:
        return ()
    effective_max_lag = _to_float(max_lag, "Максимальный лаг") if max_lag is not None else max(distance for distance, _ in pairs)
    if effective_max_lag is None or effective_max_lag <= 0:
        effective_max_lag = max(distance for distance, _ in pairs)
    bin_count = max(1, int(math.ceil(effective_max_lag / lag_size)))
    bins: list[VariogramBin] = []
    for lag_index in range(bin_count):
        lag_min = lag_index * lag_size
        lag_max = lag_min + lag_size
        selected = [(distance, gamma) for distance, gamma in pairs if lag_min < distance <= lag_max]
        if not selected:
            continue
        pair_count = len(selected)
        bins.append(
            VariogramBin(
                lag_index=lag_index + 1,
                lag_center=round((lag_min + lag_max) / 2.0, 10),
                lag_min=round(lag_min, 10),
                lag_max=round(lag_max, 10),
                pair_count=pair_count,
                gamma=round(sum(gamma for _, gamma in selected) / pair_count, 10),
                mean_distance=round(sum(distance for distance, _ in selected) / pair_count, 10),
            )
        )
    return tuple(bins)


def evaluate_variogram_model(distance: float, model: VariogramModelSpec | dict[str, Any]) -> float:
    spec = _model_from_dict(model) if isinstance(model, dict) else model
    h = max(0.0, float(distance))
    nugget = max(0.0, spec.nugget)
    sill = max(nugget, spec.sill)
    partial_sill = max(0.0, sill - nugget)
    range_major = max(0.000001, spec.range_major)
    ratio = h / range_major
    if spec.model_type == "nugget":
        return round(sill if h > 0 else nugget, 10)
    if spec.model_type == "linear":
        return round(min(sill, nugget + partial_sill * ratio), 10)
    if spec.model_type == "exponential":
        return round(nugget + partial_sill * (1.0 - math.exp(-3.0 * ratio)), 10)
    if spec.model_type == "gaussian":
        return round(nugget + partial_sill * (1.0 - math.exp(-3.0 * ratio * ratio)), 10)
    # spherical
    if ratio >= 1.0:
        return round(sill, 10)
    return round(nugget + partial_sill * (1.5 * ratio - 0.5 * ratio**3), 10)


def fit_variogram_model(
    bins: Iterable[VariogramBin | dict[str, Any]],
    *,
    name: str = "Fitted Variogram",
    model_type: str = "spherical",
    property_name: str = "",
    zone_name: str = "",
    author: str = "",
) -> VariogramModelSpec:
    rows = tuple(_bin_from_dict(row) if isinstance(row, dict) else row for row in bins)
    if not rows:
        raise ValueError("Для подбора модели нужны экспериментальные лаги.")
    model_type = _clean_model_type(model_type)
    max_gamma = max(row.gamma for row in rows)
    min_gamma = min(row.gamma for row in rows)
    max_distance = max(row.mean_distance for row in rows)
    nugget_candidates = [0.0, min_gamma * 0.25, min_gamma * 0.5]
    sill_candidates = [max_gamma, max_gamma * 1.15, max_gamma * 1.35]
    range_candidates = [max_distance * 0.5, max_distance, max_distance * 1.5, max_distance * 2.0]
    best: tuple[float, float, float, float] | None = None
    for nugget in nugget_candidates:
        for sill in sill_candidates:
            if sill < nugget:
                continue
            for range_major in range_candidates:
                candidate = VariogramModelSpec(name=name, model_type=model_type, nugget=nugget, sill=sill, range_major=max(range_major, 0.000001))
                sse = sum((evaluate_variogram_model(row.mean_distance, candidate) - row.gamma) ** 2 for row in rows)
                weighted = sse / max(1, sum(row.pair_count for row in rows))
                if best is None or weighted < best[0]:
                    best = (weighted, nugget, sill, max(range_major, 0.000001))
    assert best is not None
    score, nugget, sill, range_major = best
    return VariogramModelSpec(
        name=_clean_text(name, "Название модели", required=True),
        model_type=model_type,
        nugget=round(nugget, 10),
        sill=round(sill, 10),
        range_major=round(range_major, 10),
        property_name=_clean_text(property_name, "Свойство", max_length=120),
        zone_name=_clean_text(zone_name, "Зона", max_length=120),
        created_at=_now_iso(),
        author=_clean_text(author, "Автор", max_length=120),
        fit_score=round(score, 10),
    )


def _clean_model_type(value: Any) -> str:
    model_type = _clean_text(value, "Тип вариограммы", required=True, max_length=80).lower()
    if model_type not in VARIOGRAM_MODELS:
        raise ValueError(f"Тип вариограммы должен быть одним из: {', '.join(sorted(VARIOGRAM_MODELS))}.")
    return model_type


def _model_to_dict(item: VariogramModelSpec) -> dict[str, Any]:
    return {
        "name": item.name,
        "model_type": item.model_type,
        "nugget": item.nugget,
        "sill": item.sill,
        "range_major": item.range_major,
        "range_minor": item.range_minor,
        "range_vertical": item.range_vertical,
        "azimuth": item.azimuth,
        "dip": item.dip,
        "property_name": item.property_name,
        "zone_name": item.zone_name,
        "created_at": item.created_at,
        "author": item.author,
        "source": item.source,
        "fit_score": item.fit_score,
    }


def _model_from_dict(raw: dict[str, Any]) -> VariogramModelSpec:
    return VariogramModelSpec(
        name=_clean_text(raw.get("name"), "Название модели", required=True),
        model_type=_clean_model_type(raw.get("model_type", "spherical")),
        nugget=_to_float(raw.get("nugget", 0.0), "Nugget", required=True, minimum=0.0) or 0.0,
        sill=_to_float(raw.get("sill", 1.0), "Sill", required=True, minimum=0.0) or 1.0,
        range_major=_to_float(raw.get("range_major", 1000.0), "Major range", required=True, minimum=0.000001) or 1000.0,
        range_minor=_to_float(raw.get("range_minor"), "Minor range", minimum=0.000001),
        range_vertical=_to_float(raw.get("range_vertical"), "Vertical range", minimum=0.000001),
        azimuth=_to_float(raw.get("azimuth", 0.0), "Azimuth", required=True) or 0.0,
        dip=_to_float(raw.get("dip", 0.0), "Dip", required=True) or 0.0,
        property_name=_clean_text(raw.get("property_name"), "Свойство", max_length=120),
        zone_name=_clean_text(raw.get("zone_name"), "Зона", max_length=120),
        created_at=_clean_text(raw.get("created_at"), "Дата", max_length=80),
        author=_clean_text(raw.get("author"), "Автор", max_length=120),
        source=_clean_text(raw.get("source"), "Источник", max_length=120) or "experimental_variogram",
        fit_score=_to_float(raw.get("fit_score"), "Fit score", minimum=0.0),
    )


def _bin_to_dict(item: VariogramBin) -> dict[str, Any]:
    return {
        "lag_index": item.lag_index,
        "lag_center": item.lag_center,
        "lag_min": item.lag_min,
        "lag_max": item.lag_max,
        "pair_count": item.pair_count,
        "gamma": item.gamma,
        "mean_distance": item.mean_distance,
    }


def _bin_from_dict(raw: dict[str, Any]) -> VariogramBin:
    return VariogramBin(
        lag_index=int(_to_float(raw.get("lag_index"), "Lag index", required=True, minimum=1) or 1),
        lag_center=_to_float(raw.get("lag_center"), "Lag center", required=True, minimum=0.0) or 0.0,
        lag_min=_to_float(raw.get("lag_min"), "Lag min", required=True, minimum=0.0) or 0.0,
        lag_max=_to_float(raw.get("lag_max"), "Lag max", required=True, minimum=0.0) or 0.0,
        pair_count=int(_to_float(raw.get("pair_count"), "Pair count", required=True, minimum=1) or 1),
        gamma=_to_float(raw.get("gamma"), "Gamma", required=True, minimum=0.0) or 0.0,
        mean_distance=_to_float(raw.get("mean_distance"), "Mean distance", required=True, minimum=0.0) or 0.0,
    )


def _ellipsoid_to_dict(item: SearchEllipsoidSpec) -> dict[str, Any]:
    return {
        "name": item.name,
        "radius_major": item.radius_major,
        "radius_minor": item.radius_minor,
        "radius_vertical": item.radius_vertical,
        "azimuth": item.azimuth,
        "dip": item.dip,
        "min_neighbors": item.min_neighbors,
        "max_neighbors": item.max_neighbors,
        "sector_count": item.sector_count,
        "description": item.description,
    }


def _ellipsoid_from_dict(raw: dict[str, Any]) -> SearchEllipsoidSpec:
    min_neighbors = int(_to_float(raw.get("min_neighbors", 1), "Min neighbors", required=True, minimum=0) or 1)
    max_neighbors = int(_to_float(raw.get("max_neighbors", 16), "Max neighbors", required=True, minimum=1) or 16)
    if max_neighbors < min_neighbors:
        raise ValueError("Max neighbors не может быть меньше min neighbors.")
    return SearchEllipsoidSpec(
        name=_clean_text(raw.get("name"), "Название эллипсоида", required=True),
        radius_major=_to_float(raw.get("radius_major"), "Major radius", required=True, minimum=0.000001) or 1.0,
        radius_minor=_to_float(raw.get("radius_minor"), "Minor radius", required=True, minimum=0.000001) or 1.0,
        radius_vertical=_to_float(raw.get("radius_vertical"), "Vertical radius", required=True, minimum=0.000001) or 1.0,
        azimuth=_to_float(raw.get("azimuth", 0.0), "Azimuth", required=True) or 0.0,
        dip=_to_float(raw.get("dip", 0.0), "Dip", required=True) or 0.0,
        min_neighbors=min_neighbors,
        max_neighbors=max_neighbors,
        sector_count=int(_to_float(raw.get("sector_count", 1), "Sector count", required=True, minimum=1) or 1),
        description=_clean_text(raw.get("description"), "Описание", max_length=600),
    )


def _job_to_dict(item: GeostatisticsJob) -> dict[str, Any]:
    return {
        "name": item.name,
        "property_name": item.property_name,
        "zone_name": item.zone_name,
        "algorithm": item.algorithm,
        "model_name": item.model_name,
        "search_ellipsoid": item.search_ellipsoid,
        "status": item.status,
        "parameters": dict(item.parameters),
        "created_at": item.created_at,
        "author": item.author,
    }


def _job_from_dict(raw: dict[str, Any]) -> GeostatisticsJob:
    return GeostatisticsJob(
        name=_clean_text(raw.get("name"), "Название задания", required=True),
        property_name=_clean_text(raw.get("property_name"), "Свойство", required=True),
        zone_name=_clean_text(raw.get("zone_name"), "Зона", max_length=120),
        algorithm=_clean_text(raw.get("algorithm", "experimental_variogram"), "Алгоритм", required=True),
        model_name=_clean_text(raw.get("model_name"), "Модель", max_length=120),
        search_ellipsoid=_clean_text(raw.get("search_ellipsoid"), "Эллипсоид", max_length=120),
        status=_clean_text(raw.get("status", "planned"), "Статус", max_length=80) or "planned",
        parameters=dict(raw.get("parameters") or {}),
        created_at=_clean_text(raw.get("created_at"), "Дата", max_length=80),
        author=_clean_text(raw.get("author"), "Автор", max_length=120),
    )


def load_geostatistics_workspace(root: Any = DEFAULT_PROJECTS_ROOT, project_id: str = DEFAULT_PROJECT_ID) -> dict[str, Any]:
    return _json_read(_workspace_path(root, project_id), {"variogram_models": [], "search_ellipsoids": [], "jobs": []})


def save_variogram_model(root: Any, project_id: str, model: VariogramModelSpec | dict[str, Any], *, replace: bool = True) -> VariogramModelSpec:
    spec = _model_from_dict(model) if isinstance(model, dict) else model
    if not spec.created_at:
        spec = VariogramModelSpec(**{**_model_to_dict(spec), "created_at": _now_iso()})
    data = load_geostatistics_workspace(root, project_id)
    items = [_model_from_dict(row) for row in data.get("variogram_models", [])]
    existing = [row for row in items if row.name.lower() == spec.name.lower()]
    if existing and not replace:
        raise ValueError(f"Модель вариограммы уже существует: {spec.name}")
    items = [row for row in items if row.name.lower() != spec.name.lower()] + [spec]
    data["variogram_models"] = [_model_to_dict(row) for row in items]
    _json_write(_workspace_path(root, project_id), data)
    append_project_history(root, project_id, "geostatistics.save_variogram_model", f"Saved variogram model: {spec.name}")
    return spec


def list_variogram_models(root: Any = DEFAULT_PROJECTS_ROOT, project_id: str = DEFAULT_PROJECT_ID, *, property_name: str | None = None) -> tuple[VariogramModelSpec, ...]:
    items = tuple(_model_from_dict(row) for row in load_geostatistics_workspace(root, project_id).get("variogram_models", []))
    if property_name:
        return tuple(row for row in items if row.property_name.lower() == property_name.lower())
    return items


def save_search_ellipsoid(root: Any, project_id: str, ellipsoid: SearchEllipsoidSpec | dict[str, Any], *, replace: bool = True) -> SearchEllipsoidSpec:
    spec = _ellipsoid_from_dict(ellipsoid) if isinstance(ellipsoid, dict) else ellipsoid
    data = load_geostatistics_workspace(root, project_id)
    items = [_ellipsoid_from_dict(row) for row in data.get("search_ellipsoids", [])]
    existing = [row for row in items if row.name.lower() == spec.name.lower()]
    if existing and not replace:
        raise ValueError(f"Search ellipsoid уже существует: {spec.name}")
    items = [row for row in items if row.name.lower() != spec.name.lower()] + [spec]
    data["search_ellipsoids"] = [_ellipsoid_to_dict(row) for row in items]
    _json_write(_workspace_path(root, project_id), data)
    append_project_history(root, project_id, "geostatistics.save_search_ellipsoid", f"Saved search ellipsoid: {spec.name}")
    return spec


def list_search_ellipsoids(root: Any = DEFAULT_PROJECTS_ROOT, project_id: str = DEFAULT_PROJECT_ID) -> tuple[SearchEllipsoidSpec, ...]:
    return tuple(_ellipsoid_from_dict(row) for row in load_geostatistics_workspace(root, project_id).get("search_ellipsoids", []))


def save_geostatistics_job(root: Any, project_id: str, job: GeostatisticsJob | dict[str, Any], *, replace: bool = True) -> GeostatisticsJob:
    spec = _job_from_dict(job) if isinstance(job, dict) else job
    if not spec.created_at:
        spec = GeostatisticsJob(**{**_job_to_dict(spec), "created_at": _now_iso()})
    data = load_geostatistics_workspace(root, project_id)
    items = [_job_from_dict(row) for row in data.get("jobs", [])]
    existing = [row for row in items if row.name.lower() == spec.name.lower()]
    if existing and not replace:
        raise ValueError(f"Geostatistics job уже существует: {spec.name}")
    items = [row for row in items if row.name.lower() != spec.name.lower()] + [spec]
    data["jobs"] = [_job_to_dict(row) for row in items]
    _json_write(_workspace_path(root, project_id), data)
    append_project_history(root, project_id, "geostatistics.save_job", f"Saved geostatistics job: {spec.name}")
    return spec


def list_geostatistics_jobs(root: Any = DEFAULT_PROJECTS_ROOT, project_id: str = DEFAULT_PROJECT_ID) -> tuple[GeostatisticsJob, ...]:
    return tuple(_job_from_dict(row) for row in load_geostatistics_workspace(root, project_id).get("jobs", []))


def build_default_geostatistics_seed(author: str = "") -> dict[str, Any]:
    return {
        "variogram_models": [
            _model_to_dict(VariogramModelSpec(name="POR spherical foundation", model_type="spherical", nugget=0.02, sill=0.08, range_major=1200.0, property_name="POR", author=author, created_at=_now_iso())),
            _model_to_dict(VariogramModelSpec(name="PERM exponential foundation", model_type="exponential", nugget=0.1, sill=1.0, range_major=900.0, property_name="PERM", author=author, created_at=_now_iso())),
        ],
        "search_ellipsoids": [
            _ellipsoid_to_dict(SearchEllipsoidSpec(name="Default reservoir search", radius_major=1500.0, radius_minor=800.0, radius_vertical=25.0, max_neighbors=16, sector_count=4)),
        ],
        "jobs": [
            _job_to_dict(GeostatisticsJob(name="POR experimental variogram", property_name="POR", algorithm="experimental_variogram", model_name="POR spherical foundation", search_ellipsoid="Default reservoir search", author=author, created_at=_now_iso())),
        ],
    }


def seed_geostatistics_workspace(root: Any, project_id: str, *, author: str = "", overwrite: bool = False) -> dict[str, Any]:
    path = _workspace_path(root, project_id)
    if path.exists() and not overwrite:
        return load_geostatistics_workspace(root, project_id)
    seed = build_default_geostatistics_seed(author=author)
    _json_write(path, seed)
    append_project_history(root, project_id, "geostatistics.seed", "Seeded geostatistics workspace")
    return seed


def build_geostatistics_manifest(root: Any = DEFAULT_PROJECTS_ROOT, project_id: str = DEFAULT_PROJECT_ID) -> GeostatisticsManifest:
    models = list_variogram_models(root, project_id)
    ellipsoids = list_search_ellipsoids(root, project_id)
    jobs = list_geostatistics_jobs(root, project_id)
    warnings: list[str] = []
    if not models:
        warnings.append("Нет моделей вариограмм.")
    if not ellipsoids:
        warnings.append("Нет search ellipsoid настроек.")
    return GeostatisticsManifest(
        project_id=safe_project_id(project_id),
        generated_at=_now_iso(),
        model_count=len(models),
        ellipsoid_count=len(ellipsoids),
        job_count=len(jobs),
        warnings=tuple(warnings),
    )


def build_variogram_model_table(models: Iterable[VariogramModelSpec]) -> list[dict[str, Any]]:
    return [
        {
            "name": row.name,
            "property": row.property_name,
            "type": row.model_type,
            "nugget": row.nugget,
            "sill": row.sill,
            "range_major": row.range_major,
            "fit_score": row.fit_score,
        }
        for row in models
    ]


def build_experimental_variogram_table(bins: Iterable[VariogramBin]) -> list[dict[str, Any]]:
    return [_bin_to_dict(row) for row in bins]


def build_search_ellipsoid_table(items: Iterable[SearchEllipsoidSpec]) -> list[dict[str, Any]]:
    return [
        {
            "name": row.name,
            "major": row.radius_major,
            "minor": row.radius_minor,
            "vertical": row.radius_vertical,
            "azimuth": row.azimuth,
            "neighbors": f"{row.min_neighbors}-{row.max_neighbors}",
            "sectors": row.sector_count,
        }
        for row in items
    ]


def render_geostatistics_markdown(root: Any = DEFAULT_PROJECTS_ROOT, project_id: str = DEFAULT_PROJECT_ID) -> str:
    manifest = build_geostatistics_manifest(root, project_id)
    models = list_variogram_models(root, project_id)
    ellipsoids = list_search_ellipsoids(root, project_id)
    jobs = list_geostatistics_jobs(root, project_id)
    lines = [
        "# Geostatistics Workspace Report",
        "",
        f"Project: `{manifest.project_id}`",
        f"Generated: `{manifest.generated_at}`",
        "",
        "## Summary",
        f"- Variogram models: {manifest.model_count}",
        f"- Search ellipsoids: {manifest.ellipsoid_count}",
        f"- Jobs: {manifest.job_count}",
        "",
        "## Variogram Models",
    ]
    if models:
        lines.append("| Name | Property | Type | Nugget | Sill | Range | Fit |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|")
        for row in models:
            lines.append(f"| {row.name} | {row.property_name or '-'} | {row.model_type} | {row.nugget} | {row.sill} | {row.range_major} | {row.fit_score if row.fit_score is not None else '-'} |")
    else:
        lines.append("No variogram models registered.")
    lines.extend(["", "## Search Ellipsoids"])
    if ellipsoids:
        lines.append("| Name | Major | Minor | Vertical | Azimuth | Neighbors |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        for row in ellipsoids:
            lines.append(f"| {row.name} | {row.radius_major} | {row.radius_minor} | {row.radius_vertical} | {row.azimuth} | {row.min_neighbors}-{row.max_neighbors} |")
    else:
        lines.append("No search ellipsoids registered.")
    lines.extend(["", "## Jobs"])
    if jobs:
        for row in jobs:
            lines.append(f"- **{row.name}** — {row.algorithm}, property `{row.property_name}`, status `{row.status}`.")
    else:
        lines.append("No geostatistics jobs registered.")
    if manifest.warnings:
        lines.extend(["", "## Warnings"])
        lines.extend(f"- {warning}" for warning in manifest.warnings)
    return "\n".join(lines) + "\n"
