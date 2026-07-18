# GAS RATIO PRO

A professional trilingual engineering platform for importing, quality-controlling, versioning, analysing, interpreting, and visualising well, subsurface, geophysical, and project data for the oil-and-gas industry.

**Language:** [Русский](README.ru.md) · [Қазақша](README.kk.md) · English

## Documentation

- [User guide](docs/user/en/index.md)
- [Developer documentation](docs/developer/en/index.md)
- [Supported formats](docs/user/en/supported_formats_and_legal_sources.md)
- [Project plan](docs/project/PROJECT_PLAN.en.md)
- [Current status](docs/PROJECT_STATUS.en.md)

## Supported and planned formats

- **LAS 1.x/2.x/3.x** — import, legacy compatibility, editing, QC, versioning, visualisation, and export;
- **Excel/CSV** — import, mapping, calculations, and visualisation;
- **DLIS/LIS79** — metadata preview through the optional `dlisio` adapter;
- **SEG-Y** — header preview, trace-header inventory, and geometry diagnostics;
- **PDF/DOCX** — engineering and QC reports;
- **GeoPackage/Shapefile/GeoTIFF, GRDECL/RESQML, HDF5/NetCDF** — planned Data/GIS/Reservoir Platform stages.

## Main subsystems

- Workbench and Project Explorer;
- Unified Import Pipeline, import profiles, and readiness scores;
- Data Platform with immutable artifacts, Dataset Manifest, SHA-256, provenance, and lineage;
- LAS QC Platform and localised PDF/DOCX reporting;
- gas-geochemistry calculations and interval interpretation;
- well correlation and preparation for multi-well log panels;
- Russian, Kazakh, and English interface and documentation.

## Print and export validation v225.6

- approved golden artifacts now cover every A4/A3 portrait/landscape profile;
- the manifest freezes every SVG/PNG page, multi-page PDF, track partition, physical bounds, and checksum;
- an end-to-end acceptance test runs from persisted user-profile selection through HTML/PDF/DOCX and SVG/PNG delivery;
- PDF preview images now scale to the actual report frame when page and report orientations differ;
- all 51 inherited legacy regression contracts are classified without silent `xfail`;
- [user guide](docs/user/en/print_center_page_aware.md);
- [developer architecture](docs/developer/en/page_aware_print_architecture.md).

## Installation and launch

Python 3.10+ is required.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
.\run_app.ps1
```

## Author

**Sarmuldin R. R.** — software engineer and author of GAS RATIO PRO.
