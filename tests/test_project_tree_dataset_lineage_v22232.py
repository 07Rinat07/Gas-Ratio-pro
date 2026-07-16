from pathlib import Path

from projects import create_project
from projects.project_tree import build_project_tree, flatten_project_tree
from services.data_platform_application_service import DataPlatformApplicationService


def _write_las(path: Path, value: int) -> Path:
    path.write_text(
        "~V\nVERS. 2.0\nWRAP. NO\n~W\nWELL. W-1\nSTRT.M 1000\nSTOP.M 1001\nSTEP.M 1\nNULL. -999.25\n"
        "~C\nDEPT.M\nGR.API\n~A\n1000 %d\n1001 %d\n" % (value, value + 1),
        encoding="utf-8",
    )
    return path


def test_project_tree_loads_dataset_lineage_only_when_requested(tmp_path):
    project = create_project(tmp_path, name="Lineage", project_id="lineage")
    service = DataPlatformApplicationService(tmp_path)
    first = service.register_source_file_result(project_id=project.id, source=_write_las(tmp_path / "v1.las", 10))
    service.register_source_file_result(
        project_id=project.id,
        source=_write_las(tmp_path / "v2.las", 20),
        previous_dataset_id=first.manifest.dataset_id,
    )

    timings: dict[str, float] = {}
    deferred = build_project_tree(tmp_path, project.id, include_sections=set(), section_timings_ms=timings)
    deferred_nodes = {node.id: node for _level, node in flatten_project_tree(deferred)}
    assert deferred_nodes["folder:datasets"].children[0].metadata["deferred"] == 1
    assert "datasets" not in timings

    loaded = build_project_tree(tmp_path, project.id, include_sections={"datasets"}, section_timings_ms=timings)
    nodes = {node.id: node for _level, node in flatten_project_tree(loaded)}
    lineage = nodes[f"dataset_lineage:{first.manifest.lineage_id}"]
    assert lineage.metadata["version_count"] == 2
    assert [child.metadata["version"] for child in lineage.children] == [1, 2]
    assert "datasets" in timings
