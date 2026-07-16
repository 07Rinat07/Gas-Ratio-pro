from core.application_state import ApplicationStateController


def test_controller_get_is_read_only_mapping_compatibility_alias():
    state = {"requested": ("wells", "datasets")}
    controller = ApplicationStateController(state)

    assert controller.get("requested") == ("wells", "datasets")
    assert controller.get("missing", ()) == ()
    assert state == {"requested": ("wells", "datasets")}
