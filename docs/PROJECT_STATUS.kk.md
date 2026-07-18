# Ағымдағы күй — v225.12 Stable

Жаңартылды: 2026 жылғы 18 шілде.

## Белсенді кезең

**Stage 5.3 — Calibration Package Trust & Review Workflow аяқталды және Stable v225.12 ретінде расталды.** Production formulas өзгермеді.

## Trust boundary

- Stage 5.2 бастапқы operator ZIP byte-for-byte өзгермейді;
- detached Ed25519 signature нақты `package_fingerprint`, project ID, key ID, signer identity, validity және lineage байланыстырады;
- default trust registry әдейі бос және тек бекітілген public-key records сақтайды;
- application services private keys қабылдамайды және сақтамайды.

## Review, revocation және expiry

- validation үшін current `technical_reviewer` approval қажет;
- production үшін current `technical_reviewer` және `data_governance_reviewer` approvals қажет;
- review history immutable және `previous_decision_fingerprint` арқылы байланысады;
- package, key және signature қайтарылуы мүмкін;
- data-rights, signature және key expiry final report алдында тексеріледі.

## Controlled promotion және lineage

- тек `development → validation → production` реттілігі рұқсат;
- environment state immutable promotion record-пен салыстырылады;
- state-ті қолмен өзгерту production trust бермейді;
- lineage: `root`, `supersedes`, `derived_from`, `recalibrated_from`;
- parent сол жобада болуы керек, cycles/self-reference/conflicting parent тыйым салынған.

## Export authorization

- strict production trust activation, `PresentationModel` және renderer алдында тексеріледі;
- trust decision, registry/signature fingerprints және promotion ID project authorization package құрамына кіреді;
- ExportArtifact және Export History schema v6 trust evidence сақтайды;
- trust context өзгерсе project export cache тазартылады;
- Foundation Dual Water `blocked_final_report` күйінде қалады.

## Evidence

- `artifacts/validation/calibration_package_trust_v225_12.json`;
- Stage 5.3 gate: signature **1/1**, reviewer approvals **2/2**, promotion transitions **2/2**, production trust **passed**, private keys persisted **0**;
- Live Workbench Acceptance: `ru/kk/en` үшін **14/14**;
- толық regression-suite: **2934 passed, 0 failed**; release verification аяқталды.

## Тұрақты contracts

Stable Workbench, full-frame A3 landscape layout, architecture boundaries, controlled visual baselines, numerical validation, field calibration, operator rights, immutable package storage және renderer алдындағы authorization міндетті.

Reservoir Intelligence / Interpretation 2.0, Pixler rehabilitation, Ternary rehabilitation және Depth engineering panel explicit validation evidence-сіз өзгермейді.

## Stabilization & Release Audit

Trust workflow Stage 5/5.1/5.2 gates айналып өтпейді. Private keys және private operator datasets таратылмайды. `.github/workflows` user archive құрамына кірмейді.

## Келесі кезең

**Stage 5.4 — Trust Registry Operations & External Identity Integration.** Controlled key rotation, authenticated reviewer identity adapter, audit-bundle export, registry administration және optional external KMS/HSM boundary; production formulas өзгермейді.
