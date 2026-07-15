from pathlib import Path

from core.application_service_container import ApplicationServiceContainer
from core.runtime_service_registry import RuntimeServiceRegistry


def test_streamlit_ui_does_not_resolve_cache_telemetry_infrastructure() -> None:
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")

    assert "from core.cache_metrics import CacheMetricsRegistry" not in source
    assert 'ensure_runtime_service(\n        "cache_metrics_registry"' not in source
    assert "metrics_registry=cache_metrics_registry" not in source
    assert "from core.correlation_runtime_cache import CorrelationRenderArtifacts" not in source
    assert "CorrelationRenderArtifacts(" not in source
    assert ".put_artifacts(" in source


def test_container_resolves_one_shared_cache_metrics_registry(tmp_path: Path) -> None:
    registry = RuntimeServiceRegistry()
    container = ApplicationServiceContainer(registry)

    pdf = container.pdf_preview(project_id="p", root=tmp_path)
    interpretation = container.interpretation_presentation(project_id="p", root=tmp_path)
    correlation = container.correlation_presentation(project_id="p", root=tmp_path)

    shared = registry.get("cache_metrics_registry")
    assert shared is not None
    assert pdf._cache._metrics is shared.counter("pdf_preview_runtime", max_entries=3)
    assert interpretation._metrics_registry is shared
    assert correlation._metrics_registry is shared
