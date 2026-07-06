from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd

from projects.repository import safe_project_id

PROJECT_DATA_QUALITY_FILE_NAME = "data_quality_reports.json"
SEVERITY_ORDER = {"info": 0, "warning": 1, "error": 2, "critical": 3}
DEPTH_COLUMN_CANDIDATES = ("DEPT", "DEPTH", "MD", "TVD", "TDEP")
PETROPHYSICAL_LIMITS = {
    "VSH": (0.0, 1.0),
    "PHIE": (0.0, 1.0),
    "PHIT": (0.0, 1.0),
    "SW": (0.0, 1.0),
    "PERM": (0.0, None),
    "NET_PAY": (0.0, 1.0),
}
COMMON_CURVE_LIMITS = {
    "GR": (0.0, 350.0),
    "RHOB": (1.0, 3.5),
    "NPHI": (-0.15, 1.0),
    "DT": (20.0, 240.0),
    "RT": (0.01, 100000.0),
    "C1": (0.0, None),
    "C2": (0.0, None),
    "C3": (0.0, None),
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _project_dir(root: Path | str, project_id: str) -> Path:
    return Path(root) / safe_project_id(project_id)


def _quality_path(root: Path | str, project_id: str) -> Path:
    return _project_dir(root, project_id) / PROJECT_DATA_QUALITY_FILE_NAME


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


def _clean_text(value: Any, default: str = "") -> str:
    return default if value is None else str(value).strip()


def _as_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _round_float(value: Any, digits: int = 6) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return round(number, digits)


def normalize_curve_name(name: Any) -> str:
    return _clean_text(name).upper().replace(".", "").replace(" ", "_")


def find_depth_column(df: pd.DataFrame, preferred: str | None = None) -> str | None:
    if df is None or df.empty:
        return None
    columns = list(df.columns)
    if preferred and preferred in columns:
        return preferred
    upper_map = {normalize_curve_name(col): col for col in columns}
    for candidate in DEPTH_COLUMN_CANDIDATES:
        if candidate in upper_map:
            return upper_map[candidate]
    return columns[0] if columns else None


@dataclass(frozen=True)
class QualityIssue:
    severity: str
    category: str
    code: str
    message: str
    object_type: str = "dataset"
    object_name: str = ""
    recommendation: str = ""

    def __post_init__(self) -> None:
        if self.severity not in SEVERITY_ORDER:
            raise ValueError("severity должен быть одним из: info, warning, error, critical")


@dataclass(frozen=True)
class CurveQualitySummary:
    curve: str
    count: int
    missing: int
    completeness: float
    minimum: float | None = None
    maximum: float | None = None
    mean: float | None = None
    std: float | None = None
    outliers: int = 0
    constant: bool = False


@dataclass(frozen=True)
class DataQualityReport:
    id: str
    name: str
    source_type: str = "dataset"
    source_id: str = ""
    created_at: str = ""
    issues: tuple[QualityIssue, ...] = ()
    curve_summaries: tuple[CurveQualitySummary, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def issue_count(self) -> int:
        return len(self.issues)

    @property
    def highest_severity(self) -> str:
        if not self.issues:
            return "info"
        return max((issue.severity for issue in self.issues), key=lambda item: SEVERITY_ORDER[item])


@dataclass(frozen=True)
class DataQualityDashboardSummary:
    reports: int
    issues: int
    critical: int
    errors: int
    warnings: int
    info: int
    highest_severity: str


def issue_to_dict(issue: QualityIssue) -> dict[str, Any]:
    return {
        "severity": issue.severity,
        "category": issue.category,
        "code": issue.code,
        "message": issue.message,
        "object_type": issue.object_type,
        "object_name": issue.object_name,
        "recommendation": issue.recommendation,
    }


def issue_from_dict(raw: Mapping[str, Any]) -> QualityIssue:
    return QualityIssue(
        severity=_clean_text(raw.get("severity"), "info"),
        category=_clean_text(raw.get("category"), "general"),
        code=_clean_text(raw.get("code"), "UNKNOWN"),
        message=_clean_text(raw.get("message"), ""),
        object_type=_clean_text(raw.get("object_type"), "dataset"),
        object_name=_clean_text(raw.get("object_name"), ""),
        recommendation=_clean_text(raw.get("recommendation"), ""),
    )


def curve_summary_to_dict(summary: CurveQualitySummary) -> dict[str, Any]:
    return {
        "curve": summary.curve,
        "count": summary.count,
        "missing": summary.missing,
        "completeness": summary.completeness,
        "minimum": summary.minimum,
        "maximum": summary.maximum,
        "mean": summary.mean,
        "std": summary.std,
        "outliers": summary.outliers,
        "constant": summary.constant,
    }


def curve_summary_from_dict(raw: Mapping[str, Any]) -> CurveQualitySummary:
    return CurveQualitySummary(
        curve=_clean_text(raw.get("curve")),
        count=int(raw.get("count", 0) or 0),
        missing=int(raw.get("missing", 0) or 0),
        completeness=float(raw.get("completeness", 0.0) or 0.0),
        minimum=_round_float(raw.get("minimum")),
        maximum=_round_float(raw.get("maximum")),
        mean=_round_float(raw.get("mean")),
        std=_round_float(raw.get("std")),
        outliers=int(raw.get("outliers", 0) or 0),
        constant=bool(raw.get("constant", False)),
    )


def report_to_dict(report: DataQualityReport) -> dict[str, Any]:
    return {
        "id": report.id,
        "name": report.name,
        "source_type": report.source_type,
        "source_id": report.source_id,
        "created_at": report.created_at,
        "issues": [issue_to_dict(issue) for issue in report.issues],
        "curve_summaries": [curve_summary_to_dict(summary) for summary in report.curve_summaries],
        "metadata": dict(report.metadata),
    }


def report_from_dict(raw: Mapping[str, Any]) -> DataQualityReport:
    return DataQualityReport(
        id=_clean_text(raw.get("id")),
        name=_clean_text(raw.get("name"), "Data quality report"),
        source_type=_clean_text(raw.get("source_type"), "dataset"),
        source_id=_clean_text(raw.get("source_id"), ""),
        created_at=_clean_text(raw.get("created_at"), ""),
        issues=tuple(issue_from_dict(item) for item in raw.get("issues", []) if isinstance(item, Mapping)),
        curve_summaries=tuple(curve_summary_from_dict(item) for item in raw.get("curve_summaries", []) if isinstance(item, Mapping)),
        metadata=raw.get("metadata", {}) if isinstance(raw.get("metadata", {}), Mapping) else {},
    )


def analyze_las_quality(df: pd.DataFrame, *, depth_column: str | None = None, expected_step: float | None = None) -> tuple[QualityIssue, ...]:
    issues: list[QualityIssue] = []
    if df is None or df.empty:
        return (
            QualityIssue("critical", "LAS QC", "EMPTY_DATASET", "Таблица LAS пуста.", recommendation="Загрузите LAS с секцией ~ASCII и числовыми данными."),
        )

    depth_col = find_depth_column(df, depth_column)
    if not depth_col or depth_col not in df.columns:
        return (
            QualityIssue("critical", "LAS QC", "MISSING_DEPTH", "Не найдена колонка глубины.", recommendation="Укажите DEPT/DEPTH/MD или назначьте колонку глубины вручную."),
        )

    depth = _as_numeric(df[depth_col])
    if depth.isna().all():
        issues.append(QualityIssue("critical", "LAS QC", "DEPTH_NOT_NUMERIC", "Глубина не является числовой.", "curve", depth_col))
        return tuple(issues)

    clean_depth = depth.dropna()
    if clean_depth.empty:
        issues.append(QualityIssue("critical", "LAS QC", "DEPTH_EMPTY", "Все значения глубины пустые.", "curve", depth_col))
        return tuple(issues)

    diffs = clean_depth.diff().dropna()
    if (diffs < 0).any() and not (diffs > 0).any():
        issues.append(QualityIssue("error", "LAS QC", "DEPTH_DECREASING", "Глубина убывает вниз по таблице.", "curve", depth_col, "Используйте Reverse Depth и сохраните LAS под новым именем."))
    elif (diffs < 0).any():
        issues.append(QualityIssue("critical", "LAS QC", "DEPTH_NON_MONOTONIC", "Глубина не монотонна.", "curve", depth_col, "Отсортируйте данные по глубине и проверьте дубликаты/разрывы."))

    duplicated = int(clean_depth.duplicated().sum())
    if duplicated:
        issues.append(QualityIssue("error", "LAS QC", "DEPTH_DUPLICATES", f"Найдено дублирующихся глубин: {duplicated}.", "curve", depth_col, "Удалите или агрегируйте повторяющиеся значения глубины."))

    missing_depth = int(depth.isna().sum())
    if missing_depth:
        issues.append(QualityIssue("error", "LAS QC", "DEPTH_MISSING", f"Пустые значения глубины: {missing_depth}.", "curve", depth_col))

    positive_diffs = diffs[diffs > 0].round(6)
    if not positive_diffs.empty:
        step = float(positive_diffs.mode().iloc[0])
        tolerance = max(abs(step) * 0.05, 1e-6)
        irregular = int((positive_diffs.sub(step).abs() > tolerance).sum())
        if irregular:
            issues.append(QualityIssue("warning", "LAS QC", "IRREGULAR_DEPTH_STEP", f"Нерегулярный шаг глубины: {irregular} интервалов отличаются от типового шага {round(step, 6)}.", "curve", depth_col, "Выполните resampling на единый шаг дискретизации."))
        if expected_step is not None and abs(step - expected_step) > tolerance:
            issues.append(QualityIssue("warning", "LAS QC", "UNEXPECTED_DEPTH_STEP", f"Типовой шаг {round(step, 6)} отличается от ожидаемого {expected_step}.", "curve", depth_col))

    empty_columns = [str(col) for col in df.columns if df[col].isna().all()]
    for col in empty_columns:
        issues.append(QualityIssue("warning", "Curve QC", "EMPTY_CURVE", "Кривая полностью пустая.", "curve", col, "Удалите кривую или проверьте импорт LAS."))

    return tuple(issues)


def analyze_curve_quality(df: pd.DataFrame, *, depth_column: str | None = None, outlier_iqr_factor: float = 3.0) -> tuple[CurveQualitySummary, ...]:
    if df is None or df.empty:
        return ()
    depth_col = find_depth_column(df, depth_column)
    summaries: list[CurveQualitySummary] = []
    for column in df.columns:
        if column == depth_col:
            continue
        series = _as_numeric(df[column])
        if series.notna().sum() == 0:
            summaries.append(CurveQualitySummary(str(column), int(len(series)), int(series.isna().sum()), 0.0))
            continue
        clean = series.dropna()
        q1 = clean.quantile(0.25)
        q3 = clean.quantile(0.75)
        iqr = q3 - q1
        if iqr and iqr == iqr:
            outliers = int(((clean < q1 - outlier_iqr_factor * iqr) | (clean > q3 + outlier_iqr_factor * iqr)).sum())
        else:
            outliers = 0
        summaries.append(
            CurveQualitySummary(
                curve=str(column),
                count=int(len(series)),
                missing=int(series.isna().sum()),
                completeness=round(float(series.notna().mean()), 6),
                minimum=_round_float(clean.min()),
                maximum=_round_float(clean.max()),
                mean=_round_float(clean.mean()),
                std=_round_float(clean.std(ddof=0)),
                outliers=outliers,
                constant=bool(clean.nunique(dropna=True) <= 1),
            )
        )
    return tuple(summaries)


def validate_curve_ranges(df: pd.DataFrame, *, limits: Mapping[str, tuple[float | None, float | None]] | None = None) -> tuple[QualityIssue, ...]:
    if df is None or df.empty:
        return ()
    merged_limits = {**COMMON_CURVE_LIMITS, **(limits or {})}
    issues: list[QualityIssue] = []
    normalized = {normalize_curve_name(col): col for col in df.columns}
    for canonical, (low, high) in merged_limits.items():
        if canonical not in normalized:
            continue
        column = normalized[canonical]
        series = _as_numeric(df[column]).dropna()
        if series.empty:
            continue
        invalid = pd.Series(False, index=series.index)
        if low is not None:
            invalid = invalid | (series < low)
        if high is not None:
            invalid = invalid | (series > high)
        count = int(invalid.sum())
        if count:
            issues.append(QualityIssue("warning", "Curve QC", "CURVE_RANGE_OUTLIERS", f"{count} значений вне ожидаемого диапазона {low}–{high}.", "curve", str(column), "Проверьте единицы измерения, NULL value и выбросы."))
    return tuple(issues)


def validate_petrophysical_results(df: pd.DataFrame) -> tuple[QualityIssue, ...]:
    return validate_curve_ranges(df, limits=PETROPHYSICAL_LIMITS)


def validate_geological_intervals(rows: Iterable[Mapping[str, Any]]) -> tuple[QualityIssue, ...]:
    issues: list[QualityIssue] = []
    by_well: dict[str, list[tuple[float, float, str]]] = {}
    for raw in rows:
        name = _clean_text(raw.get("name") or raw.get("zone_name"), "zone")
        well_id = _clean_text(raw.get("well_id"), "field") or "field"
        top = _round_float(raw.get("top_md_m") if "top_md_m" in raw else raw.get("top"))
        base = _round_float(raw.get("base_md_m") if "base_md_m" in raw else raw.get("base"))
        if top is None or base is None:
            issues.append(QualityIssue("warning", "Geological QC", "ZONE_DEPTH_MISSING", "Не задана кровля или подошва зоны.", "zone", name))
            continue
        if base <= top:
            issues.append(QualityIssue("error", "Geological QC", "ZONE_ORDER_INVALID", "Подошва зоны должна быть глубже кровли.", "zone", name))
            continue
        by_well.setdefault(well_id, []).append((top, base, name))

    for well_id, intervals in by_well.items():
        ordered = sorted(intervals, key=lambda item: item[0])
        for previous, current in zip(ordered, ordered[1:]):
            prev_top, prev_base, prev_name = previous
            top, base, name = current
            if top < prev_base:
                issues.append(QualityIssue("error", "Geological QC", "ZONE_OVERLAP", f"Зоны пересекаются в скважине {well_id}: {prev_name} и {name}.", "zone", name, "Проверьте tops/horizons и границы интервалов."))
            elif top > prev_base:
                issues.append(QualityIssue("info", "Geological QC", "ZONE_GAP", f"Разрыв между зонами в скважине {well_id}: {round(top - prev_base, 6)} м.", "zone", name))
    return tuple(issues)


def build_data_quality_report(
    df: pd.DataFrame,
    *,
    name: str = "Data Quality Report",
    source_type: str = "las",
    source_id: str = "",
    depth_column: str | None = None,
    expected_step: float | None = None,
    geological_rows: Iterable[Mapping[str, Any]] | None = None,
) -> DataQualityReport:
    issues = list(analyze_las_quality(df, depth_column=depth_column, expected_step=expected_step))
    issues.extend(validate_curve_ranges(df))
    issues.extend(validate_petrophysical_results(df))
    if geological_rows is not None:
        issues.extend(validate_geological_intervals(geological_rows))
    curve_summaries = analyze_curve_quality(df, depth_column=depth_column)
    report_id = f"dq-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    return DataQualityReport(
        id=report_id,
        name=_clean_text(name, "Data Quality Report"),
        source_type=_clean_text(source_type, "las"),
        source_id=_clean_text(source_id, ""),
        created_at=_utc_now(),
        issues=tuple(issues),
        curve_summaries=curve_summaries,
        metadata={"rows": int(len(df)) if df is not None else 0, "columns": list(map(str, df.columns)) if df is not None else []},
    )


def save_data_quality_report(root: Path | str, project_id: str, report: DataQualityReport) -> DataQualityReport:
    path = _quality_path(root, project_id)
    payload = _json_read(path, [])
    if not isinstance(payload, list):
        payload = []
    payload = [item for item in payload if not (isinstance(item, Mapping) and item.get("id") == report.id)]
    payload.insert(0, report_to_dict(report))
    _json_write(path, payload)
    return report


def list_data_quality_reports(root: Path | str, project_id: str) -> tuple[DataQualityReport, ...]:
    payload = _json_read(_quality_path(root, project_id), [])
    if not isinstance(payload, list):
        return ()
    return tuple(report_from_dict(item) for item in payload if isinstance(item, Mapping))


def summarize_data_quality_reports(reports: Sequence[DataQualityReport]) -> DataQualityDashboardSummary:
    counts = {"critical": 0, "error": 0, "warning": 0, "info": 0}
    for report in reports:
        for issue in report.issues:
            counts[issue.severity] += 1
    highest = "info"
    for severity, count in counts.items():
        if count and SEVERITY_ORDER[severity] > SEVERITY_ORDER[highest]:
            highest = severity
    return DataQualityDashboardSummary(
        reports=len(reports),
        issues=sum(counts.values()),
        critical=counts["critical"],
        errors=counts["error"],
        warnings=counts["warning"],
        info=counts["info"],
        highest_severity=highest,
    )


def build_quality_issue_table(issues: Iterable[QualityIssue]) -> list[dict[str, Any]]:
    return [
        {
            "Severity": issue.severity,
            "Категория": issue.category,
            "Код": issue.code,
            "Объект": issue.object_name,
            "Тип объекта": issue.object_type,
            "Описание": issue.message,
            "Рекомендация": issue.recommendation,
        }
        for issue in issues
    ]


def build_curve_quality_table(summaries: Iterable[CurveQualitySummary]) -> list[dict[str, Any]]:
    return [
        {
            "Кривая": item.curve,
            "Count": item.count,
            "Missing": item.missing,
            "Completeness": item.completeness,
            "Min": item.minimum,
            "Max": item.maximum,
            "Mean": item.mean,
            "Std": item.std,
            "Outliers": item.outliers,
            "Constant": item.constant,
        }
        for item in summaries
    ]


def build_quality_report_table(reports: Iterable[DataQualityReport]) -> list[dict[str, Any]]:
    return [
        {
            "ID": report.id,
            "Название": report.name,
            "Источник": report.source_type,
            "Объект": report.source_id,
            "Дата": report.created_at,
            "Проблем": report.issue_count,
            "Макс. уровень": report.highest_severity,
            "Кривых": len(report.curve_summaries),
        }
        for report in reports
    ]


def export_quality_report_json(report: DataQualityReport) -> str:
    return json.dumps(report_to_dict(report), ensure_ascii=False, indent=2)


def export_quality_report_html(report: DataQualityReport) -> str:
    issue_rows = "".join(
        f"<tr><td>{issue.severity}</td><td>{issue.category}</td><td>{issue.code}</td><td>{issue.object_name}</td><td>{issue.message}</td><td>{issue.recommendation}</td></tr>"
        for issue in report.issues
    )
    curve_rows = "".join(
        f"<tr><td>{summary.curve}</td><td>{summary.count}</td><td>{summary.missing}</td><td>{summary.completeness}</td><td>{summary.minimum}</td><td>{summary.maximum}</td><td>{summary.outliers}</td></tr>"
        for summary in report.curve_summaries
    )
    return f"""<!doctype html>
<html lang=\"ru\">
<head><meta charset=\"utf-8\"><title>{report.name}</title></head>
<body>
<h1>{report.name}</h1>
<p><strong>Источник:</strong> {report.source_type} / {report.source_id}</p>
<p><strong>Создан:</strong> {report.created_at}</p>
<h2>Проблемы качества</h2>
<table border=\"1\" cellspacing=\"0\" cellpadding=\"4\"><tr><th>Severity</th><th>Категория</th><th>Код</th><th>Объект</th><th>Описание</th><th>Рекомендация</th></tr>{issue_rows}</table>
<h2>Качество кривых</h2>
<table border=\"1\" cellspacing=\"0\" cellpadding=\"4\"><tr><th>Кривая</th><th>Count</th><th>Missing</th><th>Completeness</th><th>Min</th><th>Max</th><th>Outliers</th></tr>{curve_rows}</table>
</body></html>"""
