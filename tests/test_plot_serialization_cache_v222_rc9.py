from palettes.plot_cache import PlotCache


class CountingFigure:
    def __init__(self, value: int):
        self.value = value
        self.calls = 0

    def to_json(self):
        self.calls += 1
        return '{"data":[{"y":[' + str(self.value) + ']}],"layout":{}}'


def test_plot_cache_serializes_each_screen_figure_once():
    figure = CountingFigure(3)
    cache = PlotCache(max_entries=2)
    bundle = cache.put("a", [figure])
    assert figure.calls == 1
    assert bundle.screen_payloads[0]["data"][0]["y"] == [3]
    assert cache.get("a") is bundle
    assert figure.calls == 1
    assert cache.stats().serialized_figures == 1


def test_plot_cache_provides_stable_fingerprint():
    first = CountingFigure(7)
    second = CountingFigure(7)
    cache = PlotCache(max_entries=2)
    a = cache.put("a", [first])
    b = cache.put("b", [second])
    assert a.fingerprints == b.fingerprints
    assert a.serialized_bytes > 0


def test_plot_cache_lru_still_evicts_serialized_payloads():
    cache = PlotCache(max_entries=1)
    cache.put("a", [CountingFigure(1)])
    cache.put("b", [CountingFigure(2)])
    assert cache.get("a") is None
    assert cache.get("b") is not None
    assert cache.stats().evictions == 1
