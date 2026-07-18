# Project Roadmap — v225.5

Жаңартылған күні: 18 шілде 2026 жыл.

Бұл құжат Gas Ratio Pro әзірлеуінің жалғыз белсенді реті болып табылады.

## Stage 4 — Workbench UI Completion

Күйі: **ACTIVE / release candidate v225.5**.

Аяқталды:

1. SVG/PNG/PDF/DOCX/HTML үшін бір page-aware package;
2. көрінетін көпбетті Professional Print Center;
3. бұғаттаушы cross-format parity gate;
4. safety floor бар A4/A3 пайдаланушы физикалық профильдері;
5. legacy CompositeLog static-export тоқтатылды;
6. multi-page SVG/PNG үшін manifest-backed ZIP;
7. `ru/kk/en` құжаттамасы синхрондалды.

Келесі рұқсат етілген жұмыстар:

1. толық Print Center workflow пайдаланушы acceptance-test;
2. A4/A3 portrait/landscape және пайдаланушы профильдері үшін visual golden artifacts;
3. қалған legacy regression contracts аудиті;
4. Stage 4 аяқтап, release candidate нұсқасын stable күйіне ауыстыру.

## Stabilization & Release Audit

Әр релиз алдында parity gate, regression прогон, A4/A3 физикалық тексеру, `ru/kk/en` құжаттама, manifest/links/version metadata және архив тұтастығы міндетті.

## Reservoir Intelligence / Interpretation 2.0

Күйі: **FROZEN AFTER ACCEPTANCE**. Қабылданған Definition of Done міндетті регрессиялық келісімшарт болып қалады:

- Pixler rehabilitation;
- Ternary rehabilitation;
- Depth engineering panel;
- аралықтардың инженерлік жиынтығы және қайталанатын визуалдық жіктеу;
- Definition of Done: барлық бекітілген көріністер бір есептеу нәтижесін пайдаланады және print/export кезеңдерінде өзгермейді.

## Open Standards and Legal Research Governance

Сыртқы стандарттар мен third-party components тек policy, machine-readable registry, лицензиялық растау және оқшауланған adapter boundary арқылы қосылады.

## Petrophysical Engine

Күйі: Stage 4 аяқталғанша **BLOCKED**. Бекітілген есептеу келісімшартын өзгертпейтін сыни түзетулер ғана рұқсат.
