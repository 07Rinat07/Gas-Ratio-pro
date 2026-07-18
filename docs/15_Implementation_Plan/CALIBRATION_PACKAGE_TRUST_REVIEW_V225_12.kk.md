# v225.12 іске асыру жоспары — Calibration Package Trust & Review Workflow

Күйі: **COMPLETED / Stable v225.12**.

## Мақсаттар

1. Өзгермейтін операторлық пакетті detached Ed25519 қолтаңбасымен қол қою және жабық кілтті қолданбаға енгізбеу.
2. Қолтаңбаны project/environment scope және validity period бар application-scoped trust registry арқылы тексеру.
3. Reviewer decisions, revocations, lineage және promotion records бастапқы ZIP-тен бөлек сақтау.
4. Тек `development → validation → production` ретімен promotion рұқсат ету.
5. Trust evidence жеткіліксіз, қайтарылған немесе мерзімі өткен кезде activation/final export бұғаттау.
6. Trust fingerprints-ті project authorization package, export artifact және Export History v6 ішінде сақтау.
7. Production formulas және Stage 5/5.1/5.2 contracts өзгертпеу.

## Іске асыру

- canonical trust schemas және fingerprints;
- detached Ed25519 signature verify;
- бос default trust registry және public-key administration contract;
- `previous_decision_fingerprint` бар immutable review chain;
- package/key/signature revocation;
- rights/signature/key expiry monitor;
- cycle/self-reference қорғанысы бар signed lineage;
- immutable promotion record-пен байланысқан environment state;
- `PresentationModel` және renderer алдында production trust gate;
- trust context бойынша cache isolation;
- Export History schema v6;
- үш тілді Professional Print Center panel;
- key generation, detached signing және Stage 5.3 evidence CLI.

## Definition of Done

- cryptography, review, revocation, expiry, lineage және promotion tests өтеді;
- environment state қолмен өзгерту production trust бермейді;
- private key source tree, tests, docs, evidence және release ZIP ішінде жоқ;
- production promotion-ға дейін activation/export blocked;
- Foundation Dual Water `blocked_final_report` күйінде қалады;
- Live Workbench Acceptance `ru/kk/en` тілдерінде өтеді;
- full regression failures жоқ;
- ru/kk/en құжаттамасы синхрондалған;
- `.github/workflows` user archive құрамына кірмейді.
