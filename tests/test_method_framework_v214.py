from __future__ import annotations

import pandas as pd

from core.hydrocarbon_intervals import HydrocarbonInterval
from core.methods import MethodContext, MethodResult, build_default_method_registry


def _interval() -> HydrocarbonInterval:
    return HydrocarbonInterval(
        top=1000.0,
        base=1001.0,
        sample_count=3,
        fluid_type="oil",
        confidence="high",
        interpretation="Вероятный нефтяной интервал",
        confidence_score=84,
        average_ch=1.5,
    )


def _context(frame: pd.DataFrame) -> MethodContext:
    return MethodContext(
        frame=frame,
        interval=_interval(),
        interval_id="HC-001",
        selected_row=frame.iloc[0] if not frame.empty else {},
    )


def test_default_registry_exposes_three_methods_in_stable_order() -> None:
    registry = build_default_method_registry()
    assert [method.method_id for method in registry.methods()] == [
        "pixler_gas_ratio",
        "ternary_gas_composition",
        "haworth_mud_gas",
    ]


def test_registry_runs_methods_through_single_context_contract() -> None:
    frame = pd.DataFrame(
        {
            "depth": [1000.0, 1000.5, 1001.0],
            "c1": [10.0, 11.0, 12.0],
            "c2": [2.0, 2.0, 2.0],
            "c3": [1.0, 1.0, 1.0],
            "ic4": [0.2, 0.2, 0.2],
            "nc4": [0.3, 0.3, 0.3],
            "ic5": [0.1, 0.1, 0.1],
            "nc5": [0.1, 0.1, 0.1],
        }
    )
    results = build_default_method_registry().analyze_all(_context(frame))
    assert len(results) == 3
    assert all(isinstance(result, MethodResult) for result in results)
    assert {result.method for result in results} == {"Pixler", "Ternary", "Haworth"}
    assert all(result.method_id for result in results)
    assert all(result.version for result in results)


def test_missing_inputs_return_unavailable_results_instead_of_exceptions() -> None:
    frame = pd.DataFrame({"depth": [1000.0], "c1": [1.0]})
    results = build_default_method_registry().analyze_all(_context(frame))
    by_name = {result.method: result for result in results}
    assert by_name["Pixler"].available is False
    assert by_name["Ternary"].available is False
    assert by_name["Haworth"].available is True


def test_registry_rejects_duplicate_method_ids() -> None:
    registry = build_default_method_registry()
    try:
        registry.register(registry.get("pixler_gas_ratio"))
    except ValueError as exc:
        assert "already registered" in str(exc)
    else:
        raise AssertionError("duplicate method id must be rejected")
