from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from projects.las_files import ProjectLasFile, list_project_las_files, read_project_las_file_dataframe
from projects.repository import DEFAULT_PROJECT_ID, DEFAULT_PROJECTS_ROOT

DEPTH_CURVE_CANDIDATES = ("DEPT", "DEPTH", "MD")


@dataclass(frozen=True)
class ProjectDatasetRecord:
    """Compact project dataset card used by Dataset Manager.

    The card is intentionally metadata-oriented. For LAS datasets it reads only
    enough tabular information to show size, curve names and basic readiness
    diagnostics. It does not duplicate source files and does not mutate saved LAS
    versions.
    """

    id: str
    kind: str
    name: str
    source_id: str
    well_id: str
    version_label: str
    original_file_name: str
    saved_at: str
    archived_at: str = ""
    row_count: int = 0
    column_count: int = 0
    depth_curve: str = ""
    curves: tuple[str, ...] = ()
    status: str = "ready"
    warnings: tuple[str, ...] = ()
    metadata: dict[str, Any] | None = None

    @property
    def status_label(self) -> str:
        labels = {
            "ready": "готов",
            "warning": "требует проверки",
            "error": "ошибка чтения",
        }
        return labels.get(self.status, self.status)

    @property
    def is_ready(self) -> bool:
        return self.status == "ready"


def _find_depth_curve(columns: tuple[str, ...]) -> str:
    by_upper = {column.upper(): column for column in columns}
    for candidate in DEPTH_CURVE_CANDIDATES:
        if candidate in by_upper:
            return by_upper[candidate]
    return ""


def _curve_names(dataframe: pd.DataFrame) -> tuple[str, ...]:
    return tuple(str(column) for column in dataframe.columns)


def build_project_las_dataset_record(
    record: ProjectLasFile,
    dataframe: pd.DataFrame | None = None,
    *,
    error: str = "",
) -> ProjectDatasetRecord:
    """Build a Dataset Manager card for one saved project LAS version."""

    warnings: list[str] = []
    curves: tuple[str, ...] = ()
    row_count = 0
    column_count = 0
    depth_curve = ""
    status = "ready"

    if error:
        status = "error"
        warnings.append(error)
    elif dataframe is not None:
        curves = _curve_names(dataframe)
        row_count = int(len(dataframe))
        column_count = int(len(dataframe.columns))
        depth_curve = _find_depth_curve(curves)
        if row_count == 0:
            warnings.append("LAS dataset не содержит строк ASCII-данных.")
        if column_count == 0:
            warnings.append("LAS dataset не содержит кривых.")
        if not depth_curve:
            warnings.append("Не найдена глубинная кривая DEPT/DEPTH/MD.")
        if warnings:
            status = "warning"
    else:
        status = "warning"
        warnings.append("Таблица LAS не передана для проверки dataset-карточки.")

    return ProjectDatasetRecord(
        id=f"las:{record.id}",
        kind="LAS",
        name=f"{record.name} · {record.version_label}",
        source_id=record.id,
        well_id=record.well_id,
        version_label=record.version_label,
        original_file_name=record.original_file_name,
        saved_at=record.saved_at,
        archived_at=record.archived_at,
        row_count=row_count,
        column_count=column_count,
        depth_curve=depth_curve,
        curves=curves,
        status=status,
        warnings=tuple(warnings),
        metadata=dict(record.metadata or {}),
    )


def list_project_las_datasets(
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
    include_archived: bool = False,
) -> tuple[ProjectDatasetRecord, ...]:
    """Return LAS dataset cards for the active project.

    Each card corresponds to an existing saved LAS version. Broken LAS files are
    kept in the returned list as ``error`` records so the user can see that the
    dataset exists but needs repair instead of silently losing it from the UI.
    """

    datasets: list[ProjectDatasetRecord] = []
    for record in list_project_las_files(root, project_id, include_archived=include_archived):
        try:
            dataframe = read_project_las_file_dataframe(root, project_id, record.id)
        except Exception as exc:  # pragma: no cover - exact parser errors vary by file
            datasets.append(
                build_project_las_dataset_record(
                    record,
                    error=f"Не удалось прочитать LAS: {exc}",
                )
            )
        else:
            datasets.append(build_project_las_dataset_record(record, dataframe))
    return tuple(datasets)


def build_project_dataset_table(datasets: tuple[ProjectDatasetRecord, ...] | list[ProjectDatasetRecord]) -> pd.DataFrame:
    """Convert dataset cards to a small table for Streamlit and tests."""

    return pd.DataFrame(
        [
            {
                "Тип": dataset.kind,
                "Dataset": dataset.name,
                "Статус": dataset.status_label,
                "Скважина ID": dataset.well_id,
                "Источник ID": dataset.source_id,
                "Файл": dataset.original_file_name,
                "Строк": dataset.row_count,
                "Кривых": dataset.column_count,
                "Глубина": dataset.depth_curve,
                "Кривые": ", ".join(dataset.curves[:12]),
                "Предупреждения": "; ".join(dataset.warnings),
                "Сохранено": dataset.saved_at,
                "Архивировано": dataset.archived_at,
            }
            for dataset in datasets
        ]
    )
