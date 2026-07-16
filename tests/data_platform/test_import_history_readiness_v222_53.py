from pathlib import Path

from core.data_platform.dataset_manifest import DatasetManifest, DatasetProvenance
from core.data_platform.import_jobs import ImportHistoryRepository, ImportJobSnapshot
from core.data_platform.manifest_repository import DatasetManifestRepository
from projects.project_tree import build_project_tree, flatten_project_tree
from projects.repository import create_project
from services.data_platform_application_service import DataPlatformApplicationService


def _manifest(project_id: str, dataset_id: str, status: str, score: int, format_id: str = "las") -> DatasetManifest:
    return DatasetManifest(
        dataset_id=dataset_id,
        lineage_id=dataset_id,
        project_id=project_id,
        format_id=format_id,
        artifact_path=f"source/{dataset_id}.{format_id}",
        checksum_sha256=(dataset_id.encode().hex() + "0" * 64)[:64],
        size_bytes=10,
        version=1,
        source_name=f"{dataset_id}.{format_id}",
        metadata={"readiness_status": status, "readiness_score": score},
        provenance=DatasetProvenance(operation="import"),
    )


def test_import_history_is_lazy_project_explorer_branch(tmp_path: Path):
    project = create_project(tmp_path, name="Demo", project_id="demo")
    ImportHistoryRepository(tmp_path).append(ImportJobSnapshot(
        job_id="import-1", project_id=project.id, source_paths=("x.las",),
        source_names=("x.las",), status="completed", progress_percent=100,
        success_count=1, finished_at="2026-01-01T00:00:00+00:00",
    ))
    root_only = {node.id: node for _, node in flatten_project_tree(
        build_project_tree(tmp_path, project.id, include_sections=set())
    )}
    assert root_only["folder:imports"].children[0].metadata["deferred"] == 1

    loaded = {node.id: node for _, node in flatten_project_tree(
        build_project_tree(tmp_path, project.id, include_sections={"imports"})
    )}
    assert loaded["import_job:import-1"].metadata["success_count"] == 1


def test_project_readiness_dashboard_aggregates_manifest_metadata(tmp_path: Path):
    project = create_project(tmp_path, name="Demo", project_id="demo")
    repo = DatasetManifestRepository(tmp_path)
    repo.save(_manifest(project.id, "ds-ready", "ready", 96, "las"))
    repo.save(_manifest(project.id, "ds-review", "review", 72, "segy"))
    repo.save(_manifest(project.id, "ds-blocked", "blocked", 30, "dlis"))

    snapshot = DataPlatformApplicationService(tmp_path).project_readiness_dashboard(project.id)
    assert snapshot["dataset_count"] == 3
    assert snapshot["ready_count"] == 1
    assert snapshot["review_count"] == 1
    assert snapshot["blocked_count"] == 1
    assert snapshot["average_score"] == 66.0
    assert snapshot["formats"] == {"dlis": 1, "las": 1, "segy": 1}
