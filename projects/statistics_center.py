from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd

from projects.project_manager import append_project_history
from projects.repository import DEFAULT_PROJECT_ID, DEFAULT_PROJECTS_ROOT, safe_project_id
from projects.well_cards import safe_well_id

PROJECT_STATISTICS_CENTER_FILE_NAME = "statistics_center.json"
STATISTICS_CORRELATION_METHODS = {"pearson", "spearman"}
STATISTICS_SOURCE_TYPES = {"las", "calculation", "csv", "excel", "core", "mud_log", "production", "manual"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _project_dir(root: Path | str, project_id: str) -> Path:
    return Path(root) / safe_project_id(project_id)


def _statistics_path(root: Path | str, project_id: str) -> Path:
    return _project_dir(root, project_id) / PROJECT_STATISTICS_CENTER_FILE_NAME


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


def _clean_text(value: Any, field_label: str, *, max_length: int = 160, required: bool = False) -> str:
    text = "" if value is None else str(value).strip()
    if required and not text:
        raise ValueError(f"{field_label}: значение обязательно.")
    if len(text) > max_length:
        raise ValueError(f"{field_label}: максимум {max_length} символов.")
    return text


def _safe_id(value: str, default: str = "statistics") -> str:
    raw = _clean_text(value, "ID", max_length=140) or default
    normalized = re.sub(r"[^0-9A-Za-zА-Яа-я_-]+", "-", raw).strip("-_").lower() or default
    return safe_well_id(normalized)


def _float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, str):
        value = value.strip().replace(",", ".")
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number


def _clean_source_type(value: Any) -> str:
    source_type = _clean_text(value, "Тип источника", max_length=40).lower() or "manual"
    if source_type not in STATISTICS_SOURCE_TYPES:
        raise ValueError(f"Тип источника должен быть одним из: {', '.join(sorted(STATISTICS_SOURCE_TYPES))}.")
    return source_type


def _clean_method(value: Any) -> str:
    method = _clean_text(value, "Метод корреляции", max_length=24).lower() or "pearson"
    if method not in STATISTICS_CORRELATION_METHODS:
        raise ValueError(f"Метод корреляции должен быть одним из: {', '.join(sorted(STATISTICS_CORRELATION_METHODS))}.")
    return method


def _numeric_frame(data_frame: pd.DataFrame, columns: Sequence[str] | None = None) -> pd.DataFrame:
    if not isinstance(data_frame, pd.DataFrame):
        raise TypeError("Ожидается pandas.DataFrame.")
    source = data_frame.copy()
    if columns is not None:
        missing = [column for column in columns if column not in source.columns]
        if missing:
            raise ValueError(f"Колонки не найдены: {', '.join(missing)}.")
        source = source[list(columns)]
    numeric = source.apply(pd.to_numeric, errors="coerce")
    numeric = numeric.select_dtypes(include="number")
    return numeric.dropna(axis=1, how="all")


def filter_statistics_depth_range(
    data_frame: pd.DataFrame,
    *,
    depth_column: str | None = None,
    min_depth: Any = None,
    max_depth: Any = None,
) -> pd.DataFrame:
    """Return a copy of rows inside a measured-depth interval.

    Filtering is optional. If no depth column or limits are supplied, the original
    rows are copied unchanged. Invalid depth values are treated as missing and are
    excluded only when at least one interval boundary is specified.
    """
    if not isinstance(data_frame, pd.DataFrame):
        raise TypeError("Ожидается pandas.DataFrame.")
    frame = data_frame.copy()
    if not depth_column or depth_column not in frame.columns:
        return frame
    low = _float_or_none(min_depth)
    high = _float_or_none(max_depth)
    if low is None and high is None:
        return frame
    if low is not None and high is not None and low > high:
        low, high = high, low
    depths = pd.to_numeric(frame[depth_column], errors="coerce")
    mask = depths.notna()
    if low is not None:
        mask &= depths >= low
    if high is not None:
        mask &= depths <= high
    return frame.loc[mask].copy()


@dataclass(frozen=True)
class StatisticsColumnSummary:
    column: str
    count: int
    missing: int
    minimum: float | None
    q1: float | None
    mean: float | None
    median: float | None
    q3: float | None
    maximum: float | None
    std: float | None
    variance: float | None
    skew: float | None
    kurtosis: float | None


