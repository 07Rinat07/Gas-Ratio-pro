from ui.interpretation_interval_panel import DEFAULT_MANUAL_WELL_ID, resolve_interpretation_well_id


def test_resolve_interpretation_well_id_prefers_active_well() -> None:
    state = {
        "active_well_id": "well-active",
        "workbench_active_calculation": {"well_id": "well-contract"},
    }
    assert resolve_interpretation_well_id(state) == "well-active"


def test_resolve_interpretation_well_id_uses_calculation_contract() -> None:
    state = {"workbench_active_calculation": {"well_id": "well-contract"}}
    assert resolve_interpretation_well_id(state) == "well-contract"


def test_resolve_interpretation_well_id_has_stable_fallback() -> None:
    assert resolve_interpretation_well_id({}) == DEFAULT_MANUAL_WELL_ID
