from pathlib import Path
import sys
from types import SimpleNamespace

from core.data_platform import SegyTraceHeaderInventoryAdapter


class _Attributes:
    def __init__(self, values): self.values = values
    def __getitem__(self, index): return self.values[index]


class _Handle:
    tracecount = 3
    samples = (0, 1, 2, 3)
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def attributes(self, byte):
        return _Attributes([10, 11, 12] if byte == 189 else [20, 20, 21])


def test_optional_inventory_uses_manual_header_bytes(monkeypatch, tmp_path: Path):
    path = tmp_path / 'cube.segy'; path.write_bytes(b'x')
    monkeypatch.setitem(sys.modules, 'segyio', SimpleNamespace(open=lambda *a, **k: _Handle()))
    result = SegyTraceHeaderInventoryAdapter(inline_byte=189, crossline_byte=193).scan(path)
    assert result.complete is True
    assert result.metadata['trace_count'] == 3
    assert result.metadata['inline_min'] == 10
    assert result.metadata['inline_max'] == 12
    assert result.metadata['crossline_unique_count'] == 2


def test_invalid_trace_header_mapping_is_rejected():
    try:
        SegyTraceHeaderInventoryAdapter(inline_byte=239)
    except ValueError:
        pass
    else:
        raise AssertionError('invalid byte position must fail')
