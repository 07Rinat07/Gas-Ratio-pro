from pathlib import Path
import sys
from types import SimpleNamespace

from services.data_platform_application_service import DataPlatformApplicationService


class _Attrs:
    def __init__(self, values): self.values = values
    def __getitem__(self, index): return self.values[index]

class _Handle:
    tracecount = 2
    samples = (0, 1)
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def attributes(self, byte): return _Attrs([1, 2] if byte == 189 else [10, 10])


def _write_segy(path: Path):
    text = ("C 1 SYNTHETIC".ljust(80) * 40).encode('ascii')
    binary = bytearray(400)
    binary[16:18] = (1000).to_bytes(2, 'big')
    binary[20:22] = (2).to_bytes(2, 'big')
    binary[24:26] = (5).to_bytes(2, 'big')
    binary[300:302] = bytes((2, 1))
    binary[302:304] = (1).to_bytes(2, 'big')
    path.write_bytes(text + binary + bytes(240 + 8))


def test_service_builds_metadata_only_preview(tmp_path: Path):
    path = tmp_path / 'cube.segy'; _write_segy(path)
    service = DataPlatformApplicationService(tmp_path / 'projects')
    preview = service.build_import_preview(path, translate=lambda key, **kw: key.format(**kw))
    assert preview['format_id'] == 'segy'
    assert preview['bytes_read'] == 3600
    assert any(item['key'] == 'samples_per_trace' for item in preview['fields'])


def test_service_runs_optional_trace_inventory(monkeypatch, tmp_path: Path):
    path = tmp_path / 'cube.segy'; path.write_bytes(b'x')
    monkeypatch.setitem(sys.modules, 'segyio', SimpleNamespace(open=lambda *a, **k: _Handle()))
    service = DataPlatformApplicationService(tmp_path / 'projects')
    result = service.scan_segy_trace_headers(path)
    assert result.metadata['trace_count'] == 2
    assert result.metadata['inline_unique_count'] == 2
