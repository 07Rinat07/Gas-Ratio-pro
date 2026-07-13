from core.render_queue import RenderQueue, RenderTask
from palettes.plot_cache import PlotCache


class PayloadFigure:
    def __init__(self, payload: str):
        self.payload = payload

    def to_json(self):
        return self.payload


class BrokenFigure:
    def to_json(self):
        raise ValueError("cannot serialize")


def test_render_queue_isolates_one_failed_plot_and_keeps_remaining_results():
    queue = RenderQueue(max_tasks=8)
    batch = queue.execute_resilient(
        [
            RenderTask("ok-a", lambda: "a"),
            RenderTask("broken", lambda: (_ for _ in ()).throw(ValueError("bad plot"))),
            RenderTask("ok-b", lambda: "b"),
        ]
    )
    assert [item.task_id for item in batch.completed] == ["ok-a", "ok-b"]
    assert [item.value for item in batch.completed] == ["a", "b"]
    assert len(batch.failed) == 1
    assert batch.failed[0].task_id == "broken"
    assert batch.failed[0].exception_type == "ValueError"
    assert queue.stats()["running"] == 0


def test_plot_cache_enforces_memory_budget_with_lru_eviction():
    cache = PlotCache(max_entries=8, max_bytes=100)
    first = cache.put("a", [PayloadFigure('{"data":[{"x":[1,2,3]}],"layout":{}}')])
    assert first.serialized_bytes > 0
    cache.put("b", [PayloadFigure('{"data":[{"x":[4,5,6]}],"layout":{}}')])
    cache.put("c", [PayloadFigure('{"data":[{"x":[7,8,9]}],"layout":{}}')])
    stats = cache.stats()
    assert stats.estimated_bytes <= stats.max_bytes
    assert stats.evictions >= 1


def test_plot_cache_rejects_single_bundle_larger_than_memory_budget():
    cache = PlotCache(max_entries=4, max_bytes=32)
    bundle = cache.put("large", [PayloadFigure('{"data":[{"text":"' + ('x' * 100) + '"}],"layout":{}}')])
    assert bundle.serialized_bytes > 32
    assert cache.get("large") is None
    assert cache.stats().oversize_rejections == 1


def test_plot_cache_reports_serialization_errors_without_crashing_workspace():
    cache = PlotCache(max_entries=2)
    bundle = cache.put("broken", [BrokenFigure()])
    assert bundle.screen_payloads[0] == {"data": [], "layout": {}}
    assert cache.stats().serialization_errors == 1
    assert bundle.serialized_sizes[0] > 0
