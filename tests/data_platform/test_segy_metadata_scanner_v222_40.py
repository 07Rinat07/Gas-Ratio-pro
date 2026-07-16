from pathlib import Path

from core.data_platform import SegyHeaderMetadataScanner


def _write_segy(path: Path) -> None:
    text = ("C 1 TEST SEG-Y HEADER".ljust(80) * 40).encode("ascii")
    binary = bytearray(400)
    binary[16:18] = (2000).to_bytes(2, "big")
    binary[20:22] = (3).to_bytes(2, "big")
    binary[24:26] = (5).to_bytes(2, "big")
    binary[300:302] = bytes((2, 1))
    binary[302:304] = (1).to_bytes(2, "big")
    binary[304:306] = (0).to_bytes(2, "big")
    trace = bytes(240 + 3 * 4)
    path.write_bytes(text + bytes(binary) + trace * 2)


def test_scans_only_textual_and_binary_headers(tmp_path: Path) -> None:
    path = tmp_path / "cube.segy"
    _write_segy(path)
    result = SegyHeaderMetadataScanner().scan(path)
    assert result.bytes_read == 3600
    assert result.complete is True
    assert result.metadata["sample_interval_us"] == 2000
    assert result.metadata["samples_per_trace"] == 3
    assert result.metadata["sample_format_code"] == 5
    assert result.metadata["segy_revision_major"] == 2
    assert result.metadata["segy_revision_minor"] == 1
    assert result.metadata["trace_count_estimate"] == 2


def test_incomplete_header_is_nonfatal(tmp_path: Path) -> None:
    path = tmp_path / "broken.sgy"
    path.write_bytes(b"short")
    result = SegyHeaderMetadataScanner().scan(path)
    assert result.complete is False
    assert result.warnings == ("segy.header.incomplete",)
