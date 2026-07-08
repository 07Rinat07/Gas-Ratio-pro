from core.application_state import (
    ACTIVE_PROJECT_ID_KEY,
    ApplicationStateController,
    ApplicationStateKeys,
)
from core.event_bus import ApplicationEventBus, EVENT_HISTORY_KEY, EVENT_QUEUE_KEY, REFRESH_REQUEST_KEY


def test_event_bus_publish_consume_and_history():
    state = {}
    bus = ApplicationEventBus(state)

    event = bus.publish("project.changed", {"project_id": "p-1"}, source="test")

    assert event.name == "project.changed"
    assert state[EVENT_QUEUE_KEY][0]["payload"]["project_id"] == "p-1"
    assert bus.peek()[0].source == "test"
    consumed = bus.consume()
    assert consumed[0].name == "project.changed"
    assert state[EVENT_QUEUE_KEY] == []
    assert state[EVENT_HISTORY_KEY][0]["name"] == "project.changed"


def test_application_state_project_transition_publishes_event_and_clears_tables():
    state = {
        ACTIVE_PROJECT_ID_KEY: "old",
        "table_preview": [1, 2, 3],
        "dashboard_metrics": {"wells": 2},
    }
    controller = ApplicationStateController(state)

    transition = controller.activate_project("new")

    assert transition.changed is True
    assert state[ApplicationStateKeys.ACTIVE_PROJECT_ID] == "new"
    assert "table_preview" not in state
    assert "dashboard_metrics" not in state
    events = controller.consume_events()
    assert [event.name for event in events] == ["project.changed"]
    assert events[0].payload["project_id"] == "new"
    assert "table_preview" in events[0].payload["cleared_keys"]


def test_application_state_refresh_request_is_consumable():
    state = {}
    controller = ApplicationStateController(state)

    controller.request_refresh("project_deleted", source="test")

    assert state[REFRESH_REQUEST_KEY]["reason"] == "project_deleted"
    assert controller.consume_refresh_request()["reason"] == "project_deleted"
    assert REFRESH_REQUEST_KEY not in state
    assert controller.consume_events()[0].name == "ui.refresh_requested"
