from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

import pandas as pd


FILL_STRATEGIES: tuple[str, ...] = ("empty", "top", "bottom", "average", "linear")


@dataclass(frozen=True)
class DepthGap:
    start_depth: float
    end_depth: float
    missing_depths: tuple[float, ...]


@dataclass(frozen=True)
class DepthStepOutlier:
    from_depth: float
    to_depth: float
    step: float
    expected_step: float | None = None


@dataclass(frozen=True)
class DepthStepReport:
    step_count: int
    min_step: float | None
    max_step: float | None
    most_common_step: float | None
    outliers: tuple[DepthStepOutlier, ...] = ()


@dataclass(frozen=True)
class DepthDiagnostics:
    depth_column: str
    row_count: int
    valid_depth_count: int
    null_depth_count: int
    min_depth: float | None
    max_depth: float | None
    inferred_step: float | None
    step_report: DepthStepReport = DepthStepReport(0, None, None, None)
    duplicate_depths: tuple[float, ...] = ()
    reverse_step_count: int = 0
    gaps: tuple[DepthGap, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class DepthDirectionFixResult:
    data: pd.DataFrame
    depth_column: str
    before_first_depth: float | None = None
    before_last_depth: float | None = None
    after_first_depth: float | None = None
    after_last_depth: float | None = None
    direction_fixed: bool = False
    operation_log: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class LasResampleResult:
    data: pd.DataFrame
    diagnostics: DepthDiagnostics
    added_depths: tuple[float, ...] = ()
    fill_strategy: str = "empty"
    depth_order_fixed: bool = False
    warnings: tuple[str, ...] = ()


def _to_decimal(value) -> Decimal:
    try:
        normalized = str(value).strip().replace(",", ".")
        decimal_value = Decimal(normalized)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Некорректное числовое значение глубины или шага: {value!r}") from exc

    if not decimal_value.is_finite():
        raise ValueError(f"Некорректное числовое значение глубины или шага: {value!r}")
    return decimal_value


def _to_float(value: Decimal) -> float:
    return float(value.normalize())


def _round_depth(value: float) -> float:
    return round(float(value), 10)


def _coerce_depth_series(df: pd.DataFrame, depth_column: str) -> pd.Series:
    if depth_column not in df.columns:
        raise ValueError(f"Колонка глубины {depth_column!r} не найдена.")
    return pd.to_numeric(df[depth_column], errors="coerce")


def _infer_step(sorted_depths: pd.Series) -> float | None:
    diffs = sorted_depths.diff().dropna()
    positive_diffs = diffs[diffs > 0].round(10)
    if positive_diffs.empty:
        return None
    return float(positive_diffs.value_counts().idxmax())


def fix_depth_direction(
    df: pd.DataFrame,
    depth_column: str = "depth",
    *,
    target_direction: str = "increasing",
    drop_non_numeric_depths: bool = True,
) -> DepthDirectionFixResult:
    """Normalize LAS row order by depth without mutating the source dataframe.

    LAS interpretation screens usually expect depth to increase from top to
    bottom. Some LAS files arrive in reverse order where the first row is the
    deepest sample and depth decreases down the table. This helper gives the
    editor an explicit, auditable operation for that case and keeps NULL-depth
    rows out of the saved engineering version by default.
    """

    if depth_column not in df.columns:
        raise ValueError(f"Колонка глубины {depth_column!r} не найдена.")

    normalized_direction = str(target_direction).strip().lower()
    if normalized_direction not in {"increasing", "decreasing"}:
        raise ValueError("Направление глубины должно быть increasing или decreasing.")

    working = df.copy()
    working[depth_column] = pd.to_numeric(working[depth_column], errors="coerce")
    valid_depths = working[depth_column].dropna()
    warnings: list[str] = []
    log: list[str] = []

    if valid_depths.empty:
        return DepthDirectionFixResult(
            data=working.reset_index(drop=True),
            depth_column=depth_column,
            operation_log=("Depth direction was not changed: no numeric depths.",),
            warnings=("Нет числовых глубин для исправления направления.",),
        )

    before_first = float(valid_depths.iloc[0])
    before_last = float(valid_depths.iloc[-1])
    expected_increasing = normalized_direction == "increasing"
    already_ordered = bool(valid_depths.is_monotonic_increasing if expected_increasing else valid_depths.is_monotonic_decreasing)

    if drop_non_numeric_depths:
        before_rows = len(working)
        working = working.dropna(subset=[depth_column]).copy()
        removed = before_rows - len(working)
        if removed:
            log.append(f"Rows without numeric depth removed before direction fix: {removed}.")
            warnings.append("Строки без числовой глубины не включены в исправленный LAS.")

    sorted_df = working.sort_values(
        by=depth_column,
        ascending=expected_increasing,
        kind="mergesort",
        na_position="last",
    ).reset_index(drop=True)

    after_depths = sorted_df[depth_column].dropna()
    after_first = float(after_depths.iloc[0]) if not after_depths.empty else None
    after_last = float(after_depths.iloc[-1]) if not after_depths.empty else None
    direction_fixed = not already_ordered or not working.index.equals(sorted_df.index)

    if direction_fixed:
        direction_label = "ascending" if expected_increasing else "descending"
        log.append(f"Depth direction fixed: rows sorted by depth in {direction_label} order.")
    else:
        log.append("Depth direction already matches the selected order.")

    return DepthDirectionFixResult(
        data=sorted_df,
        depth_column=depth_column,
        before_first_depth=before_first,
        before_last_depth=before_last,
        after_first_depth=after_first,
        after_last_depth=after_last,
        direction_fixed=direction_fixed,
        operation_log=tuple(log),
        warnings=tuple(dict.fromkeys(warnings)),
    )


def build_depth_step_report(
    sorted_depths: pd.Series,
    expected_step=None,
    tolerance: float = 1e-9,
) -> DepthStepReport:
    """Build a compact quality report for depth increments.

    The report is based on sorted unique depths. It is intentionally separated
    from resampling so the editor can show problems before changing the data.
    """

    if sorted_depths.empty or len(sorted_depths) < 2:
        return DepthStepReport(0, None, None, None)

    diffs = sorted_depths.diff().dropna().round(10)
    positive_diffs = diffs[diffs > 0]
    if positive_diffs.empty:
        return DepthStepReport(0, None, None, None)

    expected_value = float(_to_decimal(expected_step)) if expected_step is not None else None
    common_step = float(positive_diffs.value_counts().idxmax())
    reference_step = expected_value if expected_value is not None else common_step

    outliers: list[DepthStepOutlier] = []
    for index in range(1, len(sorted_depths)):
        previous = float(sorted_depths.iloc[index - 1])
        current = float(sorted_depths.iloc[index])
        step = _round_depth(current - previous)
        if step <= 0:
            continue
        if abs(step - reference_step) > tolerance:
            outliers.append(
                DepthStepOutlier(
                    from_depth=previous,
                    to_depth=current,
                    step=step,
                    expected_step=reference_step,
                )
            )

    return DepthStepReport(
        step_count=int(len(positive_diffs)),
        min_step=float(positive_diffs.min()),
        max_step=float(positive_diffs.max()),
        most_common_step=common_step,
        outliers=tuple(outliers),
    )


def build_depth_grid(start_depth, end_depth, step) -> tuple[float, ...]:
    start = _to_decimal(start_depth)
    end = _to_decimal(end_depth)
    depth_step = _to_decimal(step)

    if depth_step <= 0:
        raise ValueError("Шаг глубины должен быть больше 0.")
    if start > end:
        raise ValueError("Начальная глубина не может быть больше конечной.")

    values: list[float] = []
    current = start
    while current <= end:
        values.append(_to_float(current))
        current += depth_step

    return tuple(values)


def diagnose_depths(
    df: pd.DataFrame,
    depth_column: str = "depth",
    expected_step=None,
) -> DepthDiagnostics:
    depths = _coerce_depth_series(df, depth_column)
    valid_depths = depths.dropna()
    warnings: list[str] = []

    null_depth_count = int(depths.isna().sum())
    if null_depth_count:
        warnings.append(f"Колонка {depth_column}: пустых или нечисловых глубин: {null_depth_count}.")

    if valid_depths.empty:
        return DepthDiagnostics(
            depth_column=depth_column,
            row_count=len(df),
            valid_depth_count=0,
            null_depth_count=null_depth_count,
            min_depth=None,
            max_depth=None,
            inferred_step=None,
            step_report=DepthStepReport(0, None, None, None),
            warnings=tuple(warnings + ["Нет числовых глубин для проверки."]),
        )

    rounded_depths = valid_depths.map(_round_depth)
    duplicate_depths = tuple(sorted(float(value) for value in rounded_depths[rounded_depths.duplicated()].unique()))
    if duplicate_depths:
        warnings.append("Найдены дубликаты глубин: " + ", ".join(str(value) for value in duplicate_depths) + ".")

    ordered_diffs = valid_depths.diff().dropna()
    reverse_step_count = int((ordered_diffs < 0).sum())
    if reverse_step_count:
        warnings.append(f"Найдены шаги глубины в обратном порядке: {reverse_step_count}.")

    sorted_unique = pd.Series(sorted(rounded_depths.drop_duplicates()))
    inferred_step = _infer_step(sorted_unique)
    step_report = build_depth_step_report(sorted_unique, expected_step=expected_step)

    if step_report.min_step is not None and step_report.max_step is not None and step_report.min_step != step_report.max_step:
        warnings.append(
            "Найден неравномерный шаг глубины: "
            f"минимальный {step_report.min_step}, максимальный {step_report.max_step}."
        )
    if step_report.outliers:
        warnings.append(f"Найдены выбросы шага глубины: {len(step_report.outliers)}.")

    gaps: list[DepthGap] = []
    if expected_step is not None:
        step_value = float(_to_decimal(expected_step))
        if step_value <= 0:
            raise ValueError("Ожидаемый шаг глубины должен быть больше 0.")
        for previous, current in zip(sorted_unique, sorted_unique.iloc[1:]):
            if current - previous <= step_value + 1e-9:
                continue
            missing = build_depth_grid(_round_depth(previous + step_value), _round_depth(current - step_value), step_value)
            if missing:
                gaps.append(DepthGap(float(previous), float(current), missing))
        if gaps:
            warnings.append(f"Найдены пропуски глубины по шагу {step_value}: {len(gaps)} интервалов.")

    return DepthDiagnostics(
        depth_column=depth_column,
        row_count=len(df),
        valid_depth_count=int(valid_depths.count()),
        null_depth_count=null_depth_count,
        min_depth=float(valid_depths.min()),
        max_depth=float(valid_depths.max()),
        inferred_step=inferred_step,
        step_report=step_report,
        duplicate_depths=duplicate_depths,
        reverse_step_count=reverse_step_count,
        gaps=tuple(gaps),
        warnings=tuple(warnings),
    )






@dataclass(frozen=True)
class ManualDepthRowsResult:
    data: pd.DataFrame
    added_depths: tuple[float, ...] = ()
    operation_log: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

@dataclass(frozen=True)
class LasEditPreview:
    before_rows: int
    after_rows: int
    before_columns: int
    after_columns: int
    added_rows: int = 0
    removed_rows: int = 0
    changed_cells: int = 0
    changed_columns: tuple[str, ...] = ()


@dataclass(frozen=True)
class LasEditAuditEntry:
    stage: str
    action: str
    details: str


def build_las_edit_preview(before: pd.DataFrame, after: pd.DataFrame) -> LasEditPreview:
    """Return a compact before/after summary for LAS editor changes.

    The function compares data by row position and column name. It is not a
    geological interpretation tool; it only gives the user a quick audit view
    before saving a prepared LAS version.
    """

    before_df = before.copy() if before is not None else pd.DataFrame()
    after_df = after.copy() if after is not None else pd.DataFrame()

    common_columns = [column for column in before_df.columns if column in after_df.columns]
    common_rows = min(len(before_df), len(after_df))
    changed_columns: list[str] = []
    changed_cells = 0

    for column in common_columns:
        left = before_df[column].iloc[:common_rows].reset_index(drop=True)
        right = after_df[column].iloc[:common_rows].reset_index(drop=True)
        left_values = left.astype("object").where(~pd.isna(left), "__NA__")
        right_values = right.astype("object").where(~pd.isna(right), "__NA__")
        changed_mask = left_values != right_values
        changed_count = int(changed_mask.sum())
        if changed_count:
            changed_cells += changed_count
            changed_columns.append(str(column))

    return LasEditPreview(
        before_rows=len(before_df),
        after_rows=len(after_df),
        before_columns=len(before_df.columns),
        after_columns=len(after_df.columns),
        added_rows=max(len(after_df) - len(before_df), 0),
        removed_rows=max(len(before_df) - len(after_df), 0),
        changed_cells=changed_cells,
        changed_columns=tuple(changed_columns),
    )


def build_las_edit_audit_log(
    *,
    depth_column: str,
    target_step,
    fill_strategy: str,
    bulk_operation_log: tuple[str, ...] | list[str] = (),
    manual_interval_log: tuple[str, ...] | list[str] = (),
    added_depths: tuple[float, ...] | list[float] = (),
    manual_preview: LasEditPreview | None = None,
) -> tuple[LasEditAuditEntry, ...]:
    """Build a saveable audit trail for a prepared LAS version."""

    entries: list[LasEditAuditEntry] = [
        LasEditAuditEntry(
            stage="configuration",
            action="Depth curve selected",
            details=f"Depth column: {depth_column}",
        ),
        LasEditAuditEntry(
            stage="configuration",
            action="Target depth step selected",
            details=f"Target step: {target_step}",
        ),
        LasEditAuditEntry(
            stage="configuration",
            action="Fill strategy selected",
            details=f"Fill strategy: {fill_strategy}",
        ),
    ]

    for item in bulk_operation_log:
        entries.append(LasEditAuditEntry(stage="bulk", action="Batch operation", details=str(item)))

    for item in manual_interval_log:
        entries.append(
            LasEditAuditEntry(
                stage="manual-interval",
                action="Manual depth rows insertion",
                details=str(item),
            )
        )

    if added_depths:
        entries.append(
            LasEditAuditEntry(
                stage="resample",
                action="Depth grid rows added",
                details=f"Added depth rows: {len(tuple(added_depths))}",
            )
        )

    if manual_preview is not None:
        entries.append(
            LasEditAuditEntry(
                stage="manual",
                action="Manual editor preview",
                details=(
                    f"Rows {manual_preview.before_rows} -> {manual_preview.after_rows}; "
                    f"changed cells: {manual_preview.changed_cells}; "
                    f"changed columns: {', '.join(manual_preview.changed_columns) or 'none'}"
                ),
            )
        )

    return tuple(entries)




@dataclass(frozen=True)
class LasEditorHint:
    topic: str
    status: str
    message: str
    action: str


def build_las_editor_hints(
    diagnostics: DepthDiagnostics,
    *,
    added_depth_count: int = 0,
    fill_strategy: str = "empty",
    bulk_operation_log: tuple[str, ...] | list[str] = (),
    manual_interval_log: tuple[str, ...] | list[str] = (),
    preview: LasEditPreview | None = None,
    saved_to_project: bool = False,
    exported: bool = False,
) -> tuple[LasEditorHint, ...]:
    """Return checkable user hints for the LAS editor workflow.

    Hints are deliberately rule-based. They explain what the editor observed,
    why it matters for calculations/correlation, and which manual action the
    engineer should take before saving or exporting a prepared LAS version.
    """

    hints: list[LasEditorHint] = []

    def add(topic: str, status: str, message: str, action: str) -> None:
        hints.append(LasEditorHint(topic=topic, status=status, message=message, action=action))

    step_report = diagnostics.step_report
    if step_report.step_count == 0:
        add(
            "Шаг глубины",
            "warning",
            "Недостаточно числовых глубин для проверки шага.",
            f"Проверьте колонку `{diagnostics.depth_column}` и строку заголовков перед сохранением версии.",
        )
    elif step_report.outliers or (step_report.min_step is not None and step_report.max_step is not None and step_report.min_step != step_report.max_step):
        add(
            "Шаг глубины",
            "warning",
            (
                f"Шаг глубины неоднородный: частый шаг {step_report.most_common_step}, "
                f"минимальный {step_report.min_step}, максимальный {step_report.max_step}."
            ),
            "Проверьте выбросы шага, затем используйте сортировку, удаление дублей или ручное добавление строк только на проблемном интервале.",
        )
    else:
        add(
            "Шаг глубины",
            "ok",
            f"Шаг глубины выглядит согласованным: {step_report.most_common_step}.",
            "Можно переходить к проверке NULL и сохранению подготовленной версии.",
        )

    if diagnostics.gaps:
        first_gap = diagnostics.gaps[0]
        add(
            "Пропуски глубины",
            "warning",
            f"Найдено интервалов с пропущенными глубинами: {len(diagnostics.gaps)}.",
            f"Начните проверку с интервала {first_gap.start_depth}–{first_gap.end_depth}; не заполняйте его автоматически без проверки соседних кривых.",
        )
    elif added_depth_count:
        add(
            "Пропуски глубины",
            "review",
            f"Редактор добавил строк глубины: {added_depth_count}.",
            "Откройте предпросмотр до/после и убедитесь, что стратегия заполнения не исказила газовые пики.",
        )
    else:
        add(
            "Пропуски глубины",
            "ok",
            "Пропуски по выбранному шагу не обнаружены.",
            "Дополнительное ручное добавление строк не требуется, если интервал выбран корректно.",
        )

    if diagnostics.null_depth_count:
        add(
            "NULL и глубина",
            "warning",
            f"В колонке глубины есть пустые или нечисловые значения: {diagnostics.null_depth_count}.",
            "Исправьте строки с пустой глубиной или удалите их до расчета; глубина не должна заполняться интерполяцией без контроля.",
        )

    null_replacement_log = [item for item in bulk_operation_log if "NULL" in str(item).upper()]
    if null_replacement_log:
        add(
            "NULL-значения",
            "review",
            str(null_replacement_log[-1]),
            "Проверьте, что заменяемое значение действительно является LAS NULL, а не реальным измерением конкретного прибора.",
        )
    else:
        add(
            "NULL-значения",
            "info",
            "Замена LAS NULL не применялась или не изменила таблицу.",
            "Если в LAS используется другое NULL-значение, укажите его явно перед расчетом.",
        )

    if manual_interval_log:
        add(
            "Ручное заполнение",
            "review",
            "; ".join(str(item) for item in manual_interval_log),
            f"Проверьте добавленные строки в интервале и стратегию заполнения `{fill_strategy}` перед сохранением версии.",
        )
    else:
        add(
            "Ручное заполнение",
            "info",
            "Ручное добавление строк по интервалу не применялось.",
            "Используйте его только для точечной подготовки проблемного участка, а не для автоматического изменения всего LAS.",
        )

    if preview is not None and (preview.added_rows or preview.removed_rows or preview.changed_cells):
        add(
            "Предпросмотр правок",
            "review",
            (
                f"После ручной правки: добавлено строк {preview.added_rows}, "
                f"удалено {preview.removed_rows}, изменено ячеек {preview.changed_cells}."
            ),
            "Сверьте измененные колонки и сохраните версию только после проверки, что правки не затронули исходные пики случайно.",
        )
    else:
        add(
            "Предпросмотр правок",
            "ok",
            "Ручные изменения после автоматической подготовки не обнаружены.",
            "Журнал правок всё равно сохранит настройки шага, заполнения и массовых операций.",
        )

    if diagnostics.duplicate_depths:
        add(
            "Дубли глубины",
            "warning",
            f"Найдены дубли глубины: {len(diagnostics.duplicate_depths)} уникальных значений.",
            "Удалите дубли только после проверки, какую строку нужно оставить: первую, усредненную или исправленную вручную.",
        )

    if diagnostics.reverse_step_count:
        add(
            "Порядок глубины",
            "warning",
            f"Найдены обратные шаги глубины: {diagnostics.reverse_step_count}.",
            "Отсортируйте глубину и проверьте, не смешаны ли в файле разные проходки или секции.",
        )

    add(
        "Сохранение скважины",
        "info" if not saved_to_project else "ok",
        "Подготовленный LAS сохраняется как отдельная версия скважины с журналом правок.",
        "Перед сохранением заполните название скважины, версию и комментарий так, чтобы позже было понятно, какие операции применялись.",
    )

    add(
        "Выгрузка данных",
        "info" if not exported else "ok",
        "CSV/LAS/XLSX выгрузки нужны для передачи подготовленных данных вне приложения.",
        "После экспорта откройте файл в стороннем просмотрщике и проверьте глубину, NULL и единицы измерения перед отправкой коллегам.",
    )

    return tuple(hints)


@dataclass(frozen=True)
class LasBulkOperationResult:
    data: pd.DataFrame
    diagnostics: DepthDiagnostics
    operation_log: tuple[str, ...] = ()
    monotonic: bool = True
    warnings: tuple[str, ...] = ()



@dataclass(frozen=True)
class DepthIntegrityReport:
    depth_column: str
    row_count: int
    start_depth: float | None
    stop_depth: float | None
    step: float | None
    monotonic_increasing: bool
    duplicate_count: int = 0
    null_depth_count: int = 0
    nan_value_count: int = 0
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class DepthSamplingOperationResult:
    data: pd.DataFrame
    operation_log: tuple[str, ...] = ()
    integrity: DepthIntegrityReport | None = None
    warnings: tuple[str, ...] = ()


def validate_depth_integrity(df: pd.DataFrame, depth_column: str = "depth") -> DepthIntegrityReport:
    """Validate the depth curve after an editor operation.

    The report is intentionally small and serializable so it can be shown in
    Streamlit, written into LAS edit metadata, and reused by tests.
    """

    if depth_column not in df.columns:
        raise ValueError(f"Колонка глубины {depth_column!r} не найдена.")

    depths = pd.to_numeric(df[depth_column], errors="coerce")
    valid = depths.dropna()
    warnings: list[str] = []
    null_count = int(depths.isna().sum())
    duplicate_count = int(valid.duplicated().sum())
    monotonic = bool(valid.is_monotonic_increasing) if not valid.empty else False
    nan_values = int(df.drop(columns=[depth_column], errors="ignore").isna().sum().sum())

    if null_count:
        warnings.append(f"Пустые или нечисловые глубины: {null_count}.")
    if duplicate_count:
        warnings.append(f"Дубликаты глубины: {duplicate_count}.")
    if not valid.empty and not monotonic:
        warnings.append("Глубина не растет монотонно сверху вниз.")

    sorted_unique = pd.Series(sorted(valid.map(_round_depth).drop_duplicates()))
    step = _infer_step(sorted_unique)

    return DepthIntegrityReport(
        depth_column=depth_column,
        row_count=len(df),
        start_depth=float(valid.iloc[0]) if not valid.empty else None,
        stop_depth=float(valid.iloc[-1]) if not valid.empty else None,
        step=step,
        monotonic_increasing=monotonic,
        duplicate_count=duplicate_count,
        null_depth_count=null_count,
        nan_value_count=nan_values,
        warnings=tuple(warnings),
    )


def shift_depth_values(df: pd.DataFrame, depth_column: str = "depth", offset=0.0) -> DepthSamplingOperationResult:
    """Shift measured depth by a constant offset without mutating the input."""

    if depth_column not in df.columns:
        raise ValueError(f"Колонка глубины {depth_column!r} не найдена.")
    offset_value = float(_to_decimal(offset))
    result = df.copy()
    result[depth_column] = pd.to_numeric(result[depth_column], errors="coerce") + offset_value
    integrity = validate_depth_integrity(result, depth_column)
    return DepthSamplingOperationResult(
        data=result,
        operation_log=(f"Depth shifted by {offset_value}.",),
        integrity=integrity,
        warnings=integrity.warnings,
    )


def convert_depth_units(
    df: pd.DataFrame,
    depth_column: str = "depth",
    *,
    source_unit: str = "m",
    target_unit: str = "ft",
) -> DepthSamplingOperationResult:
    """Convert depth values between metres and feet."""

    if depth_column not in df.columns:
        raise ValueError(f"Колонка глубины {depth_column!r} не найдена.")

    source = str(source_unit).strip().lower()
    target = str(target_unit).strip().lower()
    aliases = {"meter": "m", "metre": "m", "meters": "m", "metres": "m", "feet": "ft", "foot": "ft"}
    source = aliases.get(source, source)
    target = aliases.get(target, target)
    if source not in {"m", "ft"} or target not in {"m", "ft"}:
        raise ValueError("Поддерживается перевод глубины только между m и ft.")
    if source == target:
        factor = 1.0
    elif source == "m" and target == "ft":
        factor = 3.280839895
    else:
        factor = 0.3048

    result = df.copy()
    result[depth_column] = pd.to_numeric(result[depth_column], errors="coerce") * factor
    integrity = validate_depth_integrity(result, depth_column)
    return DepthSamplingOperationResult(
        data=result,
        operation_log=(f"Depth unit converted from {source} to {target}; factor {factor}.",),
        integrity=integrity,
        warnings=integrity.warnings,
    )


def crop_depth_interval(df: pd.DataFrame, depth_column: str = "depth", *, start_depth=None, stop_depth=None) -> DepthSamplingOperationResult:
    """Keep only rows inside a selected depth interval."""

    if depth_column not in df.columns:
        raise ValueError(f"Колонка глубины {depth_column!r} не найдена.")
    start = _coerce_optional_depth(start_depth, "Начало интервала")
    stop = _coerce_optional_depth(stop_depth, "Конец интервала")
    if start is not None and stop is not None and start > stop:
        raise ValueError("Начало интервала не может быть больше конца интервала.")

    result = df.copy()
    result[depth_column] = pd.to_numeric(result[depth_column], errors="coerce")
    before = len(result)
    if start is not None:
        result = result[result[depth_column] >= start].copy()
    if stop is not None:
        result = result[result[depth_column] <= stop].copy()
    result = result.reset_index(drop=True)
    integrity = validate_depth_integrity(result, depth_column)
    return DepthSamplingOperationResult(
        data=result,
        operation_log=(f"Depth interval cropped: {start if start is not None else 'min'} -> {stop if stop is not None else 'max'}; rows {before} -> {len(result)}.",),
        integrity=integrity,
        warnings=integrity.warnings,
    )


def resample_depth_step(
    df: pd.DataFrame,
    depth_column: str = "depth",
    *,
    target_step=0.1,
    method: str = "linear",
) -> DepthSamplingOperationResult:
    """Resample all numeric curves to a new depth step.

    This helper differs from ``resample_las_data`` by interpolating from the
    original irregular grid onto a newly generated regular grid, so conversions
    such as 0.1524 m -> 0.1 m keep curve values instead of only preserving exact
    depth matches. Text columns are forward-filled after the numeric resample.
    """

    if depth_column not in df.columns:
        raise ValueError(f"Колонка глубины {depth_column!r} не найдена.")
    method_name = str(method).strip().lower()
    if method_name not in {"linear", "nearest"}:
        raise ValueError("Метод ресемплинга должен быть linear или nearest.")
    step_value = float(_to_decimal(target_step))
    if step_value <= 0:
        raise ValueError("Шаг глубины должен быть больше 0.")

    working = df.copy()
    working[depth_column] = pd.to_numeric(working[depth_column], errors="coerce")
    working = working.dropna(subset=[depth_column]).drop_duplicates(subset=[depth_column], keep="first")
    if working.empty:
        integrity = validate_depth_integrity(working, depth_column)
        return DepthSamplingOperationResult(data=working, operation_log=("Depth resampling skipped: no numeric depth.",), integrity=integrity, warnings=integrity.warnings)

    working = working.sort_values(by=depth_column, kind="mergesort").reset_index(drop=True)
    start = float(working[depth_column].min())
    stop = float(working[depth_column].max())
    grid = list(build_depth_grid(start, stop, step_value))
    indexed = working.set_index(depth_column)

    numeric_columns = [column for column in indexed.columns if pd.to_numeric(indexed[column], errors="coerce").notna().any()]
    output = pd.DataFrame({depth_column: grid})
    if numeric_columns:
        numeric = indexed[numeric_columns].apply(pd.to_numeric, errors="coerce")
        union_index = sorted(set(numeric.index.tolist()) | set(grid))
        expanded = numeric.reindex(union_index)
        if method_name == "linear":
            filled = expanded.interpolate(method="index", limit_area="inside")
            sampled = filled.reindex(grid)
        else:
            sampled = numeric.reindex(grid, method="nearest")
        for column in numeric_columns:
            output[column] = sampled[column].to_numpy()

    text_columns = [column for column in indexed.columns if column not in numeric_columns]
    for column in text_columns:
        output[column] = indexed[column].reindex(grid, method="ffill").to_numpy()

    integrity = validate_depth_integrity(output, depth_column)
    return DepthSamplingOperationResult(
        data=output,
        operation_log=(f"Depth resampled to step {step_value} using {method_name} method; rows {len(working)} -> {len(output)}.",),
        integrity=integrity,
        warnings=integrity.warnings,
    )


def build_safe_las_filename(source_name: str, suffix: str) -> str:
    """Build a non-destructive LAS filename for editor exports."""

    source_stem = str(source_name or "prepared").strip().rsplit(".", 1)[0] or "prepared"
    safe_stem = "_".join(source_stem.replace("\\", "/").split("/")[-1].split())
    clean_suffix = "_".join(str(suffix or "edited").strip().lower().replace(".", "_").split()) or "edited"
    return f"{safe_stem}_{clean_suffix}.las"

def _coerce_optional_depth(value, field_name: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    try:
        return float(_to_decimal(value))
    except ValueError as exc:
        raise ValueError(f"{field_name}: некорректное значение глубины {value!r}.") from exc


def _replace_las_null_values(data: pd.DataFrame, null_value) -> tuple[pd.DataFrame, int]:
    result = data.copy()
    if isinstance(null_value, str) and not null_value.strip():
        return result, 0

    numeric_null = None
    try:
        numeric_null = float(_to_decimal(null_value))
    except ValueError:
        pass

    replaced_count = 0
    for column in result.columns:
        text_mask = result[column].astype(str).str.strip() == str(null_value).strip()
        mask = text_mask
        if numeric_null is not None:
            numeric_series = pd.to_numeric(result[column], errors="coerce")
            mask = mask | (numeric_series == numeric_null)
        replaced_count += int(mask.sum())
        if mask.any():
            result.loc[mask, column] = pd.NA

    return result, replaced_count


def apply_las_bulk_operations(
    df: pd.DataFrame,
    depth_column: str = "depth",
    *,
    remove_duplicate_depths: bool = False,
    trim_start=None,
    trim_end=None,
    replace_null_value=None,
    sort_depth: bool = False,
    check_monotonic: bool = True,
) -> LasBulkOperationResult:
    """Apply safe batch edits used by the LAS editor.

    The function does not mutate the input dataframe. Operations are explicit and
    logged so prepared LAS versions can later store an audit trail.
    """

    if depth_column not in df.columns:
        raise ValueError(f"Колонка глубины {depth_column!r} не найдена.")

    working = df.copy()
    log: list[str] = []
    warnings: list[str] = []

    original_rows = len(working)
    working[depth_column] = pd.to_numeric(working[depth_column], errors="coerce")

    if replace_null_value is not None and not (isinstance(replace_null_value, str) and not replace_null_value.strip()):
        working, replaced_count = _replace_las_null_values(working, replace_null_value)
        log.append(f"LAS NULL {replace_null_value!r} replaced with empty values: {replaced_count} cells.")
        if replaced_count == 0:
            warnings.append(f"Значения NULL {replace_null_value!r} не найдены.")

    start_depth = _coerce_optional_depth(trim_start, "Начало интервала")
    end_depth = _coerce_optional_depth(trim_end, "Конец интервала")
    if start_depth is not None and end_depth is not None and start_depth > end_depth:
        raise ValueError("Начало интервала не может быть больше конца интервала.")

    if start_depth is not None:
        before = len(working)
        working = working[working[depth_column].isna() | (working[depth_column] >= start_depth)].copy()
        log.append(f"Trimmed rows above {start_depth}: {before - len(working)} rows removed.")
    if end_depth is not None:
        before = len(working)
        working = working[working[depth_column].isna() | (working[depth_column] <= end_depth)].copy()
        log.append(f"Trimmed rows below {end_depth}: {before - len(working)} rows removed.")

    if remove_duplicate_depths:
        before = len(working)
        working = working.drop_duplicates(subset=[depth_column], keep="first").copy()
        removed = before - len(working)
        log.append(f"Duplicate depth rows removed: {removed}.")
        if removed == 0:
            warnings.append("Дубликаты глубин для удаления не найдены.")

    if sort_depth:
        before_order = tuple(working[depth_column].tolist())
        working = working.sort_values(by=depth_column, kind="mergesort", na_position="last").reset_index(drop=True)
        after_order = tuple(working[depth_column].tolist())
        log.append("Rows sorted by depth in ascending order." if before_order != after_order else "Depth order already ascending.")
    else:
        working = working.reset_index(drop=True)

    depth_values = working[depth_column].dropna()
    monotonic = bool(depth_values.is_monotonic_increasing)
    if check_monotonic:
        if monotonic:
            log.append("Depth monotonicity check passed.")
        else:
            warnings.append("Глубина не монотонна. Отсортируйте глубину или проверьте исходный LAS.")
            log.append("Depth monotonicity check failed.")

    if len(working) != original_rows and not log:
        log.append(f"Rows changed: {original_rows} -> {len(working)}.")

    diagnostics = diagnose_depths(working, depth_column=depth_column)
    warnings.extend(diagnostics.warnings)

    return LasBulkOperationResult(
        data=working,
        diagnostics=diagnostics,
        operation_log=tuple(dict.fromkeys(log)),
        monotonic=monotonic,
        warnings=tuple(dict.fromkeys(warnings)),
    )


def insert_manual_depth_rows(
    df: pd.DataFrame,
    depth_column: str = "depth",
    *,
    start_depth,
    end_depth,
    step,
    fill_strategy: str = "empty",
) -> ManualDepthRowsResult:
    """Insert explicit depth rows inside a user-selected interval.

    Unlike the automatic full-interval resampling, this helper only touches the
    requested interval. Existing rows are preserved, missing depths from the
    requested grid are appended, and the final table is sorted by depth. The
    returned operation log is designed for persistent LAS edit metadata.
    """

    if depth_column not in df.columns:
        raise ValueError(f"Колонка глубины {depth_column!r} не найдена.")
    if fill_strategy not in FILL_STRATEGIES:
        raise ValueError(f"Стратегия заполнения {fill_strategy!r} не поддерживается.")

    start_value = float(_to_decimal(start_depth))
    end_value = float(_to_decimal(end_depth))
    step_value = float(_to_decimal(step))
    if step_value <= 0:
        raise ValueError("Шаг глубины должен быть больше 0.")
    if start_value > end_value:
        raise ValueError("Начальная глубина не может быть больше конечной.")

    working = df.copy()
    working[depth_column] = pd.to_numeric(working[depth_column], errors="coerce")
    grid = build_depth_grid(start_value, end_value, step_value)
    existing_depths = {_round_depth(value) for value in working[depth_column].dropna()}
    added_depths = tuple(depth for depth in grid if _round_depth(depth) not in existing_depths)

    warnings: list[str] = []
    operation_log: list[str] = [
        f"Manual interval rows requested: {start_value} -> {end_value}, step {step_value}."
    ]

    if not added_depths:
        warnings.append("В выбранном интервале нет недостающих глубин для добавления.")
        operation_log.append("Manual interval rows added: 0.")
        return ManualDepthRowsResult(
            data=working.sort_values(by=depth_column, kind="mergesort", na_position="last").reset_index(drop=True),
            added_depths=(),
            operation_log=tuple(operation_log),
            warnings=tuple(warnings),
        )

    added = pd.DataFrame({column: pd.NA for column in working.columns}, index=range(len(added_depths)))
    added[depth_column] = list(added_depths)
    result = pd.concat([working, added], ignore_index=True)
    result = result.sort_values(by=depth_column, kind="mergesort", na_position="last").reset_index(drop=True)
    result = _fill_added_rows(result, depth_column, fill_strategy)

    operation_log.append(f"Manual interval rows added: {len(added_depths)}.")
    if fill_strategy != "empty":
        operation_log.append(f"Manual interval rows fill strategy: {fill_strategy}.")
        warnings.append(
            "Добавленные вручную строки заполнены автоматически. Проверьте газовые компоненты перед расчетом."
        )

    return ManualDepthRowsResult(
        data=result,
        added_depths=added_depths,
        operation_log=tuple(operation_log),
        warnings=tuple(dict.fromkeys(warnings)),
    )


def _fill_added_rows(data: pd.DataFrame, depth_column: str, fill_strategy: str) -> pd.DataFrame:
    if fill_strategy == "empty":
        return data
    if fill_strategy == "top":
        return data.ffill()
    if fill_strategy == "bottom":
        return data.bfill()

    result = data.copy()
    value_columns = [column for column in result.columns if column != depth_column]
    numeric_values = result[value_columns].apply(pd.to_numeric, errors="coerce")

    if fill_strategy == "average":
        filled = (numeric_values.ffill() + numeric_values.bfill()) / 2
    elif fill_strategy == "linear":
        filled = numeric_values.interpolate(method="linear", limit_area="inside")
    else:
        raise ValueError(f"Стратегия заполнения {fill_strategy!r} не поддерживается.")

    result[value_columns] = result[value_columns].combine_first(filled)
    return result


def resample_las_data(
    df: pd.DataFrame,
    depth_column: str = "depth",
    target_step=0.1,
    fill_strategy: str = "empty",
) -> LasResampleResult:
    if fill_strategy not in FILL_STRATEGIES:
        raise ValueError(f"Стратегия заполнения {fill_strategy!r} не поддерживается.")

    diagnostics = diagnose_depths(df, depth_column=depth_column, expected_step=target_step)
    warnings = list(diagnostics.warnings)
    if diagnostics.min_depth is None or diagnostics.max_depth is None:
        return LasResampleResult(
            data=df.copy(),
            diagnostics=diagnostics,
            fill_strategy=fill_strategy,
            warnings=tuple(warnings),
        )

    working = df.copy()
    working[depth_column] = _coerce_depth_series(working, depth_column)
    working = working.dropna(subset=[depth_column])
    if diagnostics.null_depth_count:
        warnings.append("Строки без числовой глубины не включены в сетку редактора.")

    if diagnostics.duplicate_depths:
        working = working.drop_duplicates(subset=[depth_column], keep="first")
        warnings.append("Дубликаты глубин свернуты: оставлена первая строка для каждой глубины.")

    depth_order_fixed = diagnostics.reverse_step_count > 0
    if depth_order_fixed:
        warnings.append("Порядок глубины исправлен: строки отсортированы по возрастанию глубины.")

    grid = build_depth_grid(diagnostics.min_depth, diagnostics.max_depth, target_step)
    existing_depths = {_round_depth(value) for value in working[depth_column]}
    added_depths = tuple(depth for depth in grid if _round_depth(depth) not in existing_depths)

    indexed = working.set_index(depth_column).sort_index()
    resampled = indexed.reindex(grid)
    resampled.index.name = depth_column
    resampled = resampled.reset_index()
    resampled = _fill_added_rows(resampled, depth_column, fill_strategy)

    if added_depths:
        warnings.append(f"Добавлено строк по сетке глубины: {len(added_depths)}.")
        if fill_strategy != "empty":
            warnings.append(f"Добавленные строки заполнены стратегией: {fill_strategy}.")

    return LasResampleResult(
        data=resampled,
        diagnostics=diagnostics,
        added_depths=added_depths,
        fill_strategy=fill_strategy,
        depth_order_fixed=depth_order_fixed,
        warnings=tuple(dict.fromkeys(warnings)),
    )
