from pathlib import Path

from core.dataframe_runtime_cache import DataframeRuntimeCache
from core.project_navigation_runtime_cache import ProjectNavigationRuntimeCache
from core.repository_io import AtomicJsonStore, RepositoryIOMetrics


def test_repository_mutation_invalidates_project_navigation_cache(tmp_path: Path) -> None:
    projects = tmp_path / "data" / "projects"
    project_dir = projects / "p1"
    project_dir.mkdir(parents=True)
    (project_dir / "project.json").write_text('{"name":"A"}', encoding="utf-8")

    cache = ProjectNavigationRuntimeCache()
    lookup = cache.lookup(projects, "p1")
    cache.store(project_id="p1", token=lookup.token, tree=({"id": "p1"},), counts={}, metadata_files=1)

    metrics = RepositoryIOMetrics()
    metrics.subscribe_mutations(
        "navigation", lambda event: cache.invalidate(event["project_id"], reason="repository-write")
    )
    AtomicJsonStore(repository="project", metrics=metrics).write(
        project_dir / "well.json", {"schema": "v1", "well": "W1"}
    )

    snapshot = cache.snapshot()
    assert snapshot["entries"] == 0
    assert snapshot["invalidations"] == 1
    assert snapshot["last_reason"] == "repository-write"
    mutation = metrics.mutation_snapshot()
    assert mutation["mutation_count"] == 1
    assert mutation["last_mutation"]["project_id"] == "p1"


def test_mutation_subscriber_failure_is_isolated(tmp_path: Path) -> None:
    metrics = RepositoryIOMetrics()
    metrics.subscribe_mutations("broken", lambda _event: (_ for _ in ()).throw(RuntimeError("boom")))
    path = tmp_path / "data" / "projects" / "p1" / "state.json"
    AtomicJsonStore(repository="test", metrics=metrics).write(path, {"schema": "v1"})
    snapshot = metrics.mutation_snapshot()
    assert snapshot["mutation_count"] == 1
    assert snapshot["mutation_failures"] == 1
    assert path.exists()


def test_delete_notifies_only_when_file_existed(tmp_path: Path) -> None:
    metrics = RepositoryIOMetrics()
    store = AtomicJsonStore(repository="test", metrics=metrics)
    path = tmp_path / "data" / "projects" / "p1" / "state.json"
    store.write(path, {"schema": "v1"})
    assert store.delete(path)
    assert not store.delete(path)
    assert metrics.mutation_snapshot()["mutation_count"] == 2
