# Калибрлеу пакеттерінің сенім архитектурасы

Revision 1 · Gas Ratio Pro v225.12

## Жауапкершілік шекарасы

Stage 5.3 оператор ZIP, calibration registry, dataset немесе production formulas өзгертпейді. Trust evidence бөлек project-scoped қабатта сақталады:

```text
immutable operator package
→ detached Ed25519 signature
→ trusted public key
→ review/revocation/expiry
→ development → validation → production
→ final-report trust decision
```

## Негізгі модульдер

- `core/calibration_package_trust_contract.py` — schemas, canonical JSON, fingerprints және Ed25519 verify;
- `services/calibration_package_trust_application_service.py` — signature import, review, revocation, expiry, lineage және promotion;
- `services/calibration_package_trust_diagnostics.py` — үш тілді read-only view model;
- `services/operator_calibration_package_application_service.py` — activation/final authorization алдында production trust талап етеді;
- `core/application_service_container.py` — project-scoped dependency injection;
- `reports/export_controller.py`, `reports/export_history.py` — trust evidence және history v6.

## Contracts

`calibration-trust-registry/v1`, `calibration-detached-signature/v1`, `calibration-review-decision/v1`, `calibration-revocation/v1`, `calibration-promotion-record/v1`, `calibration-trust-decision/v1` және `calibration-expiry-report/v1` схемалары қолданылады.

## Криптография

Ed25519 `cryptography` кітапханасы арқылы орындалады. Canonical JSON envelope-тің `signature_base64` және `signature_fingerprint` өрістерінсіз қол қойылады. Private key application service-ке берілмейді және жоба ішінде сақталмайды.

## Trust registry

Public key тек `active` күйінде, signing purpose бар, project/environment scope сәйкес және validity period ішінде болғанда жарамды. Registry fingerprint canonical JSON бойынша есептеледі.

## Project repository

```text
data/projects/<project>/petrophysics/operator_calibration/trust/
  signatures/
  reviews/
  revocations/
  promotions/
  environments/
```

Records immutable. Бір fingerprint басқа мазмұнмен қайта жазылмайды.

## Reviewer chain

Review record `previous_decision_fingerprint` сақтайды. Latest decision timestamp бойынша емес, terminal chain node арқылы анықталады.

- validation: `technical_reviewer` approval;
- production: `technical_reviewer` + `data_governance_reviewer` approvals;
- current reject promotion-ды блоктайды.

## Environment integrity

Тек `development → validation → production` реттілігі рұқсат. Environment state immutable promotion record ID-мен байланысады. JSON-ды қолмен production күйіне өзгерту authorization бермейді.

## Revocation, expiry және lineage

Package, key немесе signature revocation қолдау көрсетіледі. Rights, signature және key expiry әр final export алдында тексеріледі. Lineage signed envelope ішінде; parent сол жобада болуы керек, cycle/self-reference/conflicting parent тыйым салынған.

## Export boundary

Application container production trust enforcement қосады. Trust decision `PresentationModel` және renderer алдында орындалады. ExportArtifact және Export History v6 trust decision ID, registry/signature fingerprints және promotion ID сақтайды. Trust context өзгерсе project export cache тазартылады.

## Қауіпсіздік саясаты

Private keys source tree, docs, tests, evidence және release ZIP ішінде болмауы тиіс. Default trust registry бос. Stage 5.3 production formulas немесе method registry өзгертпейді. `.github/workflows` user archive құрамына кірмейді.
