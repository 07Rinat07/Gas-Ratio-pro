"""Header-only LAS metadata scanner with bounded I/O."""
from __future__ import annotations

import re
from pathlib import Path

from .metadata_scanner import MetadataScanResult

_SECTION_RE = re.compile(r"^\s*~\s*([A-Za-z]+)")
_PARAMETER_RE = re.compile(r"^\s*([^.#:\s]+)\s*(?:\.([^\s:]*))?\s*([^:]*)\s*(?::.*)?$")


class LasHeaderMetadataScanner:
    format_id = "las"

    def __init__(self, *, max_header_bytes: int = 2 * 1024 * 1024) -> None:
        if max_header_bytes < 1024:
            raise ValueError("max_header_bytes must be at least 1024")
        self.max_header_bytes = int(max_header_bytes)

    def scan(self, source: Path | str) -> MetadataScanResult:
        path = Path(source)
        raw = bytearray()
        reached_ascii = False
        first_data_line = b""
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
                    # Read only one bounded data row for delimiter diagnostics.
                    while True:
                        candidate = handle.readline(64 * 1024)
                        if not candidate:
                            break
                        if candidate.strip() and not candidate.lstrip().startswith(b"#"):
                            first_data_line = candidate.rstrip(b"\r\n")
                            break
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
        delimiter = _detect_data_delimiter(first_data_line)
        metadata["data_delimiter"] = delimiter
        if delimiter in {"comma", "semicolon", "tab"}:
            warnings.append("las.compatibility.nonstandard_data_delimiter")
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

        metadata["curve_count"] = len(curves)
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
