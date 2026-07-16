from pathlib import Path

from core.data_platform.las_metadata_scanner import LasHeaderMetadataScanner
from core.data_platform.las_validation import validate_las_metadata


def _write(tmp_path: Path, row: bytes) -> Path:
    path = tmp_path / "legacy.las"
    path.write_bytes(
        b"~V\nVERS. 1.2\n~W\nWELL. OLD-1\nSTRT.M 1000\nSTOP.M 1001\nSTEP.M 0.5\nNULL. -999.25\n~C\nDEPT.M\nGR.API\nRHOB.G/C3\n~A\n" + row + b"\n"
    )
    return path


def test_decimal_comma_is_detected_from_one_bounded_row(tmp_path):
    result = LasHeaderMetadataScanner().scan(_write(tmp_path, b"1000,0;45,2;2,31"))
    assert result.metadata["data_delimiter"] == "semicolon"
    assert result.metadata["decimal_style"] == "comma"
    assert "las.compatibility.decimal_comma" in result.warnings
    codes = {item.code for item in validate_las_metadata(result)}
    assert "las.validation.decimal_comma" in codes


def test_fixed_width_legacy_row_is_detected(tmp_path):
    result = LasHeaderMetadataScanner().scan(_write(tmp_path, b"1000.0    45.2    2.31"))
    assert result.metadata["fixed_width_data"] is True
    assert "las.compatibility.fixed_width_data" in result.warnings
    codes = {item.code for item in validate_las_metadata(result)}
    assert "las.validation.fixed_width_data" in codes
