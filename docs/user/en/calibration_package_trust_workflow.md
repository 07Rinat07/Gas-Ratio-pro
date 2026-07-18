# Operator calibration package trust and review

Revision 1 · Gas Ratio Pro v225.12

## Purpose

Stage 5.3 adds a controlled trust workflow for operator calibration packages. The Stage 5.2 source ZIP remains immutable. Signatures, reviewer decisions, revocations, expiry state, lineage, and environment promotions are stored separately.

## Requirements before activation

A package can be activated for a final report only when all conditions pass:

1. The ZIP passed the Stage 5.2 data-rights and calibration gates.
2. A detached Ed25519 signature exists for the exact `package_fingerprint`.
3. The public key is active in the approved trust registry and is allowed for the project and target environment.
4. A technical reviewer approved the numerical evidence and lineage.
5. A data-governance reviewer approved rights and production use.
6. The package was promoted in order: `development → validation → production`.
7. The package, signature, and key are not revoked.
8. Data rights, signature, and key are not expired.

## Professional Print Center workflow

The operator-calibration section provides:

- operator ZIP import;
- detached-signature JSON import;
- reviewer identity, role, decision, and rationale capture;
- controlled promotion to the next environment;
- package revocation with a mandatory reason;
- environment, signature, review, and trust diagnostics;
- expiry warnings for rights, signatures, and keys.

Activation remains blocked until a production trust decision passes.

## Detached signature

Create the signature outside the application with the operator's private Ed25519 key:

```powershell
python scripts/sign_operator_calibration_package.py `
  --package operator-calibration.zip `
  --private-key D:\secure\operator-signing-key.pem `
  --output operator-calibration.signature.json `
  --key-id operator-key-2026 `
  --project-id PROJECT-001 `
  --signer-id signer-001 `
  --signer-name "Responsible signer" `
  --organization-id OPERATOR-ORG
```

Never store a private key in the project directory, Git, documentation, or a release archive.

## Trust registry

Approved public keys are registered in `config/calibration_trust_registry_v225_12.json`. The shipped registry is intentionally empty. An administrator must add approved public-key records through a controlled process.

Each key record defines its ID, Ed25519 public key, owner, organisation, allowed projects, allowed environments, validity period, purposes, and status.

## Reviewer workflow

- `technical_reviewer` checks numerical/calibration evidence and lineage;
- `data_governance_reviewer` checks rights, classification, expiry, and production use.

A new decision does not delete the previous decision. It creates a new immutable record linked to the previous decision fingerprint, preserving the full audit history.

## Revocation and expiry

A package, signing key, or detached signature can be revoked. A revocation becomes blocking at `effective_at`. The expiry monitor separately reports expired and soon-to-expire rights, keys, and signatures.

## Lineage

Supported relations are `root`, `supersedes`, `derived_from`, and `recalibrated_from`. A parent must already exist in the same project. Self-references, cycles, and conflicting parents are rejected.

## Final export

The production trust decision is repeated before `PresentationModel` construction. Export artifacts and history v6 retain the trust decision ID, trust-registry fingerprint, signature fingerprint, promotion ID, project authorization package ID, and operator package fingerprint.

Foundation Dual Water remains `blocked_final_report`. The trust workflow does not change production formulas and cannot bypass numerical, calibration, or report-policy gates.
