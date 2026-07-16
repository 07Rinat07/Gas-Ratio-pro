from core.data_platform.las_metadata_scanner import LasHeaderMetadataScanner
from core.data_platform.las_validation import validate_las_metadata


def test_scanner_reports_curve_and_data_column_mismatch(tmp_path):
    source = tmp_path / "mismatch.las"
    source.write_text(
        "~Version\nVERS. 1.2\n~Well\nWELL. Demo\nSTRT.M 1\nSTOP.M 2\nSTEP.M 1\nNULL. -999.25\n"
        "~Curve\nDEPT.M\nGR.API\nRHOB.G/C3\n~ASCII\n1 80\n",
        encoding="ascii",
    )
    result = LasHeaderMetadataScanner().scan(source)
    assert result.metadata["curve_count"] == 3
    assert result.metadata["data_column_count"] == 2
    assert result.metadata["curve_data_column_match"] is False
    assert "las.compatibility.curve_data_column_mismatch" in result.warnings
    codes = {finding.code for finding in validate_las_metadata(result)}
    assert "las.validation.curve_data_column_mismatch" in codes


def test_scanner_accepts_matching_curve_and_data_columns(tmp_path):
    source = tmp_path / "match.las"
    source.write_text(
        "~Version\nVERS. 2.0\n~Well\nWELL. Demo\nSTRT.M 1\nSTOP.M 2\nSTEP.M 1\nNULL. -999.25\n"
        "~Curve\nDEPT.M\nGR.API\n~ASCII\n1 80\n",
        encoding="ascii",
    )
    result = LasHeaderMetadataScanner().scan(source)
    assert result.metadata["data_column_count"] == 2
    assert result.metadata["curve_data_column_match"] is True
    assert "las.compatibility.curve_data_column_mismatch" not in result.warnings
