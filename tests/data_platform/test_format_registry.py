import json

import pytest

from core.data_platform.format_registry import DataFormatCapability, DataFormatRegistry, default_format_registry


def test_default_registry_detects_priority_industry_formats():
    registry = default_format_registry()
    assert registry.detect("cube.SEGY").format_id == "segy"
    assert registry.detect("logs.dlis").format_id == "dlis"
    assert registry.detect("model.epc").format_id == "resqml"
    assert registry.detect("map.gpkg").format_id == "geopackage"
    assert registry.detect("grid.grdecl").format_id == "grdecl"


def test_registry_rejects_extension_collisions():
    registry = DataFormatRegistry([DataFormatCapability("las", "LAS", (".las",))])
    with pytest.raises(ValueError, match="extension already registered"):
        registry.register(DataFormatCapability("other", "Other", ("las",)))


def test_registry_rejects_path_like_extensions():
    with pytest.raises(ValueError):
        DataFormatCapability("bad", "Bad", ("../../bad",))


def test_registry_snapshot_is_json_serializable():
    json.dumps(default_format_registry().snapshot())
