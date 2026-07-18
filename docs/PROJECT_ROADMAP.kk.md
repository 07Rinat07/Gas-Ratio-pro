# Project Roadmap — v225.8 Stable

Жаңартылған күні: 2026 жылғы 18 шілде.

Бұл құжат Gas Ratio Pro жобасының жалғыз белсенді әзірлеу реті болып табылады.

## Stage 4 — Workbench UI Completion

Мәртебе: **COMPLETED / Stable v225.8**.

Аяқталды:

1. page-aware package, physical profile және cross-format parity gate;
2. A4/A3 visual golden artifact және Print Center E2E acceptance;
3. 9 architecture-boundary бұзушылығы жойылды;
4. brittle source assertion behavior contract-пен ауыстырылды;
5. controlled visual rebaseline және 51 legacy regression contract жабылды;
6. толық v225.8 regression suite: **2858 passed, 0 failed**;
7. нақты server health және орындалатын Streamlit session бар Live Workbench Acceptance;
8. build/source identity және Workbench-тің бес аймағы расталды;
9. LAS командасы және LAS Workspace traceback-сіз орындалды;
10. stable promotion `v225.8`: **14/14 acceptance checks passed**.

## Stage 5 — Petrophysical Engine Validation Foundation

Мәртебе: **NEXT AUTHORIZED**.

Рұқсат етілген рет:

1. ағымдағы Method Registry inventory және freeze;
2. machine-readable formula/source provenance;
3. белгілі expected result бар reference validation dataset;
4. сандық tolerance, unit contract және uncertainty metadata;
5. бірыңғай application-service validation gate;
6. жаңа UI view қосылғанға дейін regression evidence.

UI қалауы немесе тіркелмеген дереккөз негізінде формуланы өзгертуге болмайды. Әр жаңа формулаға method ID, legal/source record, units, applicability domain, reference dataset және tolerance қажет.

## Stabilization & Release Audit

Architecture boundary әлсіретуге болмайды. Visual baseline тек approved semantic manifest арқылы өзгереді. Silent `xfail`, failure жасыру және replacement contract-сыз тест жоюға тыйым салынады. Stable promotion `gas-ratio-pro/live-workbench-acceptance/v1` арқылы дәлелденеді.

## Reservoir Intelligence / Interpretation 2.0

Мәртебе: **FROZEN AFTER ACCEPTANCE**. Міндетті regression contract:

- Pixler rehabilitation;
- Ternary rehabilitation;
- Depth engineering panel;
- инженерлік interval summary және қайталанатын visual classification;
- барлық бекітілген view бір calculation result пайдаланады.

## Definition of Done

- Stage 4 stable acceptance remains reproducible and passes all required checks;
- Stage 5 methods have machine-readable provenance, units, applicability domains, datasets, and tolerances;
- no approved Interpretation 2.0 or visual contract changes without explicit validation evidence;
- full regression suite contains no failures;
- documentation remains synchronized in Russian, Kazakh, and English.

## Open Standards and Legal Research Governance

Сыртқы стандарттар мен third-party components тек policy, machine-readable registry, лицензиялық растау және оқшауланған adapter boundary арқылы қосылады.
