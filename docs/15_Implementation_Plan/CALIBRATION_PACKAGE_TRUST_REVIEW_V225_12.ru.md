# План реализации v225.12 — Calibration Package Trust & Review Workflow

Статус: **COMPLETED / Stable v225.12**.

## Цели

1. Подписывать неизменяемый операторский пакет detached Ed25519-подписью без включения закрытого ключа в приложение.
2. Проверять подпись через application-scoped trust registry с project/environment scope и сроком действия.
3. Хранить reviewer decisions, revocations, lineage и promotion records отдельно от исходного ZIP.
4. Разрешать только последовательное продвижение `development → validation → production`.
5. Блокировать активацию и финальный экспорт при недостаточном trust evidence, отзыве или истечении срока.
6. Сохранять trust fingerprints в project authorization package, export artifact и Export History v6.
7. Не изменять production formulas и Stage 5/5.1/5.2 contracts.

## Реализация

- canonical trust schemas и fingerprints;
- detached Ed25519 signature verify;
- пустой default trust registry и административный public-key contract;
- immutable review chain с `previous_decision_fingerprint`;
- package/key/signature revocation;
- rights/signature/key expiry monitor;
- signed package lineage с cycle/self-reference protection;
- environment state, связанный с immutable promotion record;
- production trust gate до `PresentationModel` и renderer;
- cache isolation по trust context;
- Export History schema v6;
- трёхъязычная панель Professional Print Center;
- CLI для генерации ключа, detached signing и Stage 5.3 evidence.

## Definition of Done

- cryptographic, review, revocation, expiry, lineage и promotion tests проходят;
- ручное изменение environment state не предоставляет production trust;
- private key отсутствует в source tree, tests, documentation, evidence и release ZIP;
- activation/export blocked до production promotion;
- Foundation Dual Water остаётся `blocked_final_report`;
- Live Workbench Acceptance проходит на `ru/kk/en`;
- full regression не содержит failures;
- документация ru/kk/en синхронизирована;
- `.github/workflows` отсутствует в пользовательском архиве.
