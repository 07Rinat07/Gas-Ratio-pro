from pathlib import Path

from core.data_platform.dataset_manifest import DatasetManifest, DatasetProvenance
from core.data_platform.import_jobs import ImportHistoryRepository, ImportJobSnapshot
from core.data_platform.manifest_repository import DatasetManifestRepository
from projects.project_tree import build_project_tree, flatten_project_tree
from projects.repository import create_project
from services.data_platform_application_service import DataPlatformApplicationService


def _manifest(project_id: str, dataset_id: str, well_id: str, status: str, score: int, curves: str) -> DatasetManifest:
    return DatasetManifest(
        dataset_id=dataset_id,
        lineage_id=dataset_id,
        project_id=project_id,
        well_id=well_id,
        format_id="las",
        artifact_path=f"source/{dataset_id}.las",
        checksum_sha256=(dataset_id.encode().hex() + "0" * 64)[:64],
        size_bytes=10,
        version=1,
        source_name=f"{dataset_id}.las",
        metadata={
            "readiness_status": status,
            "readiness_score": score,
            "curve_mnemonics": curves,
            "start_depth": 1000,
            "stop_depth": 2000,
        },
        provenance=DatasetProvenance(operation="import"),
    )


def test_readiness_items_filter_by_status_and_format(tmp_path: Path):
    project = create_project(tmp_path, name="Demo", project_id="demo")
    repo = DatasetManifestRepository(tmp_path)
    repo.save(_manifest(project.id, "ds-a", "well-a", "ready", 95, "DEPT,GR,RHOB"))
    repo.save(_manifest(project.id, "ds-b", "well-b", "review", 60, "DEPT,GR"))

    service = DataPlatformApplicationService(tmp_path)
    rows = service.list_project_readiness_items(project.id, statuses={"ready"}, formats={"las"})
    assert len(rows) == 1
    assert rows[0]["dataset_id"] == "ds-a"
    assert rows[0]["readiness_score"] == 95


def test_correlation_readiness_uses_shared_curves_without_payload_reads(tmp_path: Path):
    project = create_project(tmp_path, name="Demo", project_id="demo")
    repo = DatasetManifestRepository(tmp_path)
    repo.save(_manifest(project.id, "ds-a", "well-a", "ready", 95, "DEPT,GR,RHOB"))
    repo.save(_manifest(project.id, "ds-b", "well-b", "ready", 90, "DEPT,GR,NPHI"))

    snapshot = DataPlatformApplicationService(tmp_path).project_correlation_readiness(project.id)
    assert snapshot["well_count"] == 2
    assert snapshot["ready_count"] == 2
    assert snapshot["shared_curves"] == ["DEPT", "GR"]
    assert snapshot["eligible_for_correlation"] is True


def test_import_history_job_exposes_created_dataset_children(tmp_path: Path):
    project = create_project(tmp_path, name="Demo", project_id="demo")
    ImportHistoryRepository(tmp_path).append(ImportJobSnapshot(
        job_id="import-1",
        project_id=project.id,
        source_paths=("x.las",),
        source_names=("x.las",),
        status="completed",
        progress_percent=100,
        success_count=1,
        result={
            "items": [{
                "source_name": "x.las",
                "status": "success",
                "dataset_id": "ds-x",
                "format_id": "las",
                "readiness_score": 94,
            }]
        },
    ))
    nodes = {node.id: node for _, node in flatten_project_tree(
        build_project_tree(tmp_path, project.id, include_sections={"imports"})
    )}
    job = nodes["import_job:import-1"]
    assert job.metadata["dataset_count"] == 1
    child = nodes["import_job:import-1:dataset:ds-x"]
    assert child.metadata["dataset_id"] == "ds-x"
    assert child.metadata["readiness_score"] == 94
