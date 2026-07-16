import json
from pathlib import Path

import pandas as pd

from core.data_platform import DatasetManifest, DatasetManifestRepository, DatasetMetadataCatalog, DatasetProvenance
from services.qc_application_service import QCApplicationService


def _source_manifest(root: Path, project_id: str = "project-a") -> DatasetManifest:
    manifest = DatasetManifest.create(
        project_id=project_id,
        format_id="las",
        artifact_path="source/well.las",
        checksum_sha256="a" * 64,
        size_bytes=10,
        source_name="well.las",
        provenance=DatasetProvenance(operation="import", actor="tester"),
    )
    repo = DatasetManifestRepository(root)
    repo.save(manifest)
    DatasetMetadataCatalog(root).project(manifest)
    return manifest


def _report(service: QCApplicationService):
    df = pd.DataFrame({"DEPT": [1000.0, 1000.5, 1000.5], "GR": [80.0, -999.25, 300.0]})
    return service.run_las(df, expected_step=0.5)


def test_qc_report_is_persisted_as_derived_dataset_with_provenance(tmp_path):
    source = _source_manifest(tmp_path)
    service = QCApplicationService(tmp_path)
    result = service.persist_report(project_id=source.project_id, source_dataset_id=source.dataset_id, report=_report(service), actor="engineer")
    payload = result.to_dict()
    assert result.manifest.format_id == "qc-report-json"
    assert result.manifest.provenance.operation == "quality-control"
    assert result.manifest.provenance.source_dataset_ids == (source.dataset_id,)
    assert payload["source_dataset_ids"] == [source.dataset_id]
    artifact = tmp_path / source.project_id / "artifacts" / result.report_relative_path
    report_json = json.loads(artifact.read_text(encoding="utf-8"))
    assert report_json["source_dataset_id"] == source.dataset_id
    assert report_json["schema"] == "gas-ratio-pro/qc-report/v1"


def test_qc_filter_projection_is_json_safe_and_does_not_mutate_report():
    service = QCApplicationService()
    report = _report(service)
    original = len(report.findings)
    filtered = service.filter_report(report, severities={"error"})
    assert filtered["filtered_finding_count"] <= original
    assert len(report.findings) == original
    json.dumps(filtered)


def test_qc_container_root_enables_workspace_persistence(tmp_path):
    from core.application_service_container import ApplicationServiceContainer
    from core.runtime_service_registry import RuntimeServiceRegistry
    container = ApplicationServiceContainer(RuntimeServiceRegistry(), {})
    assert container.quality_control(root=tmp_path) is container.quality_control(root=tmp_path)
