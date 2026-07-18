# Project Roadmap — v225.4

Жаңартылған күні: 18 шілде 2026 жыл.

Бұл құжат Gas Ratio Pro дамуының **жалғыз белсенді реттілігі** болып табылады. Нұсқалық roadmap және параллель progress/next-step құжаттары тек `docs/archive/legacy_plans/` ішінде сақталады.

## Stage 4 — Workbench UI Completion

Күйі: **ACTIVE**.

v225.4 ішінде аяқталды:

- көрінетін Professional Print Center бір физикалық page-aware package пайдаланады;
- нақты профиль және барлық preview беттері іске қоспас бұрын қолжетімді;
- DOCX/HTML канондық көпбетті preview-ды тікелей алады;
- ортақ strict normalizer бірінші бетке үнсіз fallback жасауды болдырмайды;
- `bundle` бірыңғай экспорт жолына қосылды;
- preview үшін `ru/kk/en` локализациясы синхрондалды.

Келесі рұқсат етілген жұмыстар:

1. A4/A3 portrait/landscape үшін UI/PDF/DOCX/HTML/SVG/PNG автоматтандырылған parity матрицасы;
2. parity gate өткеннен кейін legacy static-export жолдарын жою;
3. мәтінді бекітілген минимумнан кішірейтпейтін пайдаланушы физикалық профильдері;
4. нақты пайдаланушы жолын тексергеннен кейін Stage 4 аяқтау.

## Stabilization & Release Audit

Күйі: **Release candidate v225.4**.

Әр шығарылым алдында regression, format parity, A4/A3 физикалық тексеруі, `ru/kk/en` құжаттамасының синхрондалуы, manifest/сілтемелер/version metadata және архив тұтастығы міндетті.

## Petrophysical Engine

Күйі: **BLOCKED**.

Stage 4 және Stabilization & Release Audit аяқталғанша петрофизикалық қозғалтқышты кеңейтуге тыйым салынады.

## Release gate

Шығарылым бір layout пен geometry signature, толық multi-page contract, silent fallback жоқтығы, қайталанатын артефактілер, кодқа сәйкес тесттер мен құжаттама және үш тілдің синхрондылығы болғанда ғана дайын.

## Reservoir Intelligence / Interpretation 2.0

Күйі: **FROZEN AFTER ACCEPTANCE**. Қабылданған Definition of Done міндетті регрессиялық келісімшарт болып қалады:

- Pixler rehabilitation;
- Ternary rehabilitation;
- Depth engineering panel;
- аралықтардың инженерлік жиынтығы және қайталанатын визуалдық жіктеу;
- Definition of Done: барлық бекітілген көріністер бір есептеу нәтижесін пайдаланады және print/export кезеңдерінде өзгермейді.
