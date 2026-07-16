# Open Standards & Interoperability Policy

Status: mandatory project policy

GAS RATIO PRO is developed as an interoperable geological and petroleum-engineering platform. New capabilities must prefer published exchange standards and documented adapter boundaries over proprietary internal project formats.

## Required principles

1. Official specifications and standards are the primary technical source.
2. External formats are integrated through adapters, Format Registry capabilities, Metadata Scanner protocols, Dataset Manifests and QC contracts.
3. Heavy parser/renderer dependencies are loaded lazily and remain outside the domain core.
4. Imported source bytes are preserved as immutable artifacts before normalization or conversion.
5. Legacy industrial data, including LAS earlier than 2.0, must be handled through explicit compatibility modes and stable diagnostics.
6. Proprietary vendor project files are not reverse-engineered or copied. Integration uses documented SDKs, licensed APIs or open exchange formats.
7. Every external dependency or adapted code fragment must have a recorded origin, version, license and review decision.
8. User-facing instructions and relevant technical documentation are maintained in Russian, Kazakh and English.

## Target standards and formats

- LAS 1.x, 2.x and 3.x;
- DLIS and LIS79;
- SEG-Y;
- RESQML and legacy RESCUE where legally and technically justified;
- GRDECL and simulator-specific documented profiles;
- GeoPackage, Shapefile and GeoTIFF;
- HDF5 and NetCDF;
- CSV, Excel, PDF and DOCX.

## Integration acceptance gate

A format adapter is not complete until it has: capability registration, metadata-only scan, immutable artifact registration, validation/QC, bounded-memory behavior, security tests, provenance, three-language user guidance and license/source evidence.
