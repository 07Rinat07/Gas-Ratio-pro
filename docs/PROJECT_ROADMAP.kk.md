# Project Roadmap — v225.7

Жаңартылған күні: 2026 жылғы 18 шілде.

Бұл құжат Gas Ratio Pro жобасының жалғыз белсенді әзірлеу реті болып табылады.

## Stage 4 — Workbench UI Completion

Мәртебе: **ACTIVE / Release candidate v225.7**.

Аяқталды:

1. бірыңғай page-aware package, physical profile және cross-format parity gate;
2. A4/A3 portrait/landscape visual golden artifact және Print Center E2E acceptance;
3. тоғыз architecture-boundary бұзушылығының барлығы жойылды;
4. 26 brittle source assertion орындалатын behavior contract тесттерімен ауыстырылды (18 legacy, бір Print Center contract және 7 PDF preview contract);
5. 13 контракт semantic snapshot manifest арқылы controlled visual rebaseline-тан өтті;
6. тарихи version pin және ескірген Workbench assertion ауыстырылды;
7. 51 legacy regression contract evidence және replacement contract-пен жабылды;
8. бір `BUILD_VERSION` көзі және синхронды `ru/kk/en` құжаттамасы енгізілді;
9. толық regression suite: **2855 passed, 0 failed**.

Келесі рұқсат етілген жұмыстар:

1. `run_app.ps1 -ForceRestart` арқылы live acceptance өткізу;
2. build/source identity және Workbench-тің бес аймағын тексеру;
3. сәтті қабылдаудан кейін ғана v225.7 stable promotion орындау;
4. stable promotion-нан кейін ғана келесі инженерлік кезеңді ашу.

## Stabilization & Release Audit

Architecture boundary әлсіретуге болмайды. Visual baseline тек бекітілген semantic manifest және controlled rebaseline арқылы өзгертіледі. Silent `xfail`, failure жасыру және replacement contract-сыз тест жоюға тыйым салынады.

## Reservoir Intelligence / Interpretation 2.0

Мәртебе: **FROZEN AFTER ACCEPTANCE**. Қабылданған Definition of Done міндетті regression contract болып қалады:

- Pixler rehabilitation;
- Ternary rehabilitation;
- Depth engineering panel;
- интервалдардың инженерлік қорытындысы және қайталанатын визуалдық классификация;
- барлық бекітілген көрініс бір calculation result пайдаланады және print/export инкременттерімен өзгертілмейді.

## Open Standards and Legal Research Governance

Сыртқы стандарттар мен third-party components тек policy, machine-readable registry, лицензиялық растау және оқшауланған adapter boundary арқылы қосылады.

## Petrophysical Engine

Мәртебе: Stage 4 stable promotion аяқталғанша **BLOCKED**. Бекітілген есептеу контрактын өзгертпейтін критикалық түзетулерге ғана рұқсат беріледі.
