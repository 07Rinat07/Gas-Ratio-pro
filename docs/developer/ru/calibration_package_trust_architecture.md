# Архитектура доверия калибровочных пакетов

Revision 1 · Gas Ratio Pro v225.12

## Граница ответственности

Stage 5.3 не изменяет операторский ZIP, calibration registry, dataset или production formulas. Trust evidence является отдельным project-scoped слоем:

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

## Основные модули

- `core/calibration_package_trust_contract.py` — схемы, canonical JSON, fingerprints, Ed25519 signing/verification и registry validation;
- `services/calibration_package_trust_application_service.py` — import signature, review, revocation, expiry, lineage, promotion и trust decision;
- `services/calibration_package_trust_diagnostics.py` — локализованный read-only view model;
- `services/operator_calibration_package_application_service.py` — требует production trust перед активацией и финальной project authorization;
- `core/application_service_container.py` — создаёт один project-scoped trust service и внедряет его в operator/export boundary;
- `reports/export_controller.py` и `reports/export_history.py` — сохраняют trust evidence; history schema обновлена до v6.

## Схемы

- `gas-ratio-pro/calibration-trust-registry/v1`;
- `gas-ratio-pro/calibration-detached-signature/v1`;
- `gas-ratio-pro/calibration-review-decision/v1`;
- `gas-ratio-pro/calibration-revocation/v1`;
- `gas-ratio-pro/calibration-promotion-record/v1`;
- `gas-ratio-pro/calibration-trust-decision/v1`;
- `gas-ratio-pro/calibration-expiry-report/v1`.

## Криптографический контракт

Используется Ed25519 из пакета `cryptography`. Подписывается canonical JSON detached envelope без полей `signature_base64` и `signature_fingerprint`. Envelope включает exact package fingerprint, project ID, key ID, signer identity, signed/expiry timestamps и lineage.

Публичный ключ хранится как raw 32-byte Ed25519 key в Base64. Подпись хранится как 64-byte value в Base64. Private key application service не принимает и не сохраняет.

## Trust registry

Registry является application-scoped public-key policy. Его fingerprint вычисляется по canonical JSON без `registry_fingerprint`. Ключ допускается только когда:

- status = `active`;
- purpose содержит `operator_calibration_package_signing`;
- project входит в `allowed_projects`;
- target environment входит в `allowed_environments`;
- `valid_from/valid_until` допускают текущий момент;
- key revocation отсутствует.

## Project repository

```text
data/projects/<project>/petrophysics/operator_calibration/trust/
  signatures/<package_fingerprint>/<signature_fingerprint>.json
  reviews/<package_fingerprint>/<decision_fingerprint>.json
  revocations/<target_type>/<target_id>/<revocation_fingerprint>.json
  promotions/<package_fingerprint>/<promotion_id>.json
  environments/<package_fingerprint>.json
```

Signature, review, revocation и promotion records immutable. Запись с тем же fingerprint и другим содержимым отклоняется.

## Reviewer chain

Review record содержит `previous_decision_fingerprint`. Последнее решение определяется по terminal node цепочки, а не по имени файла или timestamp. Это исключает неоднозначность нескольких решений в одну секунду.

Promotion policy:

- validation: минимум одно текущее approval роли `technical_reviewer`;
- production: текущие approvals `technical_reviewer` и `data_governance_reviewer`;
- любое текущее `reject` блокирует promotion.

## Environment integrity

Разрешены только последовательные переходы:

```text
development → validation → production
```

Environment state ссылается на immutable promotion record. Trust decision проверяет соответствие current environment, state promotion ID и последнего promotion record. Ручное изменение environment JSON не даёт production authorization.

## Revocation и expiry

Revocation target: `package`, `key` или `signature`. Effective revocation блокирует выбор подписи и final export.

Expiry monitor агрегирует:

- `rights.expires_at` из immutable package manifest;
- `expires_at` detached signature;
- `valid_until` trusted key.

## Lineage

Lineage является частью подписанного detached envelope. Parent package должен быть импортирован в том же проекте. Проверяются self-reference, cycle и conflicting parent across signatures.

## Export boundary

В application container `OperatorCalibrationPackageApplicationService` создаётся с `require_production_trust=True`. Последовательность final export:

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

Cache context включает trust decision, registry, signature и promotion fingerprints. Изменение trust context очищает project export cache до рендера.

## Security policy

- private keys запрещены в source tree, tests fixtures, docs, evidence и release ZIP;
- default trust registry пуст;
- доверие нельзя получить только импортом ZIP;
- UI не выполняет криптографию самостоятельно, а вызывает application service;
- production formulas и method registry не меняются Stage 5.3;
- `.github/workflows` не требуется для локальной поставки и исключается из user archive.
