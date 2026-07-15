from pathlib import Path

from core.application_service_container import ApplicationServiceContainer
from core.application_service_container import application_service_container
from reports.pdf_preview import PdfPreviewResult
from services.pdf_preview_application_service import PdfPreviewApplicationService


def _result() -> PdfPreviewResult:
    return PdfPreviewResult(pages=(), total_pages=1, rendered_pages=0, backend="test", truncated=False, image_size_bytes=0)


def test_service_owns_project_scoped_cache(tmp_path: Path) -> None:
    service = PdfPreviewApplicationService(project_id="alpha", root=tmp_path)
    service.store("sig", _result())
    assert service.inspect("sig").hit is True
    assert service.health_snapshot()["project_id"] == "alpha"


def test_legacy_migration_accepts_only_valid_entries(tmp_path: Path) -> None:
    service = PdfPreviewApplicationService(project_id="alpha", root=tmp_path)
    count = service.migrate_legacy_entries({"entries": [{"signature": "ok", "result": _result()}, {"bad": True}]})
    assert count == 1
    assert service.inspect("ok").hit is True


def test_container_reuses_pdf_preview_service(tmp_path: Path) -> None:
    container = application_service_container({})
    first = container.pdf_preview(project_id="alpha", root=tmp_path)
    second = container.pdf_preview(project_id="alpha", root=tmp_path)
    other = container.pdf_preview(project_id="beta", root=tmp_path)
    assert first is second
    assert first is not other
