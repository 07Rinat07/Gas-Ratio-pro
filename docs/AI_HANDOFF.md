# Latest implementation — Calibration Package Trust & Review Workflow v225.12

## Release state

- Build: `v225.12`.
- Channel: `stable`.
- Stage 5.3 implementation is complete.
- Production formulas are unchanged.
- The default trust registry is intentionally empty.
- Private keys are never accepted or persisted.
- Final verification: **2934 passed, 0 failed**; Live Workbench Acceptance **14/14**; Stage 5.3 gate passed.

## Architecture

- `core/calibration_package_trust_contract.py` owns trust schemas, canonical JSON, fingerprints, Ed25519 key/signature encoding, and verification.
- `services/calibration_package_trust_application_service.py` owns detached-signature import, immutable review chains, revocation, expiry, lineage, promotion, environment integrity, and trust decisions.
- `services/calibration_package_trust_diagnostics.py` supplies the ru/kk/en Print Center view model.
- `services/operator_calibration_package_application_service.py` requires production trust before strict activation and final project authorisation.
- `core/application_service_container.py` injects one project-scoped trust service into operator/export boundaries.
- `reports/export_controller.py`, `services/presentation_export_runtime_application_service.py`, and `reports/export_history.py` preserve trust evidence; Export History uses schema v6.
- `scripts/generate_calibration_signing_key.py` creates an Ed25519 key outside the project tree.
- `scripts/sign_operator_calibration_package.py` creates detached signature JSON.
- `scripts/run_petrophysical_stage_5_3_gate.py` produces machine-readable Stage 5.3 evidence.

## Trust policy

The immutable operator ZIP is not modified. A final report requires a valid detached signature, an active trusted public key scoped to the project and production environment, current technical and data-governance approvals, sequential development-to-validation-to-production promotion, unexpired rights/signature/key, no effective revocation, and matching immutable promotion evidence.

Foundation Dual Water remains `blocked_final_report`. Trust cannot override Stage 5 numerical validation, Stage 5.1 calibration/report policy, or Stage 5.2 data-rights/project authorisation.

## Security policy

Private keys are forbidden in the source tree, tests, documentation, evidence, project repository, and release ZIP. The shipped registry contains no trusted keys. Operator datasets remain project-private and are excluded from release archives. `.github/workflows` is excluded from the user archive.

## Next authorised stage

Stage 5.4 — Trust Registry Operations & External Identity Integration: controlled key rotation, authenticated reviewer identity, signed registry releases, audit-bundle export, scheduled expiry/revocation monitoring, and an optional KMS/HSM adapter boundary.

## README policy

Root README files contain only the current project overview, capabilities, quick start, documentation links, and a brief status. Detailed release history and test totals belong only in changelogs and release notes.
