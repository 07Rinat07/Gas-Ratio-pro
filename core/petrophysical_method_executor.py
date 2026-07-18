"""Shared execution boundary for registered petrophysical production methods.

The executor contains no alternative formulas.  It delegates every calculation
to the public production functions used by LAS Platform workspaces.  Validation,
field calibration and report authorization therefore exercise the same code
path instead of maintaining parallel implementations.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import pandas as pd

from las_editor.advanced_saturation_models import (
    DualWaterParameters,
    ShalySandParameters,
    calculate_dual_water_saturation,
    calculate_indonesia_water_saturation,
    calculate_simandoux_water_saturation,
)
from las_editor.petrophysical_workspace import (
    ArchieParameters,
    PetrophysicalCutoffSet,
    ShaleVolumeParameters,
    calculate_archie_water_saturation,
    calculate_effective_porosity,
    calculate_net_pay_flags,
    calculate_shale_volume,
)


def _series(values: Sequence[Any]) -> pd.Series:
    return pd.Series(list(values), dtype="float64")


def _values(series: pd.Series) -> list[float | None]:
    result: list[float | None] = []
    for value in series.tolist():
        result.append(None if pd.isna(value) else float(value))
    return result


def execute_petrophysical_method(
    method_id: str,
    *,
    inputs: Mapping[str, Any],
    parameters: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute one registered method through its production implementation."""

    clean_method_id = str(method_id).strip()
    params = dict(parameters or {})

    if clean_method_id.startswith("petrophysics.vsh_gr_"):
        result = calculate_shale_volume(_series(inputs["gr"]), ShaleVolumeParameters(**params))
        return {"values": _values(result)}
    if clean_method_id == "petrophysics.phie_shale_correction":
        result = calculate_effective_porosity(
            _series(inputs["total_porosity"]),
            _series(inputs["shale_volume"]),
        )
        return {"values": _values(result)}
    if clean_method_id == "petrophysics.sw_archie":
        result = calculate_archie_water_saturation(
            _series(inputs["phie"]),
            _series(inputs["rt"]),
            ArchieParameters(**params),
        )
        return {"values": _values(result)}
    if clean_method_id == "petrophysics.sw_simandoux":
        result = calculate_simandoux_water_saturation(
            _series(inputs["phie"]),
            _series(inputs["rt"]),
            _series(inputs["vsh"]),
            ShalySandParameters(**params),
        )
        return {"values": _values(result)}
    if clean_method_id == "petrophysics.sw_indonesia":
        result = calculate_indonesia_water_saturation(
            _series(inputs["phie"]),
            _series(inputs["rt"]),
            _series(inputs["vsh"]),
            ShalySandParameters(**params),
        )
        return {"values": _values(result)}
    if clean_method_id == "petrophysics.sw_dual_water_foundation":
        result = calculate_dual_water_saturation(
            _series(inputs["phie"]),
            _series(inputs["rt"]),
            _series(inputs["vsh"]),
            DualWaterParameters(**params),
        )
        return {"values": _values(result)}
    if clean_method_id == "petrophysics.net_pay_cutoff_flags":
        reservoir, net, pay = calculate_net_pay_flags(
            vsh=_series(inputs["vsh"]),
            phie=_series(inputs["phie"]),
            sw=_series(inputs["sw"]),
            rt=_series(inputs["rt"]),
            cutoffs=PetrophysicalCutoffSet(**params),
        )
        return {
            "reservoir": [int(value) for value in reservoir],
            "net": [int(value) for value in net],
            "pay": [int(value) for value in pay],
        }
    raise KeyError(f"No production executor registered for petrophysical method: {clean_method_id}")