@dataclass(frozen=True)
class HistogramBin:
    column: str
    left: float
    right: float
    count: int
    frequency: float


@dataclass(frozen=True)
class BoxplotSummary:
    column: str
    minimum: float | None
    q1: float | None
    median: float | None
    q3: float | None
    maximum: float | None
    iqr: float | None
    lower_fence: float | None
    upper_fence: float | None
    outliers: int


@dataclass(frozen=True)
class CrossplotPoint:
    x: float
    y: float
    depth: float | None = None
    label: str = ""


@dataclass(frozen=True)
class StatisticsReport:
    id: str
    name: str
    source_type: str
    source_id: str
    well_id: str = ""
    columns: tuple[str, ...] = ()
    rows: int = 0
    depth_column: str = ""
    min_depth: float | None = None
    max_depth: float | None = None
    correlation_method: str = "pearson"
    created_at: str = ""


@dataclass(frozen=True)
class StatisticsCenterSummary:
    reports: int
    columns: int
    source_types: int
    wells: int


def list_numeric_columns(data_frame: pd.DataFrame, *, exclude_depth: bool = False, depth_column: str | None = None) -> tuple[str, ...]:
    numeric = _numeric_frame(data_frame)
    columns = tuple(str(column) for column in numeric.columns)
    if exclude_depth and depth_column:
        return tuple(column for column in columns if column != depth_column)
    return columns


def calculate_descriptive_statistics(
    data_frame: pd.DataFrame,
    *,
    columns: Sequence[str] | None = None,
    depth_column: str | None = None,
    min_depth: Any = None,
    max_depth: Any = None,
) -> tuple[StatisticsColumnSummary, ...]:
    filtered = filter_statistics_depth_range(data_frame, depth_column=depth_column, min_depth=min_depth, max_depth=max_depth)
    numeric = _numeric_frame(filtered, columns)
    summaries: list[StatisticsColumnSummary] = []
    for column in numeric.columns:
        series = pd.to_numeric(numeric[column], errors="coerce")
        valid = series.dropna()
        if valid.empty:
            summaries.append(StatisticsColumnSummary(str(column), 0, int(series.isna().sum()), None, None, None, None, None, None, None, None, None, None))
            continue
        summaries.append(
            StatisticsColumnSummary(
                column=str(column),
                count=int(valid.count()),
                missing=int(series.isna().sum()),
                minimum=float(valid.min()),
                q1=float(valid.quantile(0.25)),
                mean=float(valid.mean()),
                median=float(valid.median()),
                q3=float(valid.quantile(0.75)),
                maximum=float(valid.max()),
                std=float(valid.std()) if valid.count() > 1 else 0.0,
                variance=float(valid.var()) if valid.count() > 1 else 0.0,
                skew=float(valid.skew()) if valid.count() > 2 else 0.0,
                kurtosis=float(valid.kurtosis()) if valid.count() > 3 else 0.0,
            )
        )
    return tuple(summaries)


def build_histogram_bins(
    data_frame: pd.DataFrame,
    column: str,
    *,
    bins: int = 10,
    depth_column: str | None = None,
    min_depth: Any = None,
    max_depth: Any = None,
) -> tuple[HistogramBin, ...]:
    if bins < 1 or bins > 200:
        raise ValueError("Количество интервалов histogram должно быть в диапазоне 1..200.")
    filtered = filter_statistics_depth_range(data_frame, depth_column=depth_column, min_depth=min_depth, max_depth=max_depth)
    numeric = _numeric_frame(filtered, [column])
    values = pd.to_numeric(numeric[column], errors="coerce").dropna()
    if values.empty:
        return ()
    counts = pd.cut(values, bins=bins, include_lowest=True).value_counts(sort=False)
    total = int(counts.sum())
    result: list[HistogramBin] = []
    for interval, count in counts.items():
        result.append(HistogramBin(column=str(column), left=float(interval.left), right=float(interval.right), count=int(count), frequency=float(count / total if total else 0.0)))
    return tuple(result)


