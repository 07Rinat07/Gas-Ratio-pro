# v225.12 Acceptance — Calibration Package Trust & Review Workflow

Acceptance passes when:

- a detached Ed25519 signature verifies against the exact `package_fingerprint`;
- a tampered envelope or wrong project scope is rejected;
- a key must be active, carry the signing purpose, match project/environment scope, and remain within its validity period;
- validation requires a current `technical_reviewer` approval;
- production requires current `technical_reviewer` and `data_governance_reviewer` approvals;
- a current rejection blocks promotion;
- only `development → validation → production` transitions are permitted;
- environment state without matching immutable promotion evidence cannot grant trust;
- package, key, or signature revocation blocks subsequent authorisation;
- expired rights, signature, or key blocks the final report;
- the lineage parent exists in the same project and cycles/self-reference are rejected;
- activation and final export evaluate production trust before the renderer;
- ExportArtifact and Export History v6 preserve trust evidence;
- private keys are never persisted by the application and are absent from the release ZIP;
- `python scripts/run_petrophysical_stage_5_3_gate.py` produces passed evidence;
- production formulas remain unchanged;
- Live Workbench and the full regression suite pass without failures.

## Actual result

- Stage 5.3 gate: signature **1/1**, reviewer approvals **2/2**, promotion transitions **2/2**, production trust **passed**, private keys persisted **0**;
- Live Workbench Acceptance: **14/14**;
- full regression suite: **2934 passed, 0 failed**.
