"""Bounded SEG-Y textual/binary header scanner without trace materialization."""
from __future__ import annotations

from pathlib import Path

from .metadata_scanner import MetadataScanResult

_SAMPLE_BYTES = {1: 4, 2: 4, 3: 2, 5: 4, 6: 8, 7: 3, 8: 1, 9: 8, 10: 4, 11: 2, 12: 8, 15: 3, 16: 1}


def _u16(data: bytes, offset: int, *, endian: str = "big") -> int:
    return int.from_bytes(data[offset : offset + 2], endian, signed=False)


def _decode_textual_header(raw: bytes) -> tuple[str, str]:
    ascii_text = raw.decode("ascii", errors="replace")
    ascii_printable = sum(ch.isprintable() or ch in "\r\n\t" for ch in ascii_text)
    try:
        ebcdic_text = raw.decode("cp500", errors="replace")
    except LookupError:
        ebcdic_text = ""
    ebcdic_printable = sum(ch.isprintable() or ch in "\r\n\t" for ch in ebcdic_text)
    if ebcdic_printable > ascii_printable:
        return ebcdic_text, "ebcdic-cp500"
    return ascii_text, "ascii"


class SegyHeaderMetadataScanner:
    """Read only the 3200-byte textual and 400-byte binary SEG-Y headers."""

    format_id = "segy"
    header_bytes = 3600

    def scan(self, source: Path | str) -> MetadataScanResult:
        path = Path(source)
        with path.open("rb") as handle:
            raw = handle.read(self.header_bytes)
        warnings: list[str] = []
        if len(raw) < self.header_bytes:
            return MetadataScanResult(
                format_id=self.format_id,
                metadata={"file_size_bytes": path.stat().st_size, "header_complete": False},
                warnings=("segy.header.incomplete",),
                bytes_read=len(raw),
                complete=False,
            )

        textual, encoding = _decode_textual_header(raw[:3200])
        binary = raw[3200:3600]
        sample_interval_us = _u16(binary, 16)
        samples_per_trace = _u16(binary, 20)
        sample_format_code = _u16(binary, 24)
        revision_raw = _u16(binary, 300)
        revision_major = (revision_raw >> 8) & 0xFF
        revision_minor = revision_raw & 0xFF
        fixed_length_flag = _u16(binary, 302)
        extended_textual_headers = _u16(binary, 304)
        if extended_textual_headers >= 0x8000:
            extended_textual_headers = extended_textual_headers - 0x10000
        sample_size = _SAMPLE_BYTES.get(sample_format_code, 0)
        file_size = path.stat().st_size
        trace_start = 3600 + max(0, extended_textual_headers) * 3200
        trace_count_estimate: int | None = None
        if fixed_length_flag == 1 and samples_per_trace and sample_size and file_size >= trace_start:
            trace_bytes = 240 + samples_per_trace * sample_size
            if trace_bytes:
                trace_count_estimate = (file_size - trace_start) // trace_bytes
        if sample_format_code not in _SAMPLE_BYTES:
            warnings.append("segy.binary.unsupported_sample_format")
        if revision_major == 0 and revision_minor == 0:
            warnings.append("segy.binary.revision_unspecified")
        if extended_textual_headers < 0:
            warnings.append("segy.binary.variable_extended_headers")

        first_lines = [line.rstrip() for line in textual.replace("\r", "\n").split("\n") if line.strip()][:5]
        metadata: dict[str, str | int | float | bool | None] = {
            "file_size_bytes": file_size,
            "header_complete": True,
            "textual_header_encoding": encoding,
            "textual_header_preview": " | ".join(first_lines)[:1000],
            "sample_interval_us": sample_interval_us,
            "samples_per_trace": samples_per_trace,
            "sample_format_code": sample_format_code,
            "sample_size_bytes": sample_size,
            "segy_revision_major": revision_major,
            "segy_revision_minor": revision_minor,
            "fixed_length_trace_flag": fixed_length_flag,
            "extended_textual_header_count": extended_textual_headers,
            "trace_data_offset_bytes": trace_start,
            "trace_count_estimate": trace_count_estimate,
        }
        return MetadataScanResult(
            format_id=self.format_id,
            metadata=metadata,
            warnings=tuple(warnings),
            bytes_read=len(raw),
            complete=True,
        )
