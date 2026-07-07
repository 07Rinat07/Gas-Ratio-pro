from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

from projects.project_manager import append_project_history
from projects.repository import DEFAULT_PROJECT_ID, DEFAULT_PROJECTS_ROOT, safe_project_id

INTERPOLATION_ENGINE_FILE_NAME = "interpolation_engine.json"
INTERPOLATION_METHODS = {"nearest", "idw", "simple_kriging_foundation"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _project_dir(root: Any, project_id: str) -> Path:
    return Path(root) / safe_project_id(project_id)


def _engine_path(root: Any, project_id: str) -> Path:
    return _project_dir(root, project_id) / INTERPOLATION_ENGINE_FILE_NAME


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
class InterpolationSample:
    x: float
    y: float
    value: float
    z: float | None = None
    well: str = ""
    zone: str = ""


@dataclass(frozen=True)
class GridNode:
    x: float
    y: float
    z: float | None = None
    i: int | None = None
    j: int | None = None
    k: int | None = None


@dataclass(frozen=True)
class InterpolatedCell:
    x: float
    y: float
    value: float | None
    z: float | None = None
    i: int | None = None
    j: int | None = None
    k: int | None = None
    method: str = "idw"
    neighbor_count: int = 0
    distance_to_nearest: float | None = None
    confidence: float = 0.0


@dataclass(frozen=True)
class InterpolationJobSpec:
    name: str
    property_name: str
    method: str = "idw"
    zone_name: str = ""
    source: str = "well_samples"
    parameters: dict[str, Any] = field(default_factory=dict)
    status: str = "planned"
    created_at: str = ""
    author: str = ""


@dataclass(frozen=True)
class InterpolationManifest:
    project_id: str
    generated_at: str
    job_count: int
    method_count: int
    warnings: tuple[str, ...] = ()


def _sample_from_dict(raw: dict[str, Any]) -> InterpolationSample:
    return InterpolationSample(
        x=_to_float(raw.get("x"), "X", required=True) or 0.0,
        y=_to_float(raw.get("y"), "Y", required=True) or 0.0,
        z=_to_float(raw.get("z"), "Z"),
        value=_to_float(raw.get("value"), "Значение", required=True) or 0.0,
        well=_clean_text(raw.get("well"), "Скважина", max_length=120),
        zone=_clean_text(raw.get("zone"), "Зона", max_length=120),
    )


def _node_from_dict(raw: dict[str, Any]) -> GridNode:
    return GridNode(
        x=_to_float(raw.get("x"), "X", required=True) or 0.0,
        y=_to_float(raw.get("y"), "Y", required=True) or 0.0,
        z=_to_float(raw.get("z"), "Z"),
        i=_to_int(raw.get("i"), "I"),
        j=_to_int(raw.get("j"), "J"),
        k=_to_int(raw.get("k"), "K"),
    )


def normalize_samples(samples: Iterable[InterpolationSample | dict[str, Any] | Sequence[Any]]) -> tuple[InterpolationSample, ...]:
    result: list[InterpolationSample] = []
    for row in samples:
        if isinstance(row, InterpolationSample):
            sample = row
        elif isinstance(row, dict):
            sample = _sample_from_dict(row)
        else:
            values = list(row)
            if len(values) < 3:
                raise ValueError("Sample должен содержать X, Y и value.")
            sample = InterpolationSample(
                x=_to_float(values[0], "X", required=True) or 0.0,
                y=_to_float(values[1], "Y", required=True) or 0.0,
                value=_to_float(values[2], "Значение", required=True) or 0.0,
                z=_to_float(values[3], "Z") if len(values) > 3 else None,
            )
        result.append(sample)
    if not result:
        raise ValueError("Для интерполяции требуется минимум одна точка.")
    return tuple(result)


def normalize_grid_nodes(nodes: Iterable[GridNode | dict[str, Any] | Sequence[Any]]) -> tuple[GridNode, ...]:
    result: list[GridNode] = []
    for row in nodes:
        if isinstance(row, GridNode):
            node = row
        elif isinstance(row, dict):
            node = _node_from_dict(row)
        else:
            values = list(row)
            if len(values) < 2:
                raise ValueError("Grid node должен содержать минимум X и Y.")
            node = GridNode(
                x=_to_float(values[0], "X", required=True) or 0.0,
                y=_to_float(values[1], "Y", required=True) or 0.0,
                z=_to_float(values[2], "Z") if len(values) > 2 else None,
            )
        result.append(node)
    if not result:
        raise ValueError("Сетка интерполяции пуста.")
    return tuple(result)


def build_regular_grid(
    *,
    x_min: float,
    x_max: float,
    y_min: float,
    y_max: float,
    nx: int,
    ny: int,
    z: float | None = None,
) -> tuple[GridNode, ...]:
    x_min = _to_float(x_min, "X min", required=True) or 0.0
    x_max = _to_float(x_max, "X max", required=True) or 0.0
    y_min = _to_float(y_min, "Y min", required=True) or 0.0
    y_max = _to_float(y_max, "Y max", required=True) or 0.0
    nx = _to_int(nx, "NX", required=True, minimum=1) or 1
    ny = _to_int(ny, "NY", required=True, minimum=1) or 1
    if x_max < x_min or y_max < y_min:
        raise ValueError("Максимальные координаты должны быть больше минимальных.")
    nodes: list[GridNode] = []
    for j in range(ny):
        y = y_min if ny == 1 else y_min + (y_max - y_min) * j / (ny - 1)
        for i in range(nx):
            x = x_min if nx == 1 else x_min + (x_max - x_min) * i / (nx - 1)
            nodes.append(GridNode(x=round(x, 10), y=round(y, 10), z=z, i=i, j=j))
    return tuple(nodes)


def _distance(sample: InterpolationSample, node: GridNode, *, use_z: bool = False) -> float:
    dz = ((sample.z or 0.0) - (node.z or 0.0)) if use_z and sample.z is not None and node.z is not None else 0.0
    return math.sqrt((sample.x - node.x) ** 2 + (sample.y - node.y) ** 2 + dz**2)


def _nearest_neighbors(
    samples: tuple[InterpolationSample, ...],
    node: GridNode,
    *,
    max_neighbors: int,
    search_radius: float | None = None,
    use_z: bool = False,
) -> list[tuple[float, InterpolationSample]]:
    pairs = [(_distance(sample, node, use_z=use_z), sample) for sample in samples]
    if search_radius is not None:
        radius = _to_float(search_radius, "Search radius", minimum=0.0)
        pairs = [(distance, sample) for distance, sample in pairs if radius is None or distance <= radius]
    pairs.sort(key=lambda item: item[0])
    return pairs[: max(1, int(max_neighbors))]


def interpolate_nearest(
    samples: Iterable[InterpolationSample | dict[str, Any] | Sequence[Any]],
    grid_nodes: Iterable[GridNode | dict[str, Any] | Sequence[Any]],
    *,
    search_radius: float | None = None,
    use_z: bool = False,
) -> tuple[InterpolatedCell, ...]:
    normalized_samples = normalize_samples(samples)
    nodes = normalize_grid_nodes(grid_nodes)
    cells: list[InterpolatedCell] = []
    for node in nodes:
        neighbors = _nearest_neighbors(normalized_samples, node, max_neighbors=1, search_radius=search_radius, use_z=use_z)
        if not neighbors:
            cells.append(InterpolatedCell(x=node.x, y=node.y, z=node.z, i=node.i, j=node.j, k=node.k, value=None, method="nearest"))
            continue
        distance, sample = neighbors[0]
        confidence = 1.0 if distance == 0 else round(1.0 / (1.0 + distance), 6)
        cells.append(InterpolatedCell(x=node.x, y=node.y, z=node.z, i=node.i, j=node.j, k=node.k, value=sample.value, method="nearest", neighbor_count=1, distance_to_nearest=round(distance, 10), confidence=confidence))
    return tuple(cells)


def interpolate_idw(
    samples: Iterable[InterpolationSample | dict[str, Any] | Sequence[Any]],
    grid_nodes: Iterable[GridNode | dict[str, Any] | Sequence[Any]],
    *,
    power: float = 2.0,
    max_neighbors: int = 12,
    search_radius: float | None = None,
    use_z: bool = False,
) -> tuple[InterpolatedCell, ...]:
    normalized_samples = normalize_samples(samples)
    nodes = normalize_grid_nodes(grid_nodes)
    power = _to_float(power, "IDW power", required=True, minimum=0.000001) or 2.0
    max_neighbors = _to_int(max_neighbors, "Max neighbors", required=True, minimum=1) or 1
    cells: list[InterpolatedCell] = []
    for node in nodes:
        neighbors = _nearest_neighbors(normalized_samples, node, max_neighbors=max_neighbors, search_radius=search_radius, use_z=use_z)
        if not neighbors:
            cells.append(InterpolatedCell(x=node.x, y=node.y, z=node.z, i=node.i, j=node.j, k=node.k, value=None, method="idw"))
            continue
        if neighbors[0][0] == 0:
            value = neighbors[0][1].value
            confidence = 1.0
        else:
            weights = [(1.0 / (distance**power), sample) for distance, sample in neighbors]
            total_weight = sum(weight for weight, _ in weights)
            value = sum(weight * sample.value for weight, sample in weights) / total_weight if total_weight else None
            confidence = min(1.0, len(neighbors) / max_neighbors) * (1.0 / (1.0 + neighbors[0][0]))
        cells.append(InterpolatedCell(x=node.x, y=node.y, z=node.z, i=node.i, j=node.j, k=node.k, value=round(value, 10) if value is not None else None, method="idw", neighbor_count=len(neighbors), distance_to_nearest=round(neighbors[0][0], 10), confidence=round(confidence, 6)))
    return tuple(cells)


def interpolate_simple_kriging_foundation(
    samples: Iterable[InterpolationSample | dict[str, Any] | Sequence[Any]],
    grid_nodes: Iterable[GridNode | dict[str, Any] | Sequence[Any]],
    *,
    mean_value: float | None = None,
    max_neighbors: int = 8,
    search_radius: float | None = None,
    use_z: bool = False,
) -> tuple[InterpolatedCell, ...]:
    """Foundation implementation: deterministic local weighted mean around a global mean.

    This is intentionally conservative. It produces reproducible cells and metadata for UI/reporting,
    while full covariance-matrix kriging can be added later without changing the public job API.
    """
    normalized_samples = normalize_samples(samples)
    if mean_value is None:
        mean_value = sum(sample.value for sample in normalized_samples) / len(normalized_samples)
    mean_value = _to_float(mean_value, "Mean value", required=True) or 0.0
    nodes = normalize_grid_nodes(grid_nodes)
    max_neighbors = _to_int(max_neighbors, "Max neighbors", required=True, minimum=1) or 1
    cells: list[InterpolatedCell] = []
    for node in nodes:
        neighbors = _nearest_neighbors(normalized_samples, node, max_neighbors=max_neighbors, search_radius=search_radius, use_z=use_z)
        if not neighbors:
            cells.append(InterpolatedCell(x=node.x, y=node.y, z=node.z, i=node.i, j=node.j, k=node.k, value=round(mean_value, 10), method="simple_kriging_foundation", confidence=0.25))
            continue
        if neighbors[0][0] == 0:
            value = neighbors[0][1].value
            confidence = 1.0
        else:
            weights = [(1.0 / (1.0 + distance), sample) for distance, sample in neighbors]
            total = sum(weight for weight, _ in weights)
            local = sum(weight * sample.value for weight, sample in weights) / total
            blend = min(0.85, len(neighbors) / max_neighbors)
            value = mean_value * (1.0 - blend) + local * blend
            confidence = 0.35 + 0.55 * min(1.0, len(neighbors) / max_neighbors) * (1.0 / (1.0 + neighbors[0][0]))
        cells.append(InterpolatedCell(x=node.x, y=node.y, z=node.z, i=node.i, j=node.j, k=node.k, value=round(value, 10), method="simple_kriging_foundation", neighbor_count=len(neighbors), distance_to_nearest=round(neighbors[0][0], 10), confidence=round(min(1.0, confidence), 6)))
    return tuple(cells)


def run_interpolation(
    samples: Iterable[InterpolationSample | dict[str, Any] | Sequence[Any]],
    grid_nodes: Iterable[GridNode | dict[str, Any] | Sequence[Any]],
    *,
    method: str = "idw",
    parameters: dict[str, Any] | None = None,
) -> tuple[InterpolatedCell, ...]:
    method = _clean_text(method, "Метод", required=True).lower()
    parameters = parameters or {}
    if method not in INTERPOLATION_METHODS:
        raise ValueError(f"Метод интерполяции не поддерживается: {method}.")
    if method == "nearest":
        return interpolate_nearest(samples, grid_nodes, search_radius=parameters.get("search_radius"), use_z=bool(parameters.get("use_z", False)))
    if method == "simple_kriging_foundation":
        return interpolate_simple_kriging_foundation(samples, grid_nodes, mean_value=parameters.get("mean_value"), max_neighbors=parameters.get("max_neighbors", 8), search_radius=parameters.get("search_radius"), use_z=bool(parameters.get("use_z", False)))
    return interpolate_idw(samples, grid_nodes, power=parameters.get("power", 2.0), max_neighbors=parameters.get("max_neighbors", 12), search_radius=parameters.get("search_radius"), use_z=bool(parameters.get("use_z", False)))


def _job_to_dict(job: InterpolationJobSpec) -> dict[str, Any]:
    method = _clean_text(job.method, "Метод", required=True).lower()
    if method not in INTERPOLATION_METHODS:
        raise ValueError(f"Метод интерполяции не поддерживается: {method}.")
    return {
        "name": _clean_text(job.name, "Название задания", required=True),
        "property_name": _clean_text(job.property_name, "Свойство", required=True, max_length=80),
        "method": method,
        "zone_name": _clean_text(job.zone_name, "Зона", max_length=120),
        "source": _clean_text(job.source, "Источник", max_length=160),
        "parameters": dict(job.parameters),
        "status": _clean_text(job.status, "Статус", max_length=60) or "planned",
        "created_at": job.created_at or _now_iso(),
        "author": _clean_text(job.author, "Автор", max_length=120),
    }


def _job_from_dict(raw: dict[str, Any]) -> InterpolationJobSpec:
    return InterpolationJobSpec(
        name=_clean_text(raw.get("name"), "Название задания", required=True),
        property_name=_clean_text(raw.get("property_name"), "Свойство", required=True, max_length=80),
        method=_clean_text(raw.get("method", "idw"), "Метод", required=True).lower(),
        zone_name=_clean_text(raw.get("zone_name"), "Зона", max_length=120),
        source=_clean_text(raw.get("source", "well_samples"), "Источник", max_length=160),
        parameters=dict(raw.get("parameters") or {}),
        status=_clean_text(raw.get("status", "planned"), "Статус", max_length=60) or "planned",
        created_at=_clean_text(raw.get("created_at"), "Дата", max_length=80),
        author=_clean_text(raw.get("author"), "Автор", max_length=120),
    )


def load_interpolation_engine(root: Any = DEFAULT_PROJECTS_ROOT, project_id: str = DEFAULT_PROJECT_ID) -> dict[str, Any]:
    payload = _json_read(_engine_path(root, project_id), {"jobs": []})
    payload.setdefault("jobs", [])
    return payload


def save_interpolation_job(root: Any, project_id: str, job: InterpolationJobSpec) -> dict[str, Any]:
    payload = load_interpolation_engine(root, project_id)
    job_payload = _job_to_dict(job)
    jobs = [row for row in payload.get("jobs", []) if row.get("name") != job_payload["name"]]
    jobs.append(job_payload)
    payload["jobs"] = jobs
    _json_write(_engine_path(root, project_id), payload)
    append_project_history(root, project_id, "interpolation.job.save", f"Saved interpolation job: {job_payload['name']}")
    return job_payload


def list_interpolation_jobs(root: Any = DEFAULT_PROJECTS_ROOT, project_id: str = DEFAULT_PROJECT_ID) -> tuple[InterpolationJobSpec, ...]:
    payload = load_interpolation_engine(root, project_id)
    return tuple(_job_from_dict(row) for row in payload.get("jobs", []))


def build_default_interpolation_seed(author: str = "") -> dict[str, Any]:
    return {
        "jobs": [
            _job_to_dict(InterpolationJobSpec(name="POR IDW foundation", property_name="POR", method="idw", zone_name="Reservoir", parameters={"power": 2.0, "max_neighbors": 12}, author=author, created_at=_now_iso())),
            _job_to_dict(InterpolationJobSpec(name="PERM nearest foundation", property_name="PERM", method="nearest", zone_name="Reservoir", parameters={"search_radius": 1500.0}, author=author, created_at=_now_iso())),
        ]
    }


def seed_interpolation_engine(root: Any, project_id: str, *, author: str = "", overwrite: bool = False) -> dict[str, Any]:
    path = _engine_path(root, project_id)
    if path.exists() and not overwrite:
        return load_interpolation_engine(root, project_id)
    payload = build_default_interpolation_seed(author=author)
    _json_write(path, payload)
    append_project_history(root, project_id, "interpolation.seed", "Seeded interpolation engine")
    return payload


def _cell_to_dict(cell: InterpolatedCell) -> dict[str, Any]:
    return {
        "x": cell.x,
        "y": cell.y,
        "z": cell.z,
        "i": cell.i,
        "j": cell.j,
        "k": cell.k,
        "value": cell.value,
        "method": cell.method,
        "neighbor_count": cell.neighbor_count,
        "distance_to_nearest": cell.distance_to_nearest,
        "confidence": cell.confidence,
    }


def build_interpolated_cells_table(cells: Iterable[InterpolatedCell]) -> list[dict[str, Any]]:
    return [_cell_to_dict(cell) for cell in cells]


def build_interpolation_job_table(jobs: Iterable[InterpolationJobSpec]) -> list[dict[str, Any]]:
    return [
        {
            "name": job.name,
            "property": job.property_name,
            "zone": job.zone_name,
            "method": job.method,
            "status": job.status,
            "source": job.source,
        }
        for job in jobs
    ]


def summarize_interpolation_result(cells: Iterable[InterpolatedCell]) -> dict[str, Any]:
    items = tuple(cells)
    values = [cell.value for cell in items if cell.value is not None]
    return {
        "cell_count": len(items),
        "estimated_count": len(values),
        "missing_count": len(items) - len(values),
        "min": round(min(values), 10) if values else None,
        "max": round(max(values), 10) if values else None,
        "mean": round(sum(values) / len(values), 10) if values else None,
        "average_confidence": round(sum(cell.confidence for cell in items) / len(items), 6) if items else None,
    }


def build_interpolation_manifest(root: Any = DEFAULT_PROJECTS_ROOT, project_id: str = DEFAULT_PROJECT_ID) -> InterpolationManifest:
    jobs = list_interpolation_jobs(root, project_id)
    warnings: list[str] = []
    if not jobs:
        warnings.append("Нет заданий интерполяции.")
    methods = {job.method for job in jobs}
    return InterpolationManifest(project_id=safe_project_id(project_id), generated_at=_now_iso(), job_count=len(jobs), method_count=len(methods), warnings=tuple(warnings))


def render_interpolation_markdown(root: Any = DEFAULT_PROJECTS_ROOT, project_id: str = DEFAULT_PROJECT_ID) -> str:
    manifest = build_interpolation_manifest(root, project_id)
    jobs = list_interpolation_jobs(root, project_id)
    lines = [
        "# Interpolation Engine Report",
        "",
        f"Project: `{manifest.project_id}`",
        f"Generated: `{manifest.generated_at}`",
        "",
        "## Summary",
        f"- Jobs: {manifest.job_count}",
        f"- Methods used: {manifest.method_count}",
        "",
        "## Registered Jobs",
    ]
    if jobs:
        lines.append("| Name | Property | Zone | Method | Status |")
        lines.append("|---|---:|---:|---:|---:|")
        for job in jobs:
            lines.append(f"| {job.name} | {job.property_name} | {job.zone_name or '-'} | {job.method} | {job.status} |")
    else:
        lines.append("No interpolation jobs registered.")
    if manifest.warnings:
        lines.extend(["", "## Warnings"])
        lines.extend(f"- {warning}" for warning in manifest.warnings)
    return "\n".join(lines) + "\n"
