from pathlib import Path
from types import SimpleNamespace
import sys

from core.data_platform.segy_trace_header_inventory import SegyTraceHeaderInventoryAdapter
from services.data_platform_application_service import DataPlatformApplicationService


class _Attrs:
    def __init__(self, values):
        self.values = values
    def __getitem__(self, index):
        return self.values[index]


class _GeometryHandle:
    tracecount = 3
    samples = (0, 1, 2)
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def attributes(self, byte):
        values = {
            189: [100, 101, 102],
            193: [200, 200, 201],
            71: [-10, -10, -10],
            73: [5000000, 5000100, 5000200],
            77: [6000000, 6000100, 6000200],
        }
        return _Attrs(values[byte])


class _NoCoordinatesHandle(_GeometryHandle):
    def attributes(self, byte):
        if byte in (73, 77):
            return _Attrs([0, 0, 0])
        return super().attributes(byte)


def test_geometry_inventory_applies_negative_coordinate_scalar(monkeypatch, tmp_path: Path):
    path = tmp_path / "cube.segy"
    path.write_bytes(b"x")
    monkeypatch.setitem(sys.modules, "segyio", SimpleNamespace(open=lambda *a, **k: _GeometryHandle()))
    result = SegyTraceHeaderInventoryAdapter().scan(path)
    assert result.metadata["x_min"] == 500000.0
    assert result.metadata["y_max"] == 600020.0
    assert result.metadata["coordinate_valid_count"] == 3
    assert result.metadata["geometry_confidence"] == "high"
    assert "segy.geometry.low_confidence" not in result.warnings


def test_geometry_inventory_reports_missing_coordinates(monkeypatch, tmp_path: Path):
    path = tmp_path / "cube.segy"
    path.write_bytes(b"x")
    monkeypatch.setitem(sys.modules, "segyio", SimpleNamespace(open=lambda *a, **k: _NoCoordinatesHandle()))
    result = SegyTraceHeaderInventoryAdapter().scan(path)
    assert result.metadata["coordinate_valid_count"] == 0
    assert result.metadata["geometry_confidence"] == "low"
    assert "segy.geometry.coordinates_unavailable" in result.warnings
    assert "segy.geometry.low_confidence" in result.warnings


def test_application_service_exposes_coordinate_byte_mapping(monkeypatch, tmp_path: Path):
    path = tmp_path / "cube.segy"
    path.write_bytes(b"x")
    monkeypatch.setitem(sys.modules, "segyio", SimpleNamespace(open=lambda *a, **k: _GeometryHandle()))
    service = DataPlatformApplicationService(tmp_path / "projects")
    result = service.scan_segy_trace_headers(
        path, coordinate_scalar_byte=71, x_byte=73, y_byte=77
    )
    assert result.metadata["coordinate_scalar_header_byte"] == 71
    assert result.metadata["x_header_byte"] == 73
    assert result.metadata["y_header_byte"] == 77
