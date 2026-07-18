# Project Roadmap — v225.6

Жаңартылған күні: 18 шілде 2026 жыл.

Бұл құжат — Gas Ratio Pro дамуының жалғыз белсенді тізбегі.

## Stage 4 — Workbench UI Completion

Күйі: **ACTIVE / release candidate v225.6**.

Аяқталды:

1. бірыңғай page-aware package және cross-format parity gate;
2. A4/A3 пайдаланушы профильдері және manifest-backed multi-page delivery;
3. төрт сертификатталған физикалық профиль үшін visual golden-artifacts;
4. HTML/PDF/DOCX/SVG/PNG үшін end-to-end Print Center acceptance;
5. mixed-orientation PDF preview scaling түзетуі;
6. 51 legacy regression contract machine-readable жүйелік аудиті;
7. `ru/kk/en` синхронды құжаттамасы.

Келесі рұқсат етілген жұмыстар:

1. audit registry ішіндегі 9 architecture-boundary violation түзету;
2. 23 source/behavior assertion-ды behavior-level тесттермен ауыстыру;
3. 13 visual contract үшін golden review арқылы controlled rebaseline орындау;
4. 6 obsolete version pin-ді тек replacement identity contract-пен бірге жою;
5. толық suite қайталау және release-blocking debt болмаған кезде ғана Stage 4 stable күйіне өткізу.

## Stabilization & Release Audit

Golden artifacts тек айқын regeneration script және visual review арқылы өзгереді. Silent `xfail`, baseline failures жасыру және replacement contract жоқ тестті жоюға тыйым салынады.

## Reservoir Intelligence / Interpretation 2.0

Күйі: **FROZEN AFTER ACCEPTANCE**. Қабылданған Definition of Done міндетті regression contract болып қалады:

- Pixler rehabilitation;
- Ternary rehabilitation;
- Depth engineering panel;
- интервалдардың инженерлік жиынтығы және қайталанатын визуалдық жіктеу;
- барлық бекітілген көріністер бір есептеу нәтижесін пайдаланады және print/export инкременттерімен өзгермейді.

## Open Standards and Legal Research Governance

Сыртқы стандарттар мен third-party components тек policy, machine-readable registry, лицензиялық дәлел және оқшауланған adapter boundary арқылы қосылады.

## Petrophysical Engine

Күйі: Stage 4 аяқталғанға дейін **BLOCKED**. Бекітілген есептеу келісімшартын өзгертпейтін критикалық түзетулер ғана рұқсат етіледі.
