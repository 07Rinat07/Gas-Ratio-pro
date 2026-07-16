from pathlib import Path

import pandas as pd

from projects import create_project
from projects.project_tree import build_project_tree, flatten_project_tree
from services.data_platform_application_service import DataPlatformApplicationService
from services.qc_application_service import QCApplicationService


def _las(path: Path, value: int) -> Path:
    path.write_text(
        "~V\nVERS. 2.0\nWRAP. NO\n~W\nWELL. W-1\nSTRT.M 1000\nSTOP.M 1001\nSTEP.M 1\nNULL. -999.25\n"
        "~C\nDEPT.M\nGR.API\n~A\n1000 %d\n1001 %d\n" % (value, value + 1),
        encoding="utf-8",
    )
    return path


def _report(service: QCApplicationService):
    return service.run_las(pd.DataFrame({"DEPT": [1000.0, 1001.0], "GR": [10.0, 11.0]}), expected_step=1.0)


def test_qc_reports_and_exports_are_exposed_in_lazy_dataset_branch(tmp_path: Path) -> None:
    project = create_project(tmp_path, name="QC Explorer", project_id="qc-explorer")
    data = DataPlatformApplicationService(tmp_path)
    source = data.register_source_file_result(project_id=project.id, source=_las(tmp_path / "well.las", 10))
    qc = QCApplicationService(tmp_path)
    report = _report(qc)
    qc_dataset = qc.persist_report(project_id=project.id, source_dataset_id=source.manifest.dataset_id, report=report)
    exported = qc.export_and_register(
        project_id=project.id,
        source_qc_dataset_id=qc_dataset.manifest.dataset_id,
        report=report,
        format_id="docx",
        translate=lambda key: key,
    )

    tree = build_project_tree(tmp_path, project.id, include_sections={"datasets"})
    nodes = {node.id: node for _level, node in flatten_project_tree(tree)}

    assert "folder:datasets:qc_reports" in nodes
    assert "folder:datasets:qc_exports" in nodes
    qc_node = nodes[f"dataset:{qc_dataset.manifest.dataset_id}"]
    export_node = nodes[f"dataset:{exported.manifest.dataset_id}"]
    assert qc_node.kind == "qc_report"
    assert qc_node.metadata["qc_status"] == report.status
    assert export_node.kind == "qc_export"
    assert export_node.metadata["downloadable"] == 1
    assert export_node.metadata["report_format"] == "docx"


def test_registered_export_can_be_read_through_bounded_service(tmp_path: Path) -> None:
    project = create_project(tmp_path, name="Download", project_id="download")
    data = DataPlatformApplicationService(tmp_path)
    source = data.register_source_file_result(project_id=project.id, source=_las(tmp_path / "well.las", 20))
    qc = QCApplicationService(tmp_path)
    report = _report(qc)
    qc_dataset = qc.persist_report(project_id=project.id, source_dataset_id=source.manifest.dataset_id, report=report)
    exported = qc.export_and_register(
        project_id=project.id,
        source_qc_dataset_id=qc_dataset.manifest.dataset_id,
        report=report,
        format_id="docx",
        translate=lambda key: key,
    )

    name, format_id, payload = data.read_registered_artifact(project.id, exported.manifest.dataset_id)
    assert name.endswith(".docx")
    assert format_id == "docx"
    assert payload


def test_dataset_comparison_contains_latest_qc_summaries(tmp_path: Path) -> None:
    project = create_project(tmp_path, name="Compare QC", project_id="compare-qc")
    data = DataPlatformApplicationService(tmp_path)
    first = data.register_source_file_result(project_id=project.id, source=_las(tmp_path / "v1.las", 10))
    second = data.register_source_file_result(
        project_id=project.id,
        source=_las(tmp_path / "v2.las", 20),
        previous_dataset_id=first.manifest.dataset_id,
    )
    qc = QCApplicationService(tmp_path)
    report = _report(qc)
    qc.persist_report(project_id=project.id, source_dataset_id=second.manifest.dataset_id, report=report)

    comparison = data.compare_dataset_versions(project.id, first.manifest.dataset_id, second.manifest.dataset_id)
    assert comparison["left_qc"]["available"] is False
    assert comparison["right_qc"]["available"] is True
    assert comparison["right_qc"]["status"] == report.status
