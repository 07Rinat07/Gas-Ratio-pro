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

## Stable release v225.11

- completed Stage 5.2 Operator Dataset Import & Calibration Comparison;
- added project-scoped operator ZIP import with mandatory data-rights, project-scope, checksum, and method-registry fingerprint validation;
- the original ZIP, manifest, registry, and dataset are stored immutably with SHA-256 fingerprints;
- added baseline/operator and operator/operator comparisons across 10 methods;
- the active operator package participates in authorization before final export construction;
- export artifacts and history v5 persist the authorization package ID and operator calibration fingerprint;
- Professional Print Center now provides a trilingual import, activation, comparison, and diagnostics panel;
- production formulas are unchanged and foundation Dual Water remains `blocked_final_report`;
- private operator data is excluded from the user release archive;
- run the gate with `python scripts/run_petrophysical_stage_5_2_gate.py`;
- [user guide](docs/user/en/operator_calibration_packages.md) · [architecture](docs/developer/en/operator_calibration_package_architecture.md).

- Final v225.11 verification: **2915 passed, 0 failed**; Live Workbench Acceptance: **14/14**; import **1/1**; comparison **10/10**; project authorization **9/9**.

## Previous stable release v225.10

- completed Stage 5.1 Field Calibration & Report Authorization Integration;
- added a project-owned synthetic field-surrogate calibration dataset for 10 methods;
- calibration gate: **10/10**, final-report authorised: **9/10**;
- added RMSE/MAE/bias, sensitivity, and uncertainty envelopes;
- final export runs authorization before PresentationModel and renderer construction;
- Professional Print Center exposes read-only diagnostics in Russian, Kazakh, and English;
- foundation Dual Water remains `blocked_final_report`;
- run: `python scripts/run_petrophysical_stage_5_1_gate.py`;
- [user guide](docs/user/en/field_calibration_and_report_authorization.md) · [architecture](docs/developer/en/field_calibration_authorization_architecture.md).

- Final v225.10 verification: **2896 passed, 0 failed**; Live Workbench Acceptance: **14/14**; numerical validation: **10/10**; field calibration: **10/10**; final-report authorization: **9/10**.

## Previous stable release v225.9

- completed Stage 5 Petrophysical Engine Validation Foundation;
- registered 10 petrophysical methods with provenance, units, applicability, limitations, and report policy;
- added 10 synthetic reference cases, numerical tolerances, and uncertainty metadata;
- an application-service gate executes production functions and writes JSON evidence;
- 10/10 methods are numerically reproducible and 9 are eligible for final reports;
- foundation Dual Water remains `blocked_final_report`;
- run: `python scripts/run_petrophysical_validation_gate.py`;
- [user guide](docs/user/en/petrophysical_validation_gate.md) · [architecture](docs/developer/en/petrophysical_validation_architecture.md).
- A3 landscape plots and narrative sections now use the full printable frame;
- PDF/DOCX/HTML moved from fixed widths to the `available-frame` policy;
- [adaptive layout guide](docs/user/en/adaptive_report_layout.md) · [layout architecture](docs/developer/en/adaptive_report_layout_architecture.md).
- final v225.9 verification: **2881 passed, 0 failed**; Live Workbench: **14/14**; petrophysical gate: **10/10**.

## Previous stable release v225.8

- promoted Stage 4 to the **stable** channel;
- Live Workbench Acceptance verifies real server health and an executable Streamlit session;
- verified build/source identity and all five Workbench regions;
- the LAS command and LAS Workspace complete without a traceback;
- stable-promotion result: **14/14 passed**;
- full regression suite: **2858 passed, 0 failed**;
- run the gate with `.\run_app.ps1 -ForceRestart -Acceptance`;
- [user guide](docs/user/en/stable_release_and_acceptance.md) · [architecture](docs/developer/en/live_workbench_acceptance_architecture.md).

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
