# v225.10 — Field Calibration, Sensitivity & Report Authorization

## Goal

Add field-calibration evidence and blocking final-report authorization without changing production formulas.

## Completed

1. created a project-owned synthetic field-surrogate dataset for 10 methods;
2. recorded ownership/legal clearance, units, and acceptance thresholds;
3. calculated RMSE, MAE, bias, and maximum error;
4. added parameter sensitivity and uncertainty envelopes;
5. combined numerical validation and calibration with report policy;
6. propagated method context from calculations into export;
7. executed authorization before model/renderer construction;
8. exposed read-only diagnostics in Professional Print Center for ru/kk/en;
9. persisted authorization evidence in artifacts and export history;
10. kept foundation Dual Water blocked from final reports.

Final v225.10 verification: **2896 passed, 0 failed**; Live Workbench Acceptance: **14/14**; numerical validation: **10/10**; field calibration: **10/10**; final-report authorization: **9/10**.
