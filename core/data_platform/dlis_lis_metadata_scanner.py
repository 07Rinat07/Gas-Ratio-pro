"""Optional DLIS/LIS79 metadata scanners isolated behind lazy dlisio imports."""
from __future__ import annotations

from pathlib import Path
from typing import Any
import json

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
            summaries: list[dict[str, object]] = []
            if self.format_id == "dlis":
                frame_count = 0
                channel_count = 0
                for index, item in enumerate(logical_files):
                    frames = tuple(getattr(item, "frames", ()) or ())
                    channels = tuple(getattr(item, "channels", ()) or ())
                    frame_count += len(frames)
                    channel_count += len(channels)
                    summaries.append({
                        "index": index,
                        "frame_count": len(frames),
                        "channel_count": len(channels),
                        "frame_names": [str(getattr(frame, "name", "")) for frame in frames[:50]],
                        "channel_names": [str(getattr(channel, "name", "")) for channel in channels[:100]],
                    })
                metadata.update({
                    "frame_count": frame_count,
                    "channel_count": channel_count,
                    "logical_files_json": json.dumps(summaries, ensure_ascii=False, separators=(",", ":")),
                })
            else:
                for index, item in enumerate(logical_files):
                    summaries.append({
                        "index": index,
                        "metadata_record_count": len(tuple(getattr(item, "metadata", ()) or ())),
                    })
                metadata["logical_record_metadata_available"] = True
                metadata["logical_files_json"] = json.dumps(summaries, ensure_ascii=False, separators=(",", ":"))
        return MetadataScanResult(
            format_id=self.format_id,
            metadata=metadata,
            warnings=(),
            bytes_read=0,
            complete=True,
        )
