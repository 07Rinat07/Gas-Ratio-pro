# Calibration package trust architecture

Revision 1 · Gas Ratio Pro v225.12

## Responsibility boundary

Stage 5.3 does not modify the operator ZIP, calibration registry, dataset, or production formulas. Trust evidence is a separate project-scoped layer:

```text
immutable operator package
        ↓ package_fingerprint
detached Ed25519 signature
        ↓ trusted public key
review decisions + revocations + expiry
        ↓ controlled promotion
development → validation → production
        ↓
final-report trust decision
```

## Main modules

- `core/calibration_package_trust_contract.py` defines schemas, canonical JSON, fingerprints, Ed25519 signing/verification, and registry validation;
- `services/calibration_package_trust_application_service.py` owns signature import, review, revocation, expiry, lineage, promotion, and trust decisions;
- `services/calibration_package_trust_diagnostics.py` supplies the localised read-only view model;
- `services/operator_calibration_package_application_service.py` requires production trust before activation and final project authorization;
- `core/application_service_container.py` constructs one project-scoped trust boundary and injects it into operator/export services;
- `reports/export_controller.py` and `reports/export_history.py` preserve trust evidence; history uses schema v6.

## Schemas

- `gas-ratio-pro/calibration-trust-registry/v1`;
- `gas-ratio-pro/calibration-detached-signature/v1`;
- `gas-ratio-pro/calibration-review-decision/v1`;
- `gas-ratio-pro/calibration-revocation/v1`;
- `gas-ratio-pro/calibration-promotion-record/v1`;
- `gas-ratio-pro/calibration-trust-decision/v1`;
- `gas-ratio-pro/calibration-expiry-report/v1`.

## Cryptographic contract

Ed25519 is provided by `cryptography`. The canonical detached envelope is signed without `signature_base64` and `signature_fingerprint`. The signed payload binds the exact package fingerprint, project ID, key ID, signer identity, signing/expiry timestamps, and lineage.

The public key is stored as a raw 32-byte Ed25519 key in Base64. The detached signature is a 64-byte Base64 value. Application services never accept or persist a private key.

## Trust registry

The registry is application-scoped public-key policy. Its fingerprint is computed from canonical JSON without `registry_fingerprint`. A key is eligible only when:

- status is `active`;
- its purposes include `operator_calibration_package_signing`;
- the project is allowed;
- the target environment is allowed;
- the current time is inside `valid_from/valid_until`;
- no effective key revocation exists.

## Project repository

```text
data/projects/<project>/petrophysics/operator_calibration/trust/
  signatures/<package_fingerprint>/<signature_fingerprint>.json
  reviews/<package_fingerprint>/<decision_fingerprint>.json
  revocations/<target_type>/<target_id>/<revocation_fingerprint>.json
  promotions/<package_fingerprint>/<promotion_id>.json
  environments/<package_fingerprint>.json
```

Signature, review, revocation, and promotion records are immutable. Reusing one fingerprint with different content is rejected.

## Reviewer chain

Each review record carries `previous_decision_fingerprint`. The current decision is derived from the terminal node of the chain rather than filename order or second-level timestamps.

Promotion policy:

- validation requires a current `technical_reviewer` approval;
- production requires current `technical_reviewer` and `data_governance_reviewer` approvals;
- any current rejection blocks promotion.

## Environment integrity

Only sequential transitions are allowed:

```text
development → validation → production
```

Environment state references an immutable promotion record. Trust evaluation verifies the current environment, state promotion ID, and latest promotion record. Manually changing the environment JSON cannot grant production authorization.

## Revocation and expiry

Revocation targets are package, key, and signature. Effective revocation removes the signature from trust selection and blocks final export.

The expiry monitor aggregates package-rights expiry, detached-signature expiry, and trusted-key validity.

## Lineage

Lineage is part of the signed envelope. A parent package must already be imported in the same project. Self-reference, cycles, and conflicting parent declarations across signatures are rejected.

## Export boundary

The application container constructs `OperatorCalibrationPackageApplicationService` with `require_production_trust=True`.

```text
method context
→ Stage 5 numerical validation
→ Stage 5.1/5.2 calibration and rights
→ Stage 5.3 production trust decision
→ PresentationModel
→ renderer
→ ExportArtifact
→ Export History v6
```

The cache context includes trust-decision, registry, signature, and promotion fingerprints. A trust-context change clears the project export cache before rendering.

## Security policy

- private keys are forbidden in source, tests, documentation, committed evidence, and release ZIP files;
- the default registry is empty;
- importing a ZIP alone never grants trust;
- UI code delegates all trust operations to the application service;
- Stage 5.3 does not modify production formulas or the method registry;
- `.github/workflows` is not required by the local distribution and remains excluded from user archives.
