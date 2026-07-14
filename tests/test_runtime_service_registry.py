from queue import SimpleQueue

from core.application_state import ApplicationStateController
from core.runtime_service_registry import RUNTIME_SERVICES_STATE_KEY, RuntimeServiceRegistry
from core.workbench_dispatcher import _snapshot_state_for_rollback


def test_registry_keeps_runtime_service_out_of_normal_state_keys():
    state = {"project": {"name": "A"}}
    controller = ApplicationStateController(state)
    queue = SimpleQueue()

    controller.set_runtime_service("jobs", queue)

    assert controller.get_runtime_service("jobs") is queue
    assert "jobs" not in state
    assert isinstance(state[RUNTIME_SERVICES_STATE_KEY], RuntimeServiceRegistry)


def test_ensure_runtime_service_constructs_once():
    state = {}
    controller = ApplicationStateController(state)
    created = []

    first = controller.ensure_runtime_service("cache", lambda: created.append(object()) or created[-1])
    second = controller.ensure_runtime_service("cache", lambda: object())

    assert first is second
    assert len(created) == 1


def test_rollback_snapshot_deepcopies_data_but_preserves_registry_identity():
    state = {"nested": {"items": [1]}}
    controller = ApplicationStateController(state)
    registry = controller.runtime_services()
    queue = registry.set("queue", SimpleQueue())

    snapshot = _snapshot_state_for_rollback(state)
    state["nested"]["items"].append(2)

    assert snapshot["nested"] == {"items": [1]}
    assert snapshot[RUNTIME_SERVICES_STATE_KEY] is registry
    assert registry.get("queue") is queue


def test_registry_descriptors_are_serializable_diagnostics():
    registry = RuntimeServiceRegistry()
    registry.set("queue", SimpleQueue())

    descriptors = registry.descriptors()

    assert descriptors[0].key == "queue"
    assert descriptors[0].type_name == "SimpleQueue"


def test_registry_snapshot_tracks_service_lifecycle_without_live_references() -> None:
    registry = RuntimeServiceRegistry()
    first = object()
    second = object()

    registry.set("cache", first)
    registry.set("cache", second)
    registry.ensure("queue", object)
    registry.remove("queue")

    snapshot = registry.snapshot()

    assert snapshot.to_dict() == {
        "active": 1,
        "created": 2,
        "replaced": 1,
        "removed": 1,
        "shutdowns": 0,
    }
