from __future__ import annotations

from typing import Mapping
import pandas as pd

from core.qc import LasQCEngine, localize_qc_report


class QCApplicationService:
    def __init__(self) -> None:
        self._las = LasQCEngine()

    def run_las(self, df: pd.DataFrame, *, depth_curve: str | None = None,
                expected_step: float | None = None, null_value: float = -999.25,
                units: Mapping[str, str] | None = None):
        return self._las.run(df, depth_curve=depth_curve, expected_step=expected_step,
                             null_value=null_value, units=units)

    def run_las_localized(self, df: pd.DataFrame, *, translate, **kwargs):
        return localize_qc_report(self.run_las(df, **kwargs), translate)
