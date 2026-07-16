"""Stable LAS import validation codes independent from UI language."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .metadata_scanner import MetadataScanResult


@dataclass(frozen=True, slots=True)
class LasValidationFinding:
    code: str
    severity: str
    blocking: bool = False

    def to_dict(self) -> dict[str, object]:
        return {"code": self.code, "severity": self.severity, "blocking": self.blocking}


def validate_las_metadata(scan: MetadataScanResult | None, *, mode: str = "tolerant") -> tuple[LasValidationFinding, ...]:
    normalized_mode = str(mode or "tolerant").strip().lower()
    if normalized_mode not in {"tolerant", "strict"}:
        raise ValueError("LAS validation mode must be tolerant or strict")
    if scan is None:
        return (LasValidationFinding("las.validation.metadata_scan_unavailable", "warning"),)
    metadata: Mapping[str, object] = scan.metadata
    findings: list[LasValidationFinding] = []
    if not scan.complete:
        findings.append(LasValidationFinding("las.validation.header_incomplete", "warning"))
    warning_codes = set(scan.warnings)
    if "las.header.byte_limit_reached" in warning_codes:
        findings.append(LasValidationFinding("las.validation.header_byte_limit_reached", "warning"))
    if "las.version.missing_or_unparseable" in warning_codes:
        findings.append(LasValidationFinding("las.validation.version_missing_or_invalid", "warning"))
    if "las.compatibility.wrap_yes" in warning_codes:
        findings.append(LasValidationFinding("las.validation.wrap_yes", "warning"))
    if "las.header.nul_bytes_detected" in warning_codes:
        findings.append(LasValidationFinding("las.validation.nul_bytes_detected", "warning"))
    if "las.compatibility.legacy_encoding" in warning_codes:
        findings.append(LasValidationFinding("las.validation.legacy_encoding", "warning"))
    if "las.compatibility.nonstandard_data_delimiter" in warning_codes:
        findings.append(LasValidationFinding("las.validation.nonstandard_data_delimiter", "warning"))
    if "las.compatibility.decimal_comma" in warning_codes:
        findings.append(LasValidationFinding("las.validation.decimal_comma", "warning"))
    if "las.compatibility.fixed_width_data" in warning_codes:
        findings.append(LasValidationFinding("las.validation.fixed_width_data", "warning"))
    if "las.compatibility.curve_data_column_mismatch" in warning_codes:
        findings.append(LasValidationFinding("las.validation.curve_data_column_mismatch", "warning"))
    if "las.compatibility.inconsistent_data_columns" in warning_codes:
        findings.append(LasValidationFinding("las.validation.inconsistent_data_columns", "warning"))
    if bool(metadata.get("legacy_las", False)):
        findings.append(LasValidationFinding("las.validation.legacy_format", "warning"))
    if not str(metadata.get("well_name", "")).strip():
        findings.append(LasValidationFinding("las.validation.well_name_missing", "warning"))
    if int(metadata.get("curve_count", 0) or 0) <= 0:
        findings.append(LasValidationFinding("las.validation.curves_missing", "error", True))
    if metadata.get("start_depth", "") == "" or metadata.get("stop_depth", "") == "":
        findings.append(LasValidationFinding("las.validation.depth_range_missing", "warning"))
    if metadata.get("null_value", "") == "":
        findings.append(LasValidationFinding("las.validation.null_value_missing", "warning"))
    if metadata.get("step", "") == "":
        findings.append(LasValidationFinding("las.validation.step_missing", "warning"))
    if normalized_mode == "strict":
        strict_codes = {
            "las.validation.version_missing_or_invalid",
            "las.validation.legacy_format",
            "las.validation.wrap_yes",
            "las.validation.legacy_encoding",
            "las.validation.nonstandard_data_delimiter",
            "las.validation.decimal_comma",
            "las.validation.fixed_width_data",
            "las.validation.curve_data_column_mismatch",
            "las.validation.inconsistent_data_columns",
        }
        findings = [
            LasValidationFinding(item.code, "error" if item.code in strict_codes else item.severity, item.blocking or item.code in strict_codes)
            for item in findings
        ]
    return tuple(findings)
