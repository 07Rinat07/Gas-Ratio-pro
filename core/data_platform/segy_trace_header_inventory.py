"""Optional SEG-Y trace-header inventory isolated behind lazy segyio imports."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .metadata_scanner import MetadataScanResult


class SegyTraceHeaderInventoryAdapter:
    """Inspect selected trace-header fields without materializing trace samples.

    Byte locations are 1-based SEG-Y trace-header byte positions. The adapter
    uses segyio lazily and returns a stable diagnostic result when unavailable.
    """

    format_id = "segy"

    def __init__(self, *, inline_byte: int = 189, crossline_byte: int = 193, max_traces: int = 100_000) -> None:
        for name, value in (("inline_byte", inline_byte), ("crossline_byte", crossline_byte)):
            if not 1 <= int(value) <= 237:
                raise ValueError(f"{name} must be a valid 4-byte trace-header start position")
        self.inline_byte = int(inline_byte)
        self.crossline_byte = int(crossline_byte)
        self.max_traces = max(1, min(int(max_traces), 1_000_000))

    def scan(self, source: Path | str) -> MetadataScanResult:
        path = Path(source)
        try:
            import segyio  # type: ignore
        except ImportError:
            return MetadataScanResult(
                format_id=self.format_id,
                metadata={
                    "optional_adapter": "segyio",
                    "adapter_available": False,
                    "inline_header_byte": self.inline_byte,
                    "crossline_header_byte": self.crossline_byte,
                    "file_size_bytes": path.stat().st_size,
                },
                warnings=("segy.adapter.segyio_unavailable",),
                bytes_read=0,
                complete=False,
            )

        warnings: list[str] = []
        with segyio.open(str(path), "r", strict=False, ignore_geometry=True) as handle:
            trace_count = int(getattr(handle, "tracecount", 0) or 0)
            sample_count = len(getattr(handle, "samples", ()) or ())
            inspected = min(trace_count, self.max_traces)
            inline_values = self._read_attribute(handle, self.inline_byte, inspected)
            crossline_values = self._read_attribute(handle, self.crossline_byte, inspected)
            if trace_count > inspected:
                warnings.append("segy.trace_inventory.truncated")
            metadata: dict[str, Any] = {
                "optional_adapter": "segyio",
                "adapter_available": True,
                "trace_count": trace_count,
                "trace_headers_inspected": inspected,
                "sample_count": sample_count,
                "inline_header_byte": self.inline_byte,
                "crossline_header_byte": self.crossline_byte,
                "inline_min": min(inline_values) if inline_values else None,
                "inline_max": max(inline_values) if inline_values else None,
                "inline_unique_count": len(set(inline_values)),
                "crossline_min": min(crossline_values) if crossline_values else None,
                "crossline_max": max(crossline_values) if crossline_values else None,
                "crossline_unique_count": len(set(crossline_values)),
            }
        return MetadataScanResult(
            format_id=self.format_id,
            metadata=metadata,
            warnings=tuple(warnings),
            bytes_read=0,
            complete=True,
        )

    @staticmethod
    def _read_attribute(handle: Any, byte_position: int, count: int) -> list[int]:
        values = handle.attributes(byte_position)
        return [int(values[index]) for index in range(count)]
