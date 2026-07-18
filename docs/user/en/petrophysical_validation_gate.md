# Petrophysical validation gate

In v225.9, petrophysical calculations are validated before use in a final engineering report. The gate does not change formulas: it executes the current production functions on synthetic references and compares the outputs with approved values.

## Run

```bash
python scripts/run_petrophysical_validation_gate.py
```

## Rules

- All 10 registered methods must pass numerical validation.
- Input and output units must match the registry contract.
- Every method must define provenance, applicability, limitations, tolerance, and uncertainty metadata.
- A method with `blocked_final_report` may pass numerical validation but remains prohibited in a final report.

## Dual Water foundation

`petrophysics.sw_dual_water_foundation` remains a transparent comparison approximation. It is not the complete Clavier–Coates–Dumanoir model and is blocked for final reports.

## Evidence

Evidence is written to `artifacts/validation/petrophysical_validation_v225_9.json`.
