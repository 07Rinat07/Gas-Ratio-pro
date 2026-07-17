# Project Roadmap — v225.3

Жаңартылған күні: 18 шілде 2026 жыл.

Бұл құжат Gas Ratio Pro әзірлеуінің **жалғыз белсенді реттілігі** болып табылады. Нұсқалық roadmap файлдары, ескі progress/next-step құжаттары және параллель жоспарлар тек `docs/archive/legacy_plans/` ішінде сақталады.

Тілдік нұсқалар: [Русский](PROJECT_ROADMAP.ru.md) · [Қазақша](PROJECT_ROADMAP.kk.md) · [English](PROJECT_ROADMAP.en.md).

## Stage 4 — Workbench UI Completion

Күйі: **ACTIVE**.

Мақсат — жұмыс аймағынан Professional Print Center-ге дейінгі пайдаланушы жолын тәуелсіз экспорт тармақтарынсыз аяқтау.

v225.3 нұсқасында аяқталды:

- header/footer/legend/content үшін бірыңғай физикалық аймақтар;
- SVG және PDF үшін page-space chrome;
- сол SVG беттерінен PNG жасау;
- geometry signature v3;
- бірыңғай `VisualizationPageAwarePackage`;
- UI-дан тәуелсіз `VisualizationPrintCenterService`;
- LAS Viewer SVG/PDF/PNG үшін бір page-aware pipeline.

Келесі рұқсат етілген жұмыстар:

1. локализацияланған пакет жиынтығын көрінетін Professional Print Center-ге қосу;
2. көпбетті page-aware preview-ді DOCX/HTML-ге тікелей беру;
3. automated parity тексерілгеннен кейін ғана legacy static-export тармақтарын жою;
4. мәтінді рұқсат етілген минимумнан кішірейтпей, пайдаланушының физикалық профиль шаблондарын қосу.

## Stabilization & Release Audit

Күйі: **Release candidate v225.3**.

Әр шығарылым алдында толық regression, форматтар parity-і, A4/A3 физикалық параметрлері, үш тілдегі құжаттама, manifest, сілтемелер, build нұсқасы және release archive тексеріледі.

## Petrophysical Engine

Күйі: **BLOCKED**.

Stage 4 және Stabilization & Release Audit аяқталғанша петрофизикалық қозғалтқышты кеңейтуге тыйым салынады. Тек бекітілген есептеу келісімшартын өзгертпейтін критикалық түзетулерге рұқсат.

## Release gate

Шығарылым тек бір layout/signature, silent single-page fallback болмауы, қайталанатын эталондар, іске асыруға сәйкес тесттер және үш тілдегі синхронды құжаттама болғанда дайын деп саналады.

## Reservoir Intelligence / Interpretation 2.0

Күйі: **FROZEN AFTER ACCEPTANCE**. Қолданыстағы интерпретация регрессиясы үшін міндетті Definition of Done сақталады:

- Pixler rehabilitation;
- Ternary rehabilitation;
- Depth engineering panel;
- интервалдардың инженерлік жиынтығы және қайталанатын визуалды жіктеу;
- Definition of Done: барлық бекітілген көріністер бір есептеу нәтижесін пайдаланады, регрессиялық тесттерден өтеді және print/export кезеңінде өзгермейді.

## Open Standards and Legal Research Governance

Сыртқы стандарт немесе third-party component тек бекітілген policy құжаттары, machine-readable registry, лицензия дәлелі және оқшауланған adapter boundary арқылы біріктіріледі. Зерттеу прототипі жеке review status алмайынша production dependency болмайды.
