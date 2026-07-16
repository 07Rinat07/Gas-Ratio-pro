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


def test_las_scanner_accepts_pre_2_0_legacy_file(tmp_path: Path) -> None:
    source = tmp_path / "archive_legacy.las"
    source.write_text(
        "~V\nVERS. 1.2 : legacy version\n"
        "~W\nWELL. Archive-17 : well\nSTRT.M 1200 : start\nSTOP.M 1201 : stop\n"
        "~C\nDEPT.M : depth\nGR.API : gamma ray\n"
        "~A\n1200 42\n",
        encoding="latin-1",
    )

    result = LasHeaderMetadataScanner().scan(source)

    assert result.complete is True
    assert result.metadata["las_version"] == "1.2"
    assert result.metadata["las_version_normalized"] == 1.2
    assert result.metadata["las_version_family"] == "1.x"
    assert result.metadata["legacy_las"] is True
    assert result.metadata["las_compatibility_mode"] == "legacy-pre-2.0"
    assert "las.compatibility.legacy_pre_2_0" in result.warnings


def test_las_scanner_uses_tolerant_mode_when_version_is_missing(tmp_path: Path) -> None:
    source = tmp_path / "archive_without_version.las"
    source.write_text(
        "~WELL\nWELL. Archive-Unknown : well\n"
        "~CURVE\nDEPT.M : depth\n"
        "~ASCII\n1000\n",
        encoding="latin-1",
    )

    result = LasHeaderMetadataScanner().scan(source)

    assert result.complete is True
    assert result.metadata["legacy_las"] is True
    assert result.metadata["las_compatibility_mode"] == "legacy-tolerant"
    assert "las.version.missing_or_unparseable" in result.warnings
    assert "las.compatibility.legacy_tolerant_mode" in result.warnings
