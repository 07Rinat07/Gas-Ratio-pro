# Latest implementation — Operator Dataset Import & Calibration Comparison v225.11

## Release state

- Build: `v225.11`.
- Channel: `stable`.
- Stage 5.2 implementation is complete.
- Operator package import: **1/1 passed**.
- Calibration comparison: **10/10 methods compared**.
- Project final-report authorization: **9/9 eligible methods authorised**.
- Foundation Dual Water: `blocked_final_report`.
- Full regression: **2915 passed, 0 failed**.
- Live Workbench Acceptance: **14/14 passed**.

## Architecture

- `core/operator_calibration_package_contract.py` defines the immutable three-file ZIP contract, rights policy, scope, checksum, and fingerprint rules.
- `services/operator_calibration_package_application_service.py` owns import, immutable project storage, activation, comparison, tamper detection, and versioned project authorization packages.
- `services/operator_calibration_diagnostics.py` supplies the ru/kk/en read-only Print Center model.
- `core/application_service_container.py` constructs the project-scoped service and injects it into export runtime.
- `services/presentation_export_runtime_application_service.py` authorises the active operator package before model/renderer construction and invalidates cached export state when the package changes.
- `reports/export_controller.py` and `reports/export_history.py` persist authorization package IDs and operator calibration fingerprints.
- `scripts/build_operator_calibration_package.py` builds a documented operator ZIP package.
- `scripts/run_petrophysical_stage_5_2_gate.py` writes machine-readable Stage 5.2 evidence.

## Package contract

Every accepted ZIP contains exactly:

```text
manifest.json
calibration_registry.json
calibration_dataset.json
```

The manifest declares project scope, operator identity, legal basis, data classification, processing/derivative/final-report/redistribution rights, expiration, payload checksums and sizes, method-registry fingerprint, and an explicit prohibition on formula changes. The original ZIP and all payloads are stored byte-for-byte under the project repository. Stored content is revalidated before every use.

## Critical policy

Production formulas are unchanged. Operator packages may calibrate and authorise methods but cannot modify the calculation contract. Private operator data must never be placed in documentation, tests, examples, evidence committed for distribution, or user release archives. Foundation Dual Water remains blocked for final engineering reports.

## Next authorised stage

Stage 5.3 — Calibration Package Trust & Review Workflow: digital signatures, reviewer approval, revocation, expiry monitoring, package lineage, and controlled promotion between project environments.

## Release governance

Always update and verify Russian, Kazakh, and English README, user instructions, developer architecture, status, roadmap, project plan, changelog, release notes, and documentation manifest. User archives exclude `.github/workflows` unless local runtime explicitly requires it.
