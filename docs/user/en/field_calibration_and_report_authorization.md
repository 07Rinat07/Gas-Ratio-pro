# Field Calibration and Final-Report Authorization

## Purpose

Stage 5.1 adds a second mandatory control layer above the numerical validation gate. A numerically reproducible method may enter a final engineering report only after its field-calibration contract and report policy have passed.

## Field-calibration dataset

v225.10 uses a **project-owned synthetic field-surrogate dataset**. It contains no third-party well data, is cleared for redistribution with the project, and acts as a reproducible acceptance dataset. Each method defines inputs, parameters, expected results, units, tolerances, and parameter distributions.

## Professional Print Center diagnostics

The read-only panel shows:

- numerical validation status;
- field-calibration status;
- report policy;
- RMSE and maximum error;
- uncertainty-envelope width;
- final-report authorization or block;
- validation, calibration, and authorization gate identifiers.

The panel is available in Russian, Kazakh, and English and does not modify source data or formulas.

## Export authorization

When a calculated DataFrame carries a machine-readable method context, final PDF/DOCX/HTML/bundle export is permitted only after `PetrophysicalReportAuthorizationApplicationService.assert_authorized()` succeeds.

The check runs **before PresentationModel construction and before any renderer starts**. A blocked method produces no file and the user receives the explicit denial reason.

## Foundation Dual Water limitation

`petrophysics.sw_dual_water_foundation` passes numerical and diagnostic calibration but retains the `blocked_final_report` policy. It must not be represented as a complete industrial Dual Water implementation in a final engineering report.

## Reproducible check

```bash
python scripts/run_petrophysical_stage_5_1_gate.py
```

Evidence is written to `artifacts/validation/` and contains contract fingerprints, calibration gate, authorization ID, and method-level decisions.
