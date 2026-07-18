# Текущее состояние — v225.12 Stable

Обновлено: 18 июля 2026 года.

## Активный этап

**Stage 5.3 — Calibration Package Trust & Review Workflow завершён и подтверждён как Stable v225.12.** Production formulas не изменялись.

## Trust boundary

- исходный операторский ZIP Stage 5.2 остаётся byte-for-byte неизменяемым;
- detached Ed25519 signature связывает точный `package_fingerprint`, project ID, key ID, signer identity, срок действия и lineage;
- default trust registry намеренно пуст и содержит только утверждённые public-key records;
- private keys не принимаются и не сохраняются application services.

## Review, revocation и expiry

- validation требует current approval роли `technical_reviewer`;
- production требует current approvals ролей `technical_reviewer` и `data_governance_reviewer`;
- review history immutable и связана через `previous_decision_fingerprint`;
- package, key и signature могут быть отозваны;
- data-rights, signature и key expiry проверяются перед финальным отчётом.

## Controlled promotion и lineage

- разрешена только последовательность `development → validation → production`;
- environment state сверяется с immutable promotion record;
- ручное изменение state не предоставляет production trust;
- lineage поддерживает `root`, `supersedes`, `derived_from`, `recalibrated_from`;
- parent должен существовать в том же проекте, cycles/self-reference/conflicting parent запрещены.

## Export authorization

- strict production trust проверяется до activation, `PresentationModel` и renderer;
- trust decision, registry/signature fingerprints и promotion ID входят в project authorization package;
- ExportArtifact и Export History schema v6 сохраняют trust evidence;
- изменение trust context очищает project export cache;
- Foundation Dual Water остаётся `blocked_final_report`.

## Evidence

- `artifacts/validation/calibration_package_trust_v225_12.json`;
- Stage 5.3 gate: signature **1/1**, reviewer approvals **2/2**, promotion transitions **2/2**, production trust **passed**, private keys persisted **0**;
- Live Workbench Acceptance: **14/14** на `ru/kk/en`;
- полный regression-suite: **2934 passed, 0 failed**; release verification завершён.

## Стабильные контракты

Stable Workbench, full-frame A3 landscape layout, architecture boundaries, controlled visual baselines, numerical validation, field calibration, operator rights, immutable package storage и authorization до renderer остаются обязательными.

Reservoir Intelligence / Interpretation 2.0, Pixler rehabilitation, Ternary rehabilitation и Depth engineering panel не изменяются без explicit validation evidence.

## Stabilization & Release Audit

Trust workflow не может обходить Stage 5/5.1/5.2 gates. Private keys и private operator datasets не распространяются. `.github/workflows` не включается в пользовательский архив.

## Следующий этап

**Stage 5.4 — Trust Registry Operations & External Identity Integration.** Следующий разрешённый контур: controlled key rotation, authenticated reviewer identity adapter, audit-bundle export, registry administration и optional external KMS/HSM boundary без изменения production formulas.
