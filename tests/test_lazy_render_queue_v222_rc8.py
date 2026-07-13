from core.lazy_workspace import LazyWorkspaceRegistry, WorkspaceRoute
from core.render_queue import RenderQueue, RenderTask


def test_render_queue_runs_unique_tasks_in_order():
    calls = []
    queue = RenderQueue(max_tasks=8)
    results = queue.execute([
        RenderTask("a", lambda: calls.append("a") or 1),
        RenderTask("a", lambda: calls.append("duplicate") or 99),
        RenderTask("b", lambda: calls.append("b") or 2),
    ])
    assert calls == ["a", "b"]
    assert [result.value for result in results] == [1, 2]
    assert queue.stats()["duplicates"] == 1


def test_render_queue_releases_running_task_after_error():
    queue = RenderQueue()
    try:
        queue.execute([RenderTask("broken", lambda: (_ for _ in ()).throw(RuntimeError("x")))])
    except RuntimeError:
        pass
    assert queue.stats()["running"] == 0
    assert queue.stats()["failed"] == 1


def test_lazy_workspace_registry_resolves_only_requested_route():
    called = []
    registry = LazyWorkspaceRegistry({
        "nav.a": WorkspaceRoute("nav.a", "a", lambda project: called.append(("a", project))),
        "nav.b": WorkspaceRoute("nav.b", "b", lambda project: called.append(("b", project))),
    })
    route = registry.resolve("nav.b")
    assert route is not None
    route.renderer("project")
    assert called == [("b", "project")]
    assert registry.resolve("nav.missing") is None
