# Operator calibration package architecture — revision 1

## Stage 5.2 boundary

Stage 5.2 adds data and evidence but does not change production formulas. Methods continue to execute only through `core.petrophysical_method_executor` and the numerical validation gate.


The machine-readable package schema is `gas-ratio-pro/operator-calibration-package/v1`.

## Layers

```text
Professional Print Center
        ↓
OperatorCalibrationPackageApplicationService
        ├── ZIP/data-rights/fingerprint validation
        ├── immutable project repository
        ├── PetrophysicalCalibrationApplicationService
        ├── calibration comparison
        └── project authorization package
        ↓
PresentationExportRuntimeApplicationService
        ↓
ExportController / renderer
```

The UI never reads or writes the package repository directly.

## Format and fingerprints

`package_fingerprint` is the SHA-256 of the canonical manifest with the fingerprint field removed. The manifest carries exact registry/dataset SHA-256 values and sizes. A separate `rights_fingerprint` ensures a permission change also changes the authorization context.

Stored members are revalidated whenever the package is used. A `package_id + version` pair is immutable; another fingerprint is a version conflict.

## Repository

```text
data/projects/<project>/petrophysics/operator_calibration/
  package_index.json
  active_package.json
  packages/<package_id>/<version>/<fingerprint>/...
  comparisons/<comparison_id>.json
  authorizations/<package_id>/<version>/<authorization_package_id>.json
```

Private operator packages are never copied into user release archives.

## Data-rights gate

Import requires project scope, legal basis, processing permission, and derivative-analysis permission. `final_report_use_allowed` is enforced separately immediately before final export. Expiration is checked both on import and on later use.

## Comparison

Comparison aggregates multiple cases for the same method ID and compares RMSE, MAE, bias, maximum error, and uncertainty width. The deterministic `comparison_id` identifies evidence; comparison never tunes or replaces formulas.

## Project authorization package

Each final export can produce a deterministic package containing project ID, method IDs, validation and baseline/operator calibration gate IDs, comparison ID, source package/version/fingerprint, rights fingerprint, and per-method decisions.

Methods covered by the active operator package use its calibration and rights. Other methods use the approved project baseline. `blocked_final_report` remains blocking.

## Cache isolation

The runtime tracks authorization ID, authorization package ID, operator fingerprint, and rights fingerprint. A context change clears project model/artifact caches before rendering.

## ZIP security

Only three root members are allowed. Total/member sizes are bounded, directories and absolute paths are rejected, and path traversal is prohibited. Checksums are verified before production methods execute.
