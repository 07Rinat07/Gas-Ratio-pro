from queue import Queue

from core.runtime_service_registry import RuntimeServiceRegistry
from core.session_state_audit import audit_session_state


def test_session_state_audit_reports_runtime_transient_and_unscoped_keys() -> None:
    state = {
        "runtime::services": RuntimeServiceRegistry(),
        "las_dataframe": [1, 2, 3],
        "workbench.active_route": "dashboard",
        "plain_note": "legacy",
        "background_queue": Queue(),
        "counter": 4,
    }

    audit = audit_session_state(state)

    assert audit.total_keys == 6
    assert audit.runtime_keys == ("background_queue", "runtime::services")
    assert "las_dataframe" in audit.transient_keys
    assert "plain_note" in audit.unscoped_keys
    assert audit.primitive_keys == 3
    assert audit.container_keys == 1
    assert audit.to_dict()["runtime_count"] == 2


def test_session_state_audit_is_serializable_and_does_not_copy_values() -> None:
    marker = object()
    state = {"custom_object": marker}

    audit = audit_session_state(state)

    assert audit.type_counts == (("object", 1),)
    assert audit.to_dict()["type_counts"] == {"object": 1}
    assert state["custom_object"] is marker
