from __future__ import annotations

from queue import SimpleQueue

from core.application_state import ApplicationStateController
from core.runtime_service_registry import RuntimeServiceRegistry
from core.workbench_lifecycle import WORKBENCH_LIFECYCLE_CLOSED, WorkbenchLifecycleManager


class CloseService:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class ShutdownService:
    def __init__(self) -> None:
        self.wait = None

    def shutdown(self, *, wait: bool = True) -> None:
        self.wait = wait


class BrokenService:
    def close(self) -> None:
        raise RuntimeError("boom")


def test_registry_shutdown_closes_services_and_reports_failures() -> None:
    registry = RuntimeServiceRegistry()
    close_service = registry.set("close", CloseService())
    shutdown_service = registry.set("shutdown", ShutdownService())
    registry.set("queue", SimpleQueue())
    registry.set("broken", BrokenService())

    results = {item.key: item for item in registry.shutdown()}

    assert close_service.closed is True
    assert shutdown_service.wait is False
    assert results["close"].closed is True
    assert results["shutdown"].method == "shutdown"
    assert results["queue"].method == "none"
    assert results["broken"].closed is False
    assert "RuntimeError" in results["broken"].error
    assert registry.descriptors() == ()


def test_application_controller_can_shutdown_runtime_services() -> None:
    state: dict[str, object] = {}
    controller = ApplicationStateController(state)
    service = controller.set_runtime_service("worker", CloseService())

    results = controller.shutdown_runtime_services()

    assert service.closed is True
    assert results[0].key == "worker"
    assert controller.runtime_services().descriptors() == ()


def test_closing_workspace_disposes_registered_runtime_services(tmp_path) -> None:
    state: dict[str, object] = {}
    controller = ApplicationStateController(state)
    service = controller.set_runtime_service("worker", CloseService())
    manager = WorkbenchLifecycleManager(state, sessions_dir=tmp_path)
    manager.initialize()
    manager.open_workspace()

    result = manager.close_workspace()

    assert result.state == WORKBENCH_LIFECYCLE_CLOSED
    assert service.closed is True
    assert "runtime_service:worker" in result.affected_keys
    assert controller.runtime_services().descriptors() == ()
