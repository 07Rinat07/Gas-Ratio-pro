"""Optional SEG-Y trace-header inventory isolated behind lazy segyio imports."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .metadata_scanner import MetadataScanResult


class SegyTraceHeaderInventoryAdapter:
    """Inspect selected trace-header fields without materializing trace samples.

    Byte locations are 1-based SEG-Y trace-header byte positions. The adapter
    uses segyio lazily and returns a stable diagnostic result when unavailable.
    Coordinate scalar and X/Y fields are optional but enabled by default using
    the conventional bytes 71, 73 and 77.
    """

    format_id = "segy"

    def __init__(
        self,
        *,
        inline_byte: int = 189,
        crossline_byte: int = 193,
        coordinate_scalar_byte: int = 71,
        x_byte: int = 73,
        y_byte: int = 77,
        max_traces: int = 100_000,
    ) -> None:
        for name, value in (
            ("inline_byte", inline_byte),
            ("crossline_byte", crossline_byte),
            ("coordinate_scalar_byte", coordinate_scalar_byte),
            ("x_byte", x_byte),
            ("y_byte", y_byte),
        ):
            if not 1 <= int(value) <= 237:
                raise ValueError(f"{name} must be a valid 4-byte trace-header start position")
        self.inline_byte = int(inline_byte)
        self.crossline_byte = int(crossline_byte)
        self.coordinate_scalar_byte = int(coordinate_scalar_byte)
        self.x_byte = int(x_byte)
        self.y_byte = int(y_byte)
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
                    "coordinate_scalar_header_byte": self.coordinate_scalar_byte,
                    "x_header_byte": self.x_byte,
                    "y_header_byte": self.y_byte,
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
            scalar_values = self._read_attribute(handle, self.coordinate_scalar_byte, inspected)
            x_raw = self._read_attribute(handle, self.x_byte, inspected)
            y_raw = self._read_attribute(handle, self.y_byte, inspected)
            x_values, y_values, valid_coordinate_count = self._scaled_coordinates(
                x_raw, y_raw, scalar_values
            )
            if trace_count > inspected:
                warnings.append("segy.trace_inventory.truncated")
            if inspected and valid_coordinate_count == 0:
                warnings.append("segy.geometry.coordinates_unavailable")
            confidence = self._geometry_confidence(
                inspected=inspected,
                valid_coordinate_count=valid_coordinate_count,
                inline_values=inline_values,
                crossline_values=crossline_values,
            )
            if confidence == "low":
                warnings.append("segy.geometry.low_confidence")
            metadata: dict[str, Any] = {
                "optional_adapter": "segyio",
                "adapter_available": True,
                "trace_count": trace_count,
                "trace_headers_inspected": inspected,
                "sample_count": sample_count,
                "inline_header_byte": self.inline_byte,
                "crossline_header_byte": self.crossline_byte,
                "coordinate_scalar_header_byte": self.coordinate_scalar_byte,
                "x_header_byte": self.x_byte,
                "y_header_byte": self.y_byte,
                "inline_min": min(inline_values) if inline_values else None,
                "inline_max": max(inline_values) if inline_values else None,
                "inline_unique_count": len(set(inline_values)),
                "crossline_min": min(crossline_values) if crossline_values else None,
                "crossline_max": max(crossline_values) if crossline_values else None,
                "crossline_unique_count": len(set(crossline_values)),
                "coordinate_scalar_unique_count": len(set(scalar_values)),
                "coordinate_valid_count": valid_coordinate_count,
                "coordinate_valid_fraction": round(valid_coordinate_count / inspected, 6) if inspected else 0.0,
                "x_min": min(x_values) if x_values else None,
                "x_max": max(x_values) if x_values else None,
                "y_min": min(y_values) if y_values else None,
                "y_max": max(y_values) if y_values else None,
                "geometry_confidence": confidence,
            }
        return MetadataScanResult(
            format_id=self.format_id,
            metadata=metadata,
            warnings=tuple(dict.fromkeys(warnings)),
            bytes_read=0,
            complete=True,
        )

    @staticmethod
    def _read_attribute(handle: Any, byte_position: int, count: int) -> list[int]:
        values = handle.attributes(byte_position)
        return [int(values[index]) for index in range(count)]

    @staticmethod
    def _apply_scalar(value: int, scalar: int) -> float:
        if scalar > 0:
            return float(value * scalar)
        if scalar < 0:
            return float(value) / abs(scalar)
        return float(value)

    @classmethod
    def _scaled_coordinates(
        cls, x_values: list[int], y_values: list[int], scalar_values: list[int]
    ) -> tuple[list[float], list[float], int]:
        scaled_x: list[float] = []
        scaled_y: list[float] = []
        valid = 0
        for x_value, y_value, scalar in zip(x_values, y_values, scalar_values):
            x = cls._apply_scalar(x_value, scalar)
            y = cls._apply_scalar(y_value, scalar)
            if x == 0.0 and y == 0.0:
                continue
            scaled_x.append(x)
            scaled_y.append(y)
            valid += 1
        return scaled_x, scaled_y, valid

    @staticmethod
    def _geometry_confidence(
        *,
        inspected: int,
        valid_coordinate_count: int,
        inline_values: list[int],
        crossline_values: list[int],
    ) -> str:
        if inspected <= 0:
            return "none"
        coordinate_fraction = valid_coordinate_count / inspected
        has_grid_variation = len(set(inline_values)) > 1 or len(set(crossline_values)) > 1
        if coordinate_fraction >= 0.95 and has_grid_variation:
            return "high"
        if coordinate_fraction >= 0.5 and (has_grid_variation or valid_coordinate_count > 1):
            return "medium"
        return "low"
