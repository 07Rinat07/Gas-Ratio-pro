from pathlib import Path

from core.data_platform import ImportWizardState, metadata_quick_qc
from core.data_platform.metadata_scanner import MetadataScanResult
from services.data_platform_application_service import DataPlatformApplicationService


def _las(path: Path, well: str = "A") -> Path:
    path.write_text(
        "~V\nVERS. 2.0\n~W\nWELL. %s\nSTRT.M 1000\nSTOP.M 1001\nSTEP.M 0.5\nNULL. -999.25\n~C\nDEPT.M\nGR.API\n~A\n1000 10\n1000.5 11\n1001 12\n" % well,
        encoding="utf-8",
    )
    return path


def test_wizard_state_is_json_safe_and_ordered():
    state = ImportWizardState(project_id="p")
    state = state.advance("preview", source_names=("a.las",), format_id="las")
    state = state.advance("configure", profile_id="las-modern", options={"mode": "strict"})
    assert state.to_dict()["step"] == "configure"
    assert state.to_dict()["options"] == {"mode": "strict"}


def test_batch_import_isolates_failures_and_persists_readiness(tmp_path: Path):
    projects = tmp_path / "projects"
    service = DataPlatformApplicationService(projects)
    good = _las(tmp_path / "good.las")
    bad = tmp_path / "bad.unknown"
    bad.write_text("x", encoding="utf-8")

    result = service.run_batch_import(project_id="p", sources=[good, bad], actor="tester")

    assert result.success_count == 1
    assert result.failed_count == 1
    assert result.items[0].readiness_score > 0
    manifest = service.manifests.load("p", result.items[0].dataset_id)
    assert manifest.metadata["readiness_status"] in {"ready", "review", "blocked"}
    assert "quick_qc_status" in manifest.metadata


def test_quick_qc_is_stable_for_supported_formats():
    result = MetadataScanResult(format_id="segy", metadata={}, warnings=(), bytes_read=3600, complete=True)
    qc = metadata_quick_qc(result)
    assert qc["status"] == "review"
    assert "segy.quick_qc.samples_per_trace_missing" in qc["warning_codes"]


def test_project_tree_exposes_readiness_badge_metadata(tmp_path: Path):
    from projects.project_tree import build_project_tree, flatten_project_tree
    from projects.repository import create_project

    create_project(tmp_path, name="P", project_id="p")
    service = DataPlatformApplicationService(tmp_path)
    item = service.register_source_file_result(project_id="p", source=_las(tmp_path / "well.las"))
    tree = build_project_tree(tmp_path, "p", include_sections={"datasets"})
    nodes = {node.id: node for _, node in flatten_project_tree(tree)}
    version = nodes[f"dataset:{item.manifest.dataset_id}"]
    assert "readiness_score" in version.metadata
    assert "readiness" in nodes[f"dataset_lineage:{item.manifest.lineage_id}"].status
