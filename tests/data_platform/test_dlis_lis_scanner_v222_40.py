from pathlib import Path

from core.data_platform import DlisLisMetadataScanner, default_format_registry


def test_registry_has_separate_lis79_capability() -> None:
    registry = default_format_registry()
    assert registry.detect("archive.lis").format_id == "lis79"
    assert registry.detect("modern.dlis").format_id == "dlis"


def test_missing_optional_dlisio_is_a_stable_scan_result(tmp_path: Path) -> None:
    path = tmp_path / "archive.dlis"
    path.write_bytes(b"TIF" + bytes(5000))
    result = DlisLisMetadataScanner("dlis").scan(path)
    assert result.format_id == "dlis"
    assert result.complete is False
    assert result.bytes_read == 4096
    assert result.metadata["optional_adapter"] == "dlisio"
    assert result.metadata["adapter_available"] is False
    assert result.warnings == ("dlis.adapter.dlisio_unavailable",)