def build_boxplot_summary(
    data_frame: pd.DataFrame,
    column: str,
    *,
    depth_column: str | None = None,
    min_depth: Any = None,
    max_depth: Any = None,
) -> BoxplotSummary:
    filtered = filter_statistics_depth_range(data_frame, depth_column=depth_column, min_depth=min_depth, max_depth=max_depth)
    numeric = _numeric_frame(filtered, [column])
    values = pd.to_numeric(numeric[column], errors="coerce").dropna()
    if values.empty:
        return BoxplotSummary(str(column), None, None, None, None, None, None, None, None, 0)
    q1 = float(values.quantile(0.25))
    q3 = float(values.quantile(0.75))
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    outliers = int(((values < lower) | (values > upper)).sum())
    return BoxplotSummary(str(column), float(values.min()), q1, float(values.median()), q3, float(values.max()), float(iqr), float(lower), float(upper), outliers)


def build_crossplot_points(
    data_frame: pd.DataFrame,
    x_column: str,
    y_column: str,
    *,
    depth_column: str | None = None,
    label_column: str | None = None,
    min_depth: Any = None,
    max_depth: Any = None,
    limit: int = 5000,
) -> tuple[CrossplotPoint, ...]:
    if limit < 1:
        raise ValueError("Лимит точек crossplot должен быть положительным.")
    filtered = filter_statistics_depth_range(data_frame, depth_column=depth_column, min_depth=min_depth, max_depth=max_depth)
    required = [x_column, y_column]
    if depth_column and depth_column in filtered.columns:
        required.append(depth_column)
    numeric = _numeric_frame(filtered, required)
    x_values = pd.to_numeric(numeric[x_column], errors="coerce")
    y_values = pd.to_numeric(numeric[y_column], errors="coerce")
    depth_values = pd.to_numeric(numeric[depth_column], errors="coerce") if depth_column and depth_column in numeric.columns else None
    labels = filtered[label_column].astype(str) if label_column and label_column in filtered.columns else None
    rows: list[CrossplotPoint] = []
    for idx in filtered.index:
        x = _float_or_none(x_values.get(idx))
        y = _float_or_none(y_values.get(idx))
        if x is None or y is None:
            continue
        depth = _float_or_none(depth_values.get(idx)) if depth_values is not None else None
        label = str(labels.get(idx)) if labels is not None else ""
        rows.append(CrossplotPoint(x=x, y=y, depth=depth, label=label))
        if len(rows) >= limit:
            break
    return tuple(rows)


def calculate_correlation_matrix(
    data_frame: pd.DataFrame,
    *,
    columns: Sequence[str] | None = None,
    method: str = "pearson",
    depth_column: str | None = None,
    min_depth: Any = None,
    max_depth: Any = None,
) -> pd.DataFrame:
    clean_method = _clean_method(method)
    filtered = filter_statistics_depth_range(data_frame, depth_column=depth_column, min_depth=min_depth, max_depth=max_depth)
    numeric = _numeric_frame(filtered, columns)
    if numeric.empty:
        return pd.DataFrame()
    return numeric.corr(method=clean_method)


def _report_from_dict(raw: dict[str, Any]) -> StatisticsReport:
    min_depth = _float_or_none(raw.get("min_depth"))
    max_depth = _float_or_none(raw.get("max_depth"))
    return StatisticsReport(
        id=_safe_id(str(raw.get("id", "statistics"))),
        name=_clean_text(raw.get("name"), "Название отчета", required=True),
        source_type=_clean_source_type(raw.get("source_type", "manual")),
        source_id=_clean_text(raw.get("source_id"), "Источник", max_length=160),
        well_id=_safe_id(str(raw.get("well_id", "")), "well") if raw.get("well_id") else "",
        columns=tuple(str(value) for value in raw.get("columns", []) if str(value).strip()),
        rows=max(0, int(raw.get("rows", 0) or 0)),
        depth_column=_clean_text(raw.get("depth_column"), "Колонка глубины", max_length=80),
        min_depth=min_depth,
        max_depth=max_depth,
        correlation_method=_clean_method(raw.get("correlation_method", "pearson")),
        created_at=str(raw.get("created_at", "")),
    )


def _report_to_dict(report: StatisticsReport) -> dict[str, Any]:
    return {
        "id": report.id,
        "name": report.name,
        "source_type": report.source_type,
        "source_id": report.source_id,
        "well_id": report.well_id,
        "columns": list(report.columns),
        "rows": report.rows,
        "depth_column": report.depth_column,
        "min_depth": report.min_depth,
        "max_depth": report.max_depth,
        "correlation_method": report.correlation_method,
        "created_at": report.created_at,
    }


