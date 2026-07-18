# Current status — v225.12 Stable

Updated: 18 July 2026.

## Active stage

**Stage 5.3 — Calibration Package Trust & Review Workflow is complete and verified as Stable v225.12.** Production formulas are unchanged.

## Trust boundary

- the Stage 5.2 source operator ZIP remains byte-for-byte immutable;
- a detached Ed25519 signature binds the exact `package_fingerprint`, project ID, key ID, signer identity, validity, and lineage;
- the default trust registry is intentionally empty and accepts only approved public-key records;
- application services never accept or persist private keys.

## Review, revocation, and expiry

- validation requires a current `technical_reviewer` approval;
- production requires current `technical_reviewer` and `data_governance_reviewer` approvals;
- review history is immutable and linked through `previous_decision_fingerprint`;
- package, key, and signature revocation are supported;
- data-rights, signature, and key expiry are checked before final reporting.

## Controlled promotion and lineage

- only `development → validation → production` is permitted;
- environment state is validated against immutable promotion evidence;
- manually editing state cannot grant production trust;
- lineage supports `root`, `supersedes`, `derived_from`, and `recalibrated_from`;
- the parent must exist in the same project; cycles, self-reference, and conflicting parents are rejected.

## Export authorisation

- strict production trust is evaluated before activation, `PresentationModel`, and renderer construction;
- the trust decision, registry/signature fingerprints, and promotion ID enter the project authorisation package;
- ExportArtifact and Export History schema v6 retain trust evidence;
- changing trust context clears the project export cache;
- Foundation Dual Water remains `blocked_final_report`.

## Evidence

- `artifacts/validation/calibration_package_trust_v225_12.json`;
- Stage 5.3 gate: signature **1/1**, reviewer approvals **2/2**, promotion transitions **2/2**, production trust **passed**, private keys persisted **0**;
- Live Workbench Acceptance: **14/14** for `ru/kk/en`;
- full regression suite: **2934 passed, 0 failed**; release verification is complete.

## Stable contracts

Stable Workbench, full-frame A3 landscape layout, architecture boundaries, controlled visual baselines, numerical validation, field calibration, operator rights, immutable package storage, and pre-render authorisation remain mandatory.

Reservoir Intelligence / Interpretation 2.0, Pixler rehabilitation, Ternary rehabilitation, and Depth engineering panel remain frozen without explicit validation evidence.

## Stabilization & Release Audit

The trust workflow cannot bypass Stage 5/5.1/5.2 gates. Private keys and private operator datasets are not distributed. `.github/workflows` remains excluded from the user archive.

## Next stage

**Stage 5.4 — Trust Registry Operations & External Identity Integration.** The next authorised boundary covers controlled key rotation, an authenticated reviewer-identity adapter, audit-bundle export, registry administration, and an optional external KMS/HSM adapter without changing production formulas.
