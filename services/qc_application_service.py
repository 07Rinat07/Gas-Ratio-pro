from __future__ import annotations

from pathlib import Path
from typing import Mapping
import pandas as pd

from core.qc import LasQCEngine, localize_qc_report
from core.qc.artifacts import QCReportArtifactService


class QCApplicationService:
    def __init__(self, projects_root: Path | str | None = None) -> None:
        self._las = LasQCEngine()
        self._artifacts = QCReportArtifactService(projects_root) if projects_root is not None else None

    def run_las(self, df: pd.DataFrame, *, depth_curve: str | None = None,
                expected_step: float | None = None, null_value: float = -999.25,
                units: Mapping[str, str] | None = None):
        return self._las.run(df, depth_curve=depth_curve, expected_step=expected_step,
                             null_value=null_value, units=units)

    def run_las_localized(self, df: pd.DataFrame, *, translate, **kwargs):
        return localize_qc_report(self.run_las(df, **kwargs), translate)

    def filter_report(self, report, *, severities: set[str] | None = None, codes: set[str] | None = None) -> dict[str, object]:
        """Return a JSON-safe UI projection without mutating the immutable report."""
        allowed_severity = {str(item).lower() for item in (severities or set())}
        allowed_codes = {str(item) for item in (codes or set())}
        payload = report.to_dict()
        payload["findings"] = [
            item for item in payload["findings"]
            if (not allowed_severity or str(item["severity"]).lower() in allowed_severity)
            and (not allowed_codes or str(item["code"]) in allowed_codes)
        ]
        payload["filtered_finding_count"] = len(payload["findings"])
        return payload

    def persist_report(self, *, project_id: str, source_dataset_id: str, report, actor: str = ""):
        if self._artifacts is None:
            raise RuntimeError("QC persistence requires a projects_root")
        return self._artifacts.persist(
            project_id=project_id,
            source_dataset_id=source_dataset_id,
            report=report,
            actor=actor,
        )

    def export_report_docx(self, *, report, destination: Path | str, translate):
        if self._artifacts is None:
            raise RuntimeError("QC export requires a projects_root")
        return self._artifacts.export_docx(report=report, destination=destination, translate=translate)

    def export_report_pdf(self, *, report, destination: Path | str, translate):
        if self._artifacts is None:
            raise RuntimeError("QC export requires a projects_root")
        return self._artifacts.export_pdf(report=report, destination=destination, translate=translate)
