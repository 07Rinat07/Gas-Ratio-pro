from pathlib import Path

from core.data_platform import LasHeaderMetadataScanner, MetadataScanResult


def test_las_scanner_reads_header_only_and_extracts_metadata(tmp_path: Path) -> None:
    source = tmp_path / "well.las"
    source.write_text(
        "~Version\nVERS. 2.0 : version\n"
        "~Well\nWELL. Alpha-1 : well\nSTRT.M 1000 : start\nSTOP.M 1002 : stop\n"
        "STEP.M 0.5 : step\nNULL. -999.25 : null\nFLD. Tengiz : field\n"
        "~Curve\nDEPT.M : Depth\nGR.API : Gamma Ray\n"
        "~ASCII\n1000 50\n1000.5 51\n",
        encoding="utf-8",
    )

    result = LasHeaderMetadataScanner().scan(source)

    assert isinstance(result, MetadataScanResult)
    assert result.format_id == "las"
    assert result.complete is True
    assert result.metadata["well_name"] == "Alpha-1"
    assert result.metadata["start_depth"] == 1000
    assert result.metadata["stop_depth"] == 1002
    assert result.metadata["step"] == 0.5
    assert result.metadata["depth_unit"] == "M"
    assert result.metadata["curve_count"] == 2
    assert result.metadata["curve_mnemonics"] == "DEPT,GR"
    assert result.bytes_read < source.stat().st_size


def test_las_scanner_is_bounded_when_ascii_section_is_missing(tmp_path: Path) -> None:
    source = tmp_path / "broken.las"
    source.write_bytes(b"~Version\n" + b"X" * 5000)
    result = LasHeaderMetadataScanner(max_header_bytes=1024).scan(source)
    assert result.complete is False
    assert result.bytes_read == 1024
    assert "las.header.byte_limit_reached" in result.warnings