def list_statistics_reports(root: Path | str = DEFAULT_PROJECTS_ROOT, project_id: str = DEFAULT_PROJECT_ID) -> tuple[StatisticsReport, ...]:
    payload = _json_read(_statistics_path(root, project_id), {"reports": []})
    rows = payload.get("reports", []) if isinstance(payload, dict) else []
    reports: list[StatisticsReport] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            reports.append(_report_from_dict(row))
        except (ValueError, TypeError):
            continue
    return tuple(sorted(reports, key=lambda item: item.created_at, reverse=True))


def save_statistics_report(
    root: Path | str,
    project_id: str,
    name: str,
    *,
    source_type: str = "manual",
    source_id: str = "",
    data_frame: pd.DataFrame | None = None,
    columns: Iterable[str] = (),
    report_id: str | None = None,
    well_id: str = "",
    depth_column: str = "",
    min_depth: Any = None,
    max_depth: Any = None,
    correlation_method: str = "pearson",
) -> StatisticsReport:
    clean_name = _clean_text(name, "Название отчета", required=True)
    clean_id = _safe_id(report_id or f"statistics-{clean_name.lower().replace(' ', '-')}")
    selected_columns = tuple(str(value) for value in columns if str(value).strip())
    rows = 0
    if data_frame is not None:
        filtered = filter_statistics_depth_range(data_frame, depth_column=depth_column or None, min_depth=min_depth, max_depth=max_depth)
        rows = int(len(filtered.index))
        if not selected_columns:
            selected_columns = list_numeric_columns(filtered, exclude_depth=True, depth_column=depth_column or None)
    report = StatisticsReport(
        id=clean_id,
        name=clean_name,
        source_type=_clean_source_type(source_type),
        source_id=_clean_text(source_id, "Источник", max_length=160),
        well_id=_safe_id(well_id, "well") if well_id else "",
        columns=tuple(selected_columns),
        rows=rows,
        depth_column=_clean_text(depth_column, "Колонка глубины", max_length=80),
        min_depth=_float_or_none(min_depth),
        max_depth=_float_or_none(max_depth),
        correlation_method=_clean_method(correlation_method),
        created_at=_utc_now(),
    )
    existing = [item for item in list_statistics_reports(root, project_id) if item.id != report.id]
    _json_write(_statistics_path(root, project_id), {"version": 1, "reports": [_report_to_dict(report), *[_report_to_dict(item) for item in existing]]})
    append_project_history(root, project_id, "statistics-center", f"Saved statistics report {clean_name}", object_type="statistics-report", object_id=report.id)
    return report


def summarize_statistics_center(root: Path | str = DEFAULT_PROJECTS_ROOT, project_id: str = DEFAULT_PROJECT_ID) -> StatisticsCenterSummary:
    reports = list_statistics_reports(root, project_id)
    return StatisticsCenterSummary(
        reports=len(reports),
        columns=len({column for report in reports for column in report.columns}),
        source_types=len({report.source_type for report in reports}),
        wells=len({report.well_id for report in reports if report.well_id}),
    )


def build_statistics_summary_table(summaries: Iterable[StatisticsColumnSummary]) -> list[dict[str, Any]]:
    return [
        {
            "Кривая": item.column,
            "Count": item.count,
            "Missing": item.missing,
            "Min": item.minimum,
            "Q1": item.q1,
            "Mean": item.mean,
            "Median": item.median,
            "Q3": item.q3,
            "Max": item.maximum,
            "Std": item.std,
            "Variance": item.variance,
            "Skew": item.skew,
            "Kurtosis": item.kurtosis,
        }
        for item in summaries
    ]


def build_histogram_table(bins: Iterable[HistogramBin]) -> list[dict[str, Any]]:
    return [
        {"Кривая": item.column, "От": item.left, "До": item.right, "Количество": item.count, "Частота": item.frequency}
        for item in bins
    ]


def build_statistics_reports_table(reports: Iterable[StatisticsReport]) -> list[dict[str, Any]]:
    return [
        {
            "Отчет": report.name,
            "ID": report.id,
            "Источник": report.source_type,
            "Объект": report.source_id or "—",
            "Скважина": report.well_id or "—",
            "Колонки": len(report.columns),
            "Строки": report.rows,
            "Глубина": f"{report.min_depth}–{report.max_depth}" if report.min_depth is not None or report.max_depth is not None else "весь интервал",
            "Корреляция": report.correlation_method,
            "Создано": report.created_at,
        }
        for report in reports
    ]
