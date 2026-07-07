from __future__ import annotations

import json
import math
import random
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Iterable, Sequence

from projects.interpolation_engine import GridNode, InterpolationSample, normalize_grid_nodes, normalize_samples
from projects.project_manager import append_project_history
from projects.repository import DEFAULT_PROJECT_ID, DEFAULT_PROJECTS_ROOT, safe_project_id

PROPERTY_SIMULATION_FILE_NAME = "property_simulation_engine.json"
SIMULATION_METHODS = {"sequential_gaussian_foundation", "sequential_indicator_foundation"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _project_dir(root: Any, project_id: str) -> Path:
    return Path(root) / safe_project_id(project_id)


def _engine_path(root: Any, project_id: str) -> Path:
    return _project_dir(root, project_id) / PROPERTY_SIMULATION_FILE_NAME


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


def _to_int(value: Any, label: str, *, required: bool = False, minimum: int | None = None) -> int | None:
    number = _to_float(value, label, required=required, minimum=float(minimum) if minimum is not None else None)
    if number is None:
        return None
    integer = int(number)
    if abs(integer - number) > 1e-9:
        raise ValueError(f"{label}: ожидается целое число.")
    return integer


@dataclass(frozen=True)
class SimulationSample:
    x: float
    y: float
    value: float | str
    z: float | None = None
    well: str = ""
    zone: str = ""


@dataclass(frozen=True)
class SimulatedCell:
    x: float
    y: float
    value: float | str | None
    z: float | None = None
    i: int | None = None
    j: int | None = None
    k: int | None = None
    method: str = "sequential_gaussian_foundation"
    realization: int = 1
    seed: int = 0
    base_estimate: float | str | None = None
    uncertainty: float = 0.0
    confidence: float = 0.0


@dataclass(frozen=True)
class SimulationJobSpec:
    name: str
    property_name: str
    method: str = "sequential_gaussian_foundation"
    zone_name: str = ""
    realization_count: int = 1
    seed: int = 42
    parameters: dict[str, Any] = field(default_factory=dict)
    source: str = "well_samples"
    status: str = "planned"
    created_at: str = ""
    author: str = ""


@dataclass(frozen=True)
class SimulationManifest:
    project_id: str
    generated_at: str
    job_count: int
    realization_count: int
    method_count: int
    warnings: tuple[str, ...] = ()


def _distance(sample: SimulationSample, node: GridNode, *, use_z: bool = False) -> float:
    dz = ((sample.z or 0.0) - (node.z or 0.0)) if use_z and sample.z is not None and node.z is not None else 0.0
    return math.sqrt((sample.x - node.x) ** 2 + (sample.y - node.y) ** 2 + dz**2)


def _normalize_simulation_sample(raw: SimulationSample | InterpolationSample | dict[str, Any] | Sequence[Any]) -> SimulationSample:
    if isinstance(raw, SimulationSample):
        return raw
    if isinstance(raw, InterpolationSample):
        return SimulationSample(x=raw.x, y=raw.y, z=raw.z, value=raw.value, well=raw.well, zone=raw.zone)
    if isinstance(raw, dict):
        value = raw.get("value")
        if isinstance(value, str) and not value.strip():
            raise ValueError("Значение sample не может быть пустым.")
        try:
            numeric_value: float | str = _to_float(value, "Значение", required=True) or 0.0
        except ValueError:
            numeric_value = _clean_text(value, "Значение", required=True, max_length=80)
        return SimulationSample(
            x=_to_float(raw.get("x"), "X", required=True) or 0.0,
            y=_to_float(raw.get("y"), "Y", required=True) or 0.0,
            z=_to_float(raw.get("z"), "Z"),
            value=numeric_value,
            well=_clean_text(raw.get("well"), "Скважина", max_length=120),
            zone=_clean_text(raw.get("zone"), "Зона", max_length=120),
        )
    values = list(raw)
    if len(values) < 3:
        raise ValueError("Simulation sample должен содержать X, Y и value.")
    try:
        numeric_value = _to_float(values[2], "Значение", required=True) or 0.0
    except ValueError:
        numeric_value = _clean_text(values[2], "Значение", required=True, max_length=80)
    return SimulationSample(
        x=_to_float(values[0], "X", required=True) or 0.0,
        y=_to_float(values[1], "Y", required=True) or 0.0,
        value=numeric_value,
        z=_to_float(values[3], "Z") if len(values) > 3 else None,
    )


def normalize_simulation_samples(samples: Iterable[SimulationSample | InterpolationSample | dict[str, Any] | Sequence[Any]]) -> tuple[SimulationSample, ...]:
    result = tuple(_normalize_simulation_sample(row) for row in samples)
    if not result:
        raise ValueError("Для моделирования требуется минимум одна точка.")
    return result


def _nearest_neighbors(
    samples: tuple[SimulationSample, ...],
    node: GridNode,
    *,
    max_neighbors: int,
    search_radius: float | None = None,
    use_z: bool = False,
) -> list[tuple[float, SimulationSample]]:
    pairs = [(_distance(sample, node, use_z=use_z), sample) for sample in samples]
    if search_radius is not None:
        radius = _to_float(search_radius, "Search radius", minimum=0.0)
        pairs = [(distance, sample) for distance, sample in pairs if radius is None or distance <= radius]
    pairs.sort(key=lambda item: item[0])
    return pairs[: max(1, int(max_neighbors))]


def _numeric_samples(samples: tuple[SimulationSample, ...]) -> tuple[SimulationSample, ...]:
    numeric = tuple(sample for sample in samples if isinstance(sample.value, (int, float)))
    if not numeric:
        raise ValueError("Sequential Gaussian Simulation требует числовые значения sample.")
    return numeric


def _weighted_mean(neighbors: list[tuple[float, SimulationSample]], *, power: float = 2.0) -> tuple[float, float]:
    if not neighbors:
        return 0.0, 0.0
    if neighbors[0][0] == 0:
        return float(neighbors[0][1].value), 1.0
    weights = [(1.0 / ((distance + 1e-9) ** power), float(sample.value)) for distance, sample in neighbors]
    total_weight = sum(weight for weight, _ in weights)
    estimate = sum(weight * value for weight, value in weights) / total_weight if total_weight else 0.0
    confidence = min(1.0, len(neighbors) / 12.0) * (1.0 / (1.0 + neighbors[0][0]))
    return estimate, confidence


def sequential_gaussian_simulation_foundation(
    samples: Iterable[SimulationSample | InterpolationSample | dict[str, Any] | Sequence[Any]],
    grid_nodes: Iterable[GridNode | dict[str, Any] | Sequence[Any]],
    *,
    realization_count: int = 1,
    seed: int = 42,
    max_neighbors: int = 12,
    search_radius: float | None = None,
    noise_scale: float = 0.25,
    min_value: float | None = None,
    max_value: float | None = None,
    use_z: bool = False,
) -> tuple[SimulatedCell, ...]:
    normalized_samples = _numeric_samples(normalize_simulation_samples(samples))
    nodes = normalize_grid_nodes(grid_nodes)
    realization_count = _to_int(realization_count, "Количество реализаций", required=True, minimum=1) or 1
    seed = _to_int(seed, "Seed", required=True) or 0
    max_neighbors = _to_int(max_neighbors, "Max neighbors", required=True, minimum=1) or 1
    noise_scale = _to_float(noise_scale, "Noise scale", required=True, minimum=0.0) or 0.0
    values = [float(sample.value) for sample in normalized_samples]
    global_std = pstdev(values) if len(values) > 1 else 0.0
    cells: list[SimulatedCell] = []
    for realization in range(1, realization_count + 1):
        rng = random.Random(seed + realization - 1)
        ordered_nodes = list(nodes)
        rng.shuffle(ordered_nodes)
        simulated_by_index: dict[tuple[float, float, float | None], float] = {}
        for node in ordered_nodes:
            neighbors = _nearest_neighbors(normalized_samples, node, max_neighbors=max_neighbors, search_radius=search_radius, use_z=use_z)
            if neighbors:
                estimate, confidence = _weighted_mean(neighbors)
                local_values = [float(sample.value) for _, sample in neighbors]
                local_std = pstdev(local_values) if len(local_values) > 1 else global_std
            else:
                estimate = mean(values)
                confidence = 0.2
                local_std = global_std
            uncertainty = max(0.0, local_std * noise_scale * (1.0 - min(0.95, confidence)))
            value = estimate + rng.gauss(0.0, uncertainty) if uncertainty > 0 else estimate
            if min_value is not None:
                value = max(_to_float(min_value, "Min value") or 0.0, value)
            if max_value is not None:
                value = min(_to_float(max_value, "Max value") or value, value)
            value = round(value, 10)
            simulated_by_index[(node.x, node.y, node.z)] = value
            cells.append(
                SimulatedCell(
                    x=node.x,
                    y=node.y,
                    z=node.z,
                    i=node.i,
                    j=node.j,
                    k=node.k,
                    value=value,
                    method="sequential_gaussian_foundation",
                    realization=realization,
                    seed=seed,
                    base_estimate=round(estimate, 10),
                    uncertainty=round(uncertainty, 10),
                    confidence=round(min(1.0, confidence), 6),
                )
            )
    return tuple(cells)


def _indicator_probabilities(neighbors: list[tuple[float, SimulationSample]], categories: tuple[str, ...]) -> dict[str, float]:
    if not neighbors:
        even = 1.0 / len(categories) if categories else 0.0
        return {category: even for category in categories}
    if neighbors[0][0] == 0:
        category = str(neighbors[0][1].value)
        return {item: 1.0 if item == category else 0.0 for item in categories}
    weighted: dict[str, float] = defaultdict(float)
    for distance, sample in neighbors:
        weighted[str(sample.value)] += 1.0 / ((distance + 1e-9) ** 2.0)
    total = sum(weighted.values())
    return {category: (weighted.get(category, 0.0) / total if total else 0.0) for category in categories}


def sequential_indicator_simulation_foundation(
    samples: Iterable[SimulationSample | InterpolationSample | dict[str, Any] | Sequence[Any]],
    grid_nodes: Iterable[GridNode | dict[str, Any] | Sequence[Any]],
    *,
    categories: Iterable[str] | None = None,
    realization_count: int = 1,
    seed: int = 42,
    max_neighbors: int = 12,
    search_radius: float | None = None,
    use_z: bool = False,
) -> tuple[SimulatedCell, ...]:
    normalized_samples = normalize_simulation_samples(samples)
    nodes = normalize_grid_nodes(grid_nodes)
    realization_count = _to_int(realization_count, "Количество реализаций", required=True, minimum=1) or 1
    seed = _to_int(seed, "Seed", required=True) or 0
    max_neighbors = _to_int(max_neighbors, "Max neighbors", required=True, minimum=1) or 1
    if categories is None:
        category_items = tuple(sorted({str(sample.value) for sample in normalized_samples}))
    else:
        category_items = tuple(_clean_text(item, "Категория", required=True, max_length=80) for item in categories)
    if not category_items:
        raise ValueError("Sequential Indicator Simulation требует минимум одну категорию.")
    cells: list[SimulatedCell] = []
    for realization in range(1, realization_count + 1):
        rng = random.Random(seed + realization - 1)
        ordered_nodes = list(nodes)
        rng.shuffle(ordered_nodes)
        for node in ordered_nodes:
            neighbors = _nearest_neighbors(normalized_samples, node, max_neighbors=max_neighbors, search_radius=search_radius, use_z=use_z)
            probabilities = _indicator_probabilities(neighbors, category_items)
            threshold = rng.random()
            cumulative = 0.0
            chosen = category_items[-1]
            for category in category_items:
                cumulative += probabilities.get(category, 0.0)
                if threshold <= cumulative:
                    chosen = category
                    break
            dominant = max(probabilities.items(), key=lambda item: item[1])[0] if probabilities else chosen
            cells.append(
                SimulatedCell(
                    x=node.x,
                    y=node.y,
                    z=node.z,
                    i=node.i,
                    j=node.j,
                    k=node.k,
                    value=chosen,
                    method="sequential_indicator_foundation",
                    realization=realization,
                    seed=seed,
                    base_estimate=dominant,
                    uncertainty=round(1.0 - probabilities.get(dominant, 0.0), 6),
                    confidence=round(probabilities.get(dominant, 0.0), 6),
                )
            )
    return tuple(cells)


def run_property_simulation(
    samples: Iterable[SimulationSample | InterpolationSample | dict[str, Any] | Sequence[Any]],
    grid_nodes: Iterable[GridNode | dict[str, Any] | Sequence[Any]],
    *,
    method: str = "sequential_gaussian_foundation",
    parameters: dict[str, Any] | None = None,
) -> tuple[SimulatedCell, ...]:
    method = _clean_text(method, "Метод", required=True).lower()
    if method not in SIMULATION_METHODS:
        raise ValueError(f"Метод моделирования не поддерживается: {method}.")
    parameters = parameters or {}
    if method == "sequential_indicator_foundation":
        return sequential_indicator_simulation_foundation(
            samples,
            grid_nodes,
            categories=parameters.get("categories"),
            realization_count=parameters.get("realization_count", 1),
            seed=parameters.get("seed", 42),
            max_neighbors=parameters.get("max_neighbors", 12),
            search_radius=parameters.get("search_radius"),
            use_z=bool(parameters.get("use_z", False)),
        )
    return sequential_gaussian_simulation_foundation(
        samples,
        grid_nodes,
        realization_count=parameters.get("realization_count", 1),
        seed=parameters.get("seed", 42),
        max_neighbors=parameters.get("max_neighbors", 12),
        search_radius=parameters.get("search_radius"),
        noise_scale=parameters.get("noise_scale", 0.25),
        min_value=parameters.get("min_value"),
        max_value=parameters.get("max_value"),
        use_z=bool(parameters.get("use_z", False)),
    )


def _job_to_dict(job: SimulationJobSpec) -> dict[str, Any]:
    method = _clean_text(job.method, "Метод", required=True).lower()
    if method not in SIMULATION_METHODS:
        raise ValueError(f"Метод моделирования не поддерживается: {method}.")
    realization_count = _to_int(job.realization_count, "Количество реализаций", required=True, minimum=1) or 1
    return {
        "name": _clean_text(job.name, "Название задания", required=True),
        "property_name": _clean_text(job.property_name, "Свойство", required=True, max_length=80),
        "method": method,
        "zone_name": _clean_text(job.zone_name, "Зона", max_length=120),
        "realization_count": realization_count,
        "seed": _to_int(job.seed, "Seed", required=True) or 0,
        "parameters": dict(job.parameters),
        "source": _clean_text(job.source, "Источник", max_length=160),
        "status": _clean_text(job.status, "Статус", max_length=60) or "planned",
        "created_at": job.created_at or _now_iso(),
        "author": _clean_text(job.author, "Автор", max_length=120),
    }


def _job_from_dict(raw: dict[str, Any]) -> SimulationJobSpec:
    return SimulationJobSpec(
        name=_clean_text(raw.get("name"), "Название задания", required=True),
        property_name=_clean_text(raw.get("property_name"), "Свойство", required=True, max_length=80),
        method=_clean_text(raw.get("method", "sequential_gaussian_foundation"), "Метод", required=True).lower(),
        zone_name=_clean_text(raw.get("zone_name"), "Зона", max_length=120),
        realization_count=_to_int(raw.get("realization_count", 1), "Количество реализаций", required=True, minimum=1) or 1,
        seed=_to_int(raw.get("seed", 42), "Seed", required=True) or 0,
        parameters=dict(raw.get("parameters") or {}),
        source=_clean_text(raw.get("source", "well_samples"), "Источник", max_length=160),
        status=_clean_text(raw.get("status", "planned"), "Статус", max_length=60) or "planned",
        created_at=_clean_text(raw.get("created_at"), "Дата", max_length=80),
        author=_clean_text(raw.get("author"), "Автор", max_length=120),
    )


def load_property_simulation_engine(root: Any = DEFAULT_PROJECTS_ROOT, project_id: str = DEFAULT_PROJECT_ID) -> dict[str, Any]:
    payload = _json_read(_engine_path(root, project_id), {"jobs": []})
    payload.setdefault("jobs", [])
    return payload


def save_simulation_job(root: Any, project_id: str, job: SimulationJobSpec) -> dict[str, Any]:
    payload = load_property_simulation_engine(root, project_id)
    job_payload = _job_to_dict(job)
    jobs = [row for row in payload.get("jobs", []) if row.get("name") != job_payload["name"]]
    jobs.append(job_payload)
    payload["jobs"] = jobs
    _json_write(_engine_path(root, project_id), payload)
    append_project_history(root, project_id, "property_simulation.job.save", f"Saved simulation job: {job_payload['name']}")
    return job_payload


def list_simulation_jobs(root: Any = DEFAULT_PROJECTS_ROOT, project_id: str = DEFAULT_PROJECT_ID) -> tuple[SimulationJobSpec, ...]:
    payload = load_property_simulation_engine(root, project_id)
    return tuple(_job_from_dict(row) for row in payload.get("jobs", []))


def build_default_property_simulation_seed(author: str = "") -> dict[str, Any]:
    return {
        "jobs": [
            _job_to_dict(SimulationJobSpec(name="POR SGS foundation", property_name="POR", method="sequential_gaussian_foundation", zone_name="Reservoir", realization_count=3, seed=42, parameters={"noise_scale": 0.2, "min_value": 0.0, "max_value": 0.45}, author=author, created_at=_now_iso())),
            _job_to_dict(SimulationJobSpec(name="Facies SIS foundation", property_name="FACIES", method="sequential_indicator_foundation", zone_name="Reservoir", realization_count=2, seed=77, parameters={"categories": ["Sand", "Shale"]}, author=author, created_at=_now_iso())),
        ]
    }


def seed_property_simulation_engine(root: Any, project_id: str, *, author: str = "", overwrite: bool = False) -> dict[str, Any]:
    path = _engine_path(root, project_id)
    if path.exists() and not overwrite:
        return load_property_simulation_engine(root, project_id)
    payload = build_default_property_simulation_seed(author=author)
    _json_write(path, payload)
    append_project_history(root, project_id, "property_simulation.seed", "Seeded property simulation engine")
    return payload


def _cell_to_dict(cell: SimulatedCell) -> dict[str, Any]:
    return {
        "realization": cell.realization,
        "seed": cell.seed,
        "x": cell.x,
        "y": cell.y,
        "z": cell.z,
        "i": cell.i,
        "j": cell.j,
        "k": cell.k,
        "value": cell.value,
        "method": cell.method,
        "base_estimate": cell.base_estimate,
        "uncertainty": cell.uncertainty,
        "confidence": cell.confidence,
    }


def build_simulated_cells_table(cells: Iterable[SimulatedCell]) -> list[dict[str, Any]]:
    return [_cell_to_dict(cell) for cell in cells]


def build_simulation_job_table(jobs: Iterable[SimulationJobSpec]) -> list[dict[str, Any]]:
    return [
        {
            "name": job.name,
            "property": job.property_name,
            "zone": job.zone_name,
            "method": job.method,
            "realizations": job.realization_count,
            "seed": job.seed,
            "status": job.status,
        }
        for job in jobs
    ]


def summarize_simulation_result(cells: Iterable[SimulatedCell]) -> dict[str, Any]:
    items = tuple(cells)
    numeric_values = [float(cell.value) for cell in items if isinstance(cell.value, (int, float))]
    category_values = [str(cell.value) for cell in items if isinstance(cell.value, str)]
    category_counts = dict(Counter(category_values))
    return {
        "cell_count": len(items),
        "realization_count": len({cell.realization for cell in items}),
        "numeric_count": len(numeric_values),
        "category_count": len(category_values),
        "min": round(min(numeric_values), 10) if numeric_values else None,
        "max": round(max(numeric_values), 10) if numeric_values else None,
        "mean": round(sum(numeric_values) / len(numeric_values), 10) if numeric_values else None,
        "category_counts": category_counts,
        "average_uncertainty": round(sum(cell.uncertainty for cell in items) / len(items), 6) if items else None,
        "average_confidence": round(sum(cell.confidence for cell in items) / len(items), 6) if items else None,
    }


def build_property_simulation_manifest(root: Any = DEFAULT_PROJECTS_ROOT, project_id: str = DEFAULT_PROJECT_ID) -> SimulationManifest:
    jobs = list_simulation_jobs(root, project_id)
    warnings: list[str] = []
    if not jobs:
        warnings.append("Нет заданий стохастического моделирования.")
    methods = {job.method for job in jobs}
    realizations = sum(job.realization_count for job in jobs)
    return SimulationManifest(project_id=safe_project_id(project_id), generated_at=_now_iso(), job_count=len(jobs), realization_count=realizations, method_count=len(methods), warnings=tuple(warnings))


def render_property_simulation_markdown(root: Any = DEFAULT_PROJECTS_ROOT, project_id: str = DEFAULT_PROJECT_ID) -> str:
    manifest = build_property_simulation_manifest(root, project_id)
    jobs = list_simulation_jobs(root, project_id)
    lines = [
        "# Property Simulation Engine Report",
        "",
        f"Project: `{manifest.project_id}`",
        f"Generated: `{manifest.generated_at}`",
        "",
        "## Summary",
        f"- Jobs: {manifest.job_count}",
        f"- Total realizations: {manifest.realization_count}",
        f"- Methods used: {manifest.method_count}",
        "",
        "## Registered Jobs",
    ]
    if jobs:
        lines.append("| Name | Property | Zone | Method | Realizations | Seed | Status |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|")
        for job in jobs:
            lines.append(f"| {job.name} | {job.property_name} | {job.zone_name or '-'} | {job.method} | {job.realization_count} | {job.seed} | {job.status} |")
    else:
        lines.append("No simulation jobs registered.")
    if manifest.warnings:
        lines.extend(["", "## Warnings"])
        lines.extend(f"- {warning}" for warning in manifest.warnings)
    return "\n".join(lines) + "\n"
