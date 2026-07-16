"""Allow-listed registry of industry data format capabilities."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True, slots=True)
class DataFormatCapability:
    format_id: str
    display_name: str
    extensions: tuple[str, ...]
    media_types: tuple[str, ...] = ()
    supports_import: bool = True
    supports_export: bool = False
    supports_metadata_scan: bool = False
    supports_streaming: bool = False
    supports_preview: bool = False
    category: str = "generic"

    def __post_init__(self) -> None:
        format_id = self.format_id.strip().lower()
        if not format_id or not format_id.replace("-", "").replace("_", "").isalnum():
            raise ValueError("format_id must be a non-empty stable identifier")
        normalized = tuple(_normalize_extension(item) for item in self.extensions)
        if not normalized:
            raise ValueError("at least one extension is required")
        if len(set(normalized)) != len(normalized):
            raise ValueError("duplicate extensions are not allowed")
        object.__setattr__(self, "format_id", format_id)
        object.__setattr__(self, "extensions", normalized)

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["extensions"] = list(self.extensions)
        payload["media_types"] = list(self.media_types)
        return payload


def _normalize_extension(value: object) -> str:
    extension = str(value).strip().lower()
    if not extension:
        raise ValueError("extension must not be empty")
    if not extension.startswith("."):
        extension = f".{extension}"
    if any(token in extension for token in ("/", "\\", "..")):
        raise ValueError("extension must not contain path components")
    return extension


class DataFormatRegistry:
    """Deterministic registry with collision checks for ids and extensions."""

    def __init__(self, capabilities: Iterable[DataFormatCapability] = ()) -> None:
        self._by_id: dict[str, DataFormatCapability] = {}
        self._by_extension: dict[str, DataFormatCapability] = {}
        for capability in capabilities:
            self.register(capability)

    def register(self, capability: DataFormatCapability) -> None:
        if capability.format_id in self._by_id:
            raise ValueError(f"format already registered: {capability.format_id}")
        collisions = [ext for ext in capability.extensions if ext in self._by_extension]
        if collisions:
            raise ValueError(f"extension already registered: {collisions[0]}")
        self._by_id[capability.format_id] = capability
        for extension in capability.extensions:
            self._by_extension[extension] = capability

    def get(self, format_id: object) -> DataFormatCapability | None:
        return self._by_id.get(str(format_id).strip().lower())

    def require(self, format_id: object) -> DataFormatCapability:
        capability = self.get(format_id)
        if capability is None:
            raise KeyError(f"unknown data format: {format_id}")
        return capability

    def detect(self, path: Path | str) -> DataFormatCapability | None:
        return self._by_extension.get(Path(path).suffix.lower())

    def list(self) -> tuple[DataFormatCapability, ...]:
        return tuple(self._by_id[key] for key in sorted(self._by_id))

    def snapshot(self) -> dict[str, object]:
        return {
            "format_count": len(self._by_id),
            "formats": [item.to_dict() for item in self.list()],
        }


def default_format_registry() -> DataFormatRegistry:
    """Return lightweight contracts only; parser dependencies stay optional."""
    return DataFormatRegistry(
        (
            DataFormatCapability("las", "LAS", (".las",), supports_export=True, supports_metadata_scan=True, supports_preview=True, category="well-log"),
            DataFormatCapability("dlis", "DLIS", (".dlis",), supports_metadata_scan=True, supports_streaming=True, supports_preview=True, category="well-log"),
            DataFormatCapability("segy", "SEG-Y", (".sgy", ".segy"), supports_metadata_scan=True, supports_streaming=True, supports_preview=True, category="seismic"),
            DataFormatCapability("resqml", "RESQML", (".epc",), supports_export=True, supports_metadata_scan=True, supports_streaming=True, category="subsurface-model"),
            DataFormatCapability("grdecl", "GRDECL", (".grdecl",), supports_export=True, supports_metadata_scan=True, category="simulation"),
            DataFormatCapability("geotiff", "GeoTIFF", (".tif", ".tiff"), supports_export=True, supports_metadata_scan=True, supports_streaming=True, supports_preview=True, category="gis"),
            DataFormatCapability("shapefile", "ESRI Shapefile", (".shp",), supports_export=True, supports_metadata_scan=True, category="gis"),
            DataFormatCapability("geopackage", "GeoPackage", (".gpkg",), supports_export=True, supports_metadata_scan=True, supports_streaming=True, category="gis"),
            DataFormatCapability("hdf5", "HDF5", (".h5", ".hdf5"), supports_export=True, supports_metadata_scan=True, supports_streaming=True, category="scientific"),
            DataFormatCapability("netcdf", "NetCDF", (".nc", ".netcdf"), supports_export=True, supports_metadata_scan=True, supports_streaming=True, category="scientific"),
            DataFormatCapability("csv", "CSV", (".csv",), supports_export=True, supports_metadata_scan=True, supports_preview=True, category="tabular"),
            DataFormatCapability("excel", "Excel", (".xlsx", ".xlsm"), supports_export=True, supports_metadata_scan=True, supports_preview=True, category="tabular"),
            DataFormatCapability("pdf", "PDF", (".pdf",), supports_import=False, supports_export=True, category="report"),
            DataFormatCapability("docx", "DOCX", (".docx",), supports_import=False, supports_export=True, category="report"),
        )
    )
