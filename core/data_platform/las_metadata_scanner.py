"""Header-only LAS metadata scanner with bounded I/O."""
from __future__ import annotations

import re
from pathlib import Path

from .metadata_scanner import MetadataScanResult

_SECTION_RE = re.compile(r"^\s*~\s*([A-Za-z]+)")
_PARAMETER_RE = re.compile(r"^\s*([^.#:\s]+)\s*(?:\.([^\s:]*))?\s*([^:]*)\s*(?::.*)?$")


class LasHeaderMetadataScanner:
    format_id = "las"

    def __init__(self, *, max_header_bytes: int = 2 * 1024 * 1024, max_sample_rows: int = 8) -> None:
        if max_header_bytes < 1024:
            raise ValueError("max_header_bytes must be at least 1024")
        if max_sample_rows < 1 or max_sample_rows > 64:
            raise ValueError("max_sample_rows must be between 1 and 64")
        self.max_header_bytes = int(max_header_bytes)
        self.max_sample_rows = int(max_sample_rows)

    def scan(self, source: Path | str) -> MetadataScanResult:
        path = Path(source)
        raw = bytearray()
        reached_ascii = False
        data_sample_lines: list[bytes] = []
        with path.open("rb") as handle:
            while len(raw) < self.max_header_bytes:
                line = handle.readline(min(64 * 1024, self.max_header_bytes - len(raw)))
                if not line:
                    break
                raw.extend(line)
                probe = line.decode("latin-1", errors="replace")
                section = _SECTION_RE.match(probe)
                if section and section.group(1).strip().lower().startswith("a"):
                    reached_ascii = True
                    # Read only a small bounded sample for structural diagnostics.
                    while len(data_sample_lines) < self.max_sample_rows:
                        candidate = handle.readline(64 * 1024)
                        if not candidate:
                            break
                        if candidate.strip() and not candidate.lstrip().startswith(b"#"):
                            data_sample_lines.append(candidate.rstrip(b"\r\n"))
                    break

        encoding, text = _decode_header(bytes(raw))
        metadata: dict[str, str | int | float | bool | None] = {
            "header_bytes": len(raw),
            "header_complete": reached_ascii,
            "curve_count": 0,
            "header_encoding": encoding,
        }
        warnings: list[str] = []
        if encoding not in {"utf-8", "utf-8-sig", "ascii"}:
            warnings.append("las.compatibility.legacy_encoding")
        first_data_line = data_sample_lines[0] if data_sample_lines else b""
        delimiter = _detect_data_delimiter(first_data_line)
        metadata["data_delimiter"] = delimiter
        decimal_style = _detect_decimal_style(first_data_line, delimiter)
        metadata["decimal_style"] = decimal_style
        fixed_width = _looks_fixed_width(first_data_line, delimiter)
        metadata["fixed_width_data"] = fixed_width
        column_counts = tuple(_count_data_columns(line, delimiter) for line in data_sample_lines)
        sampled_depths = tuple(value for value in (_first_numeric_value(line, delimiter, decimal_style) for line in data_sample_lines) if value is not None)
        data_column_count = column_counts[0] if column_counts else 0
        metadata["data_column_count"] = data_column_count
        metadata["data_sample_row_count"] = len(data_sample_lines)
        metadata["data_column_counts"] = ",".join(str(item) for item in column_counts)
        metadata["data_column_count_stable"] = len(set(column_counts)) <= 1 if column_counts else None
        metadata["data_column_count_min"] = min(column_counts) if column_counts else 0
        metadata["data_column_count_max"] = max(column_counts) if column_counts else 0
        _apply_depth_sample_diagnostics(metadata, warnings, sampled_depths)
        if delimiter in {"comma", "semicolon", "tab"}:
            warnings.append("las.compatibility.nonstandard_data_delimiter")
        if decimal_style == "comma":
            warnings.append("las.compatibility.decimal_comma")
        if fixed_width:
            warnings.append("las.compatibility.fixed_width_data")
        current_section = ""
        curves: list[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            section = _SECTION_RE.match(line)
            if section:
                current_section = section.group(1).strip().lower()
                if current_section.startswith("a"):
                    break
                continue
            parsed = _PARAMETER_RE.match(line)
            if not parsed:
                continue
            mnemonic = parsed.group(1).strip().upper()
            unit = (parsed.group(2) or "").strip()
            value = (parsed.group(3) or "").strip()
            if current_section.startswith("v") and mnemonic == "VERS":
                metadata["las_version"] = value
            elif current_section.startswith("v") and mnemonic == "WRAP":
                metadata["wrap_mode"] = value.strip().upper()
            elif current_section.startswith("w"):
                mapping = {
                    "WELL": "well_name",
                    "UWI": "uwi",
                    "API": "api",
                    "STRT": "start_depth",
                    "STOP": "stop_depth",
                    "STEP": "step",
                    "NULL": "null_value",
                    "COMP": "company",
                    "FLD": "field",
                    "LOC": "location",
                }
                key = mapping.get(mnemonic)
                if key:
                    metadata[key] = _number_or_text(value)
                    if unit and mnemonic in {"STRT", "STOP", "STEP"}:
                        metadata["depth_unit"] = unit
            elif current_section.startswith("c"):
                curves.append(mnemonic)

        _apply_declared_step_diagnostic(metadata, warnings)
        metadata["curve_count"] = len(curves)
        metadata["curve_data_column_match"] = (len(curves) == int(metadata.get("data_column_count", 0) or 0)) if first_data_line and curves else None
        if first_data_line and curves and metadata["curve_data_column_match"] is False:
            warnings.append("las.compatibility.curve_data_column_mismatch")
        if column_counts and len(set(column_counts)) > 1:
            warnings.append("las.compatibility.inconsistent_data_columns")
        metadata["curve_mnemonics"] = ",".join(curves[:256])
        _apply_las_compatibility_metadata(metadata, warnings, current_section=current_section)
        if str(metadata.get("wrap_mode", "")).upper().startswith("Y"):
            warnings.append("las.compatibility.wrap_yes")
        if b"\x00" in raw:
            warnings.append("las.header.nul_bytes_detected")
        if not reached_ascii:
            warnings.append("las.header.ascii_section_not_reached")
        if len(raw) >= self.max_header_bytes and not reached_ascii:
            warnings.append("las.header.byte_limit_reached")
        return MetadataScanResult(
            format_id=self.format_id,
            metadata=metadata,
            warnings=tuple(warnings),
            bytes_read=len(raw),
            complete=reached_ascii,
        )


def _number_or_text(value: str) -> str | int | float:
    candidate = value.strip()
    try:
        number = float(candidate)
    except ValueError:
        return candidate
    return int(number) if number.is_integer() else number


def _apply_las_compatibility_metadata(
    metadata: dict[str, str | int | float | bool | None],
    warnings: list[str],
    *,
    current_section: str,
) -> None:
    """Classify LAS compatibility without mutating source content.

    LAS files older than 2.0 are accepted in tolerant legacy mode.  The
    scanner records stable warning codes instead of rewriting headers or
    guessing missing engineering values.
    """
    raw_version = str(metadata.get("las_version") or "").strip()
    parsed_version = _parse_las_version(raw_version)
    metadata["las_version_normalized"] = parsed_version if parsed_version is not None else ""

    if parsed_version is not None and parsed_version < 2.0:
        metadata["las_compatibility_mode"] = "legacy-pre-2.0"
        metadata["legacy_las"] = True
        metadata["las_version_family"] = "1.x"
        warnings.append("las.compatibility.legacy_pre_2_0")
        return

    if parsed_version is None:
        metadata["las_compatibility_mode"] = "legacy-tolerant"
        metadata["legacy_las"] = True
        metadata["las_version_family"] = "unknown"
        warnings.append("las.version.missing_or_unparseable")
        warnings.append("las.compatibility.legacy_tolerant_mode")
        return

    metadata["las_compatibility_mode"] = "standard"
    metadata["legacy_las"] = False
    metadata["las_version_family"] = "2.x+"


def _parse_las_version(value: str) -> float | None:
    match = re.search(r"(?<!\d)(\d+(?:[.,]\d+)?)", value)
    if not match:
        return None
    try:
        return float(match.group(1).replace(",", "."))
    except ValueError:
        return None


def _decode_header(raw: bytes) -> tuple[str, str]:
    if raw.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig", raw.decode("utf-8-sig", errors="replace")
    try:
        text = raw.decode("utf-8")
        return ("ascii" if raw.isascii() else "utf-8"), text
    except UnicodeDecodeError:
        try:
            return "cp1251", raw.decode("cp1251")
        except UnicodeDecodeError:
            return "latin-1", raw.decode("latin-1", errors="replace")




def _apply_declared_step_diagnostic(metadata: dict[str, str | int | float | bool | None], warnings: list[str]) -> None:
    declared = metadata.get("step")
    observed = metadata.get("observed_step")
    try:
        declared_number = abs(float(declared))
        observed_number = abs(float(observed))
    except (TypeError, ValueError):
        return
    matches = abs(declared_number - observed_number) <= max(1e-9, declared_number * 1e-6)
    metadata["declared_step_matches_observed"] = matches
    if not matches:
        warnings.append("las.compatibility.declared_step_mismatch")


def _first_numeric_value(line: bytes, delimiter: str, decimal_style: str) -> float | None:
    if not line:
        return None
    text = line.decode("latin-1", errors="replace").strip()
    if delimiter == "semicolon":
        token = text.split(";", 1)[0]
    elif delimiter == "comma" and decimal_style != "comma":
        token = text.split(",", 1)[0]
    elif delimiter == "tab":
        token = text.split("\t", 1)[0]
    else:
        parts = text.split()
        token = parts[0] if parts else ""
    token = token.strip().replace(",", ".")
    try:
        return float(token)
    except ValueError:
        return None


def _apply_depth_sample_diagnostics(metadata: dict[str, str | int | float | bool | None], warnings: list[str], depths: tuple[float, ...]) -> None:
    metadata["depth_sample_count"] = len(depths)
    if len(depths) < 2:
        metadata["depth_monotonic"] = None
        metadata["observed_step_stable"] = None
        return
    deltas = tuple(depths[i + 1] - depths[i] for i in range(len(depths) - 1))
    increasing = all(delta > 0 for delta in deltas)
    decreasing = all(delta < 0 for delta in deltas)
    monotonic = increasing or decreasing
    metadata["depth_monotonic"] = monotonic
    metadata["depth_direction"] = "increasing" if increasing else ("decreasing" if decreasing else "mixed")
    if not monotonic:
        warnings.append("las.compatibility.non_monotonic_depth")
    absolute = tuple(abs(delta) for delta in deltas if delta != 0)
    if not absolute:
        metadata["observed_step_stable"] = False
        warnings.append("las.compatibility.unstable_step")
        return
    reference = absolute[0]
    tolerance = max(1e-9, abs(reference) * 1e-6)
    stable = all(abs(value - reference) <= tolerance for value in absolute[1:])
    metadata["observed_step"] = reference
    metadata["observed_step_min"] = min(absolute)
    metadata["observed_step_max"] = max(absolute)
    metadata["observed_step_stable"] = stable
    if not stable:
        warnings.append("las.compatibility.unstable_step")


def _detect_data_delimiter(line: bytes) -> str:
    if not line:
        return "unknown"
    if b"\t" in line:
        return "tab"
    if b";" in line:
        return "semicolon"
    if b"," in line and b" " not in line.strip():
        return "comma"
    if any(ch in line for ch in (b" ", b"\t")):
        return "whitespace"
    return "unknown"


def _detect_decimal_style(line: bytes, delimiter: str) -> str:
    """Detect decimal comma without parsing the complete data section."""
    if not line:
        return "unknown"
    text = line.decode("latin-1", errors="replace")
    if delimiter == "semicolon" and re.search(r"(?<!\d)[+-]?\d+,\d+(?!\d)", text):
        return "comma"
    if re.search(r"(?<!\d)[+-]?\d+\.\d+(?!\d)", text):
        return "dot"
    return "integer-or-unknown"


def _looks_fixed_width(line: bytes, delimiter: str) -> bool:
    """Conservatively flag fixed-width legacy rows using one bounded sample."""
    if not line or delimiter != "whitespace":
        return False
    text = line.decode("latin-1", errors="replace").rstrip()
    gaps = re.findall(r" {2,}", text)
    tokens = re.split(r" {2,}", text.strip())
    return len(gaps) >= 2 and len(tokens) >= 3 and all(token.strip() for token in tokens)


def _count_data_columns(line: bytes, delimiter: str) -> int:
    """Count columns from one bounded data row without parsing the dataset."""
    if not line:
        return 0
    text = line.decode("latin-1", errors="replace").strip()
    if not text:
        return 0
    if delimiter == "tab":
        return len([item for item in text.split("\t") if item.strip()])
    if delimiter == "semicolon":
        return len([item for item in text.split(";") if item.strip()])
    if delimiter == "comma":
        return len([item for item in text.split(",") if item.strip()])
    if delimiter == "whitespace":
        return len(re.findall(r"\S+", text))
    return 1
