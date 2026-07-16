# Import Pipeline Architecture

`ImportWizardState` is an immutable JSON-safe contract. Valid stages are `select`, `preview`, `configure`, `validate`, `register`, and `complete`.

`run_batch_import()` isolates exceptions per file. Each item is represented by `BatchImportItemResult`.

Quick QC operates only on `MetadataScanResult`. Providers must not load complete curve arrays or seismic trace samples.

Readiness is persisted in Dataset Manifest metadata as `readiness_score`, `readiness_status`, and `quick_qc_status`.
