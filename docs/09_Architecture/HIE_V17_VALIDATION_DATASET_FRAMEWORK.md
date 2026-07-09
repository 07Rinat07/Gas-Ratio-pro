# HIE v17 — Validation Dataset Framework

## Status

Implemented and tested.

## Objective

Protect Hydrocarbon Interpretation Engine from silent regressions before v1.0 freeze.

## Implemented

- Built-in reference scenarios for gas, oil, gas-condensate, Claystone barriers, uncertain/noisy intervals and missing-curve cases.
- Public validation catalog API for documentation and QA views.
- Public suite runner for automated regression checks.
- Additional rule `HC-NO-NUMERIC-DATA-001` for intervals without numeric gas-ratio evidence.

## Engineering decision

The validation dataset is not a replacement for field validation. It is a software safety layer that confirms agreed engine behavior remains stable while reports, visualization, UI and petrophysics are developed.

## Next step

HIE v18 — Architecture Audit and v1.0 freeze preparation.
