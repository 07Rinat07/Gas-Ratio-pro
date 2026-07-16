"""Optional DLIS/LIS79 metadata scanners isolated behind lazy dlisio imports."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .metadata_scanner import MetadataScanResult


class DlisLisMetadataScanner:
    """Inspect logical-file metadata without materializing curve arrays.

    When dlisio is not installed, the scanner returns a stable diagnostic result
    rather than failing application startup or importing a heavy dependency.
    """

    def __init__(self, format_id: str, *, probe_bytes: int = 4096) -> None:
        normalized = str(format_id).strip().lower()
        if normalized not in {"dlis", "lis79"}:
            raise ValueError("format_id must be dlis or lis79")
        self.format_id = normalized
        self.probe_bytes = max(512, min(int(probe_bytes), 65536))

    def scan(self, source: Path | str) -> MetadataScanResult:
        path = Path(source)
        try:
            from dlisio import dlis, lis  # type: ignore
        except ImportError:
            with path.open("rb") as handle:
                probe = handle.read(self.probe_bytes)
            return MetadataScanResult(
                format_id=self.format_id,
                metadata={
                    "file_size_bytes": path.stat().st_size,
                    "optional_adapter": "dlisio",
                    "adapter_available": False,
                    "probe_contains_tif_marker": b"TIF" in probe.upper(),
                },
                warnings=(f"{self.format_id}.adapter.dlisio_unavailable",),
                bytes_read=len(probe),
                complete=False,
            )

        loader = dlis.load if self.format_id == "dlis" else lis.load
        logical_files: list[Any] = []
        with loader(str(path)) as loaded:
            logical_files = list(loaded)
            metadata = {
                "file_size_bytes": path.stat().st_size,
                "optional_adapter": "dlisio",
                "adapter_available": True,
                "logical_file_count": len(logical_files),
            }
            if self.format_id == "dlis":
                frame_count = sum(len(getattr(item, "frames", ()) or ()) for item in logical_files)
                channel_count = sum(len(getattr(item, "channels", ()) or ()) for item in logical_files)
                metadata.update({"frame_count": frame_count, "channel_count": channel_count})
            else:
                metadata["logical_record_metadata_available"] = True
        return MetadataScanResult(
            format_id=self.format_id,
            metadata=metadata,
            warnings=(),
            bytes_read=0,
            complete=True,
        )
