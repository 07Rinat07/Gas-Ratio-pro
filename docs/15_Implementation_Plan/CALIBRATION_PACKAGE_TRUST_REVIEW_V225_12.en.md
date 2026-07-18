# v225.12 implementation plan — Calibration Package Trust & Review Workflow

Status: **COMPLETED / Stable v225.12**.

## Goals

1. Bind an immutable operator package to a detached Ed25519 signature without exposing the private key to the application.
2. Verify signatures through an application-scoped trust registry with project/environment scope and validity periods.
3. Store reviewer decisions, revocations, lineage, and promotion records separately from the source ZIP.
4. Permit only sequential `development → validation → production` promotion.
5. Block activation and final export when trust evidence is incomplete, revoked, or expired.
6. Preserve trust fingerprints in the project authorization package, export artifact, and Export History v6.
7. Leave production formulas and Stage 5/5.1/5.2 contracts unchanged.

## Implementation

- canonical trust schemas and fingerprints;
- detached Ed25519 signature verification;
- intentionally empty default trust registry and an administrative public-key contract;
- immutable review chain using `previous_decision_fingerprint`;
- package/key/signature revocation;
- rights/signature/key expiry monitoring;
- signed package lineage with cycle/self-reference protection;
- environment state bound to immutable promotion evidence;
- production trust gate before `PresentationModel` and renderer construction;
- export-cache isolation by trust context;
- Export History schema v6;
- trilingual Professional Print Center diagnostics and workflow;
- CLI tools for key generation, detached signing, and Stage 5.3 evidence.

## Definition of Done

- cryptographic, review, revocation, expiry, lineage, and promotion tests pass;
- manual environment-state modification cannot grant production trust;
- no private key exists in source, tests, documentation, evidence, or release ZIP files;
- activation/export remains blocked until production promotion;
- Foundation Dual Water remains `blocked_final_report`;
- Live Workbench Acceptance passes for `ru/kk/en`;
- the full regression suite has zero failures;
- ru/kk/en documentation is synchronised;
- `.github/workflows` is absent from the user archive.
