from pathlib import Path

from core.application_service_container import ApplicationServiceContainer
from core.runtime_service_registry import RuntimeServiceRegistry
from core.session_state_audit import audit_session_state


def test_streamlit_runtime_registers_cache_metrics_and_session_audit(tmp_path: Path) -> None:
    registry = RuntimeServiceRegistry()
    state: dict[str, object] = {}
    container = ApplicationServiceContainer(registry, state)

    interpretation = container.interpretation_presentation(project_id="p", root=tmp_path)
    pdf = container.pdf_preview(project_id="p", root=tmp_path)
    shared = registry.get("cache_metrics_registry")

    assert shared is not None
    assert interpretation._metrics_registry is shared
    assert pdf._cache._metrics is shared.counter("pdf_preview_runtime", max_entries=3)

    audit = audit_session_state(state)
    assert audit.runtime_count == 0
    assert "cache_metrics_registry" not in state
