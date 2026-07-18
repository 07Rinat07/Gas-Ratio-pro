# Ағымдағы күй — v225.8 Stable

Жаңартылған күні: 2026 жылғы 18 шілде.

## Белсенді кезең

**Stage 4 — Workbench UI Completion аяқталды.** `v225.8` құрастыруы автоматты Live Workbench Acceptance өткеннен кейін **stable** арнасына ауыстырылды.

## Stable promotion

- нақты уақытша Streamlit server `/_stcore/health` арқылы `ok` қайтарады;
- build badge, `BUILD_VERSION`, `BUILD_CHANNEL`, абсолютті runtime source path және entry point сәйкес келеді;
- Toolbar, Project Explorer, Workspace Host, Properties және Status Bar traceback-сіз көрсетіледі;
- command-backed LAS әрекеті `nav.las_workspace` маршрутын таңдайды;
- LAS Viewer және LAS Workspace ашу әрекеті traceback-сіз орындалады;
- acceptance нәтижесі: **14/14 passed**;
- acceptance contract: `config/live_workbench_acceptance_contract_v225_8.json`;
- machine-readable evidence: `artifacts/acceptance/live_workbench_acceptance_v225_8.json`.

## Stabilization & Release Audit

Architecture boundaries, the 51 resolved legacy contracts, controlled visual semantic snapshots, and the live acceptance contract remain mandatory stable-release gates. Silent `xfail`, hidden failures, and test deletion without a replacement contract are prohibited.

## Regression күйі

- full v225.8 regression suite: **2858 passed, 0 failed**;
- acceptance және stable-promotion тесттері baseline үстіне қосылды;
- architecture-boundary debt: **0**;
- белсенді legacy regression contract: **0**;
- controlled visual semantic snapshot міндетті болып қалады.

## Келесі кезең

**Stage 5 — Petrophysical Engine Validation Foundation.** Тек method registry, formula provenance, reference dataset, сандық tolerance және application-service validation gate рұқсат етіледі. Validation evidence болмаса, бекітілген формулаларды, Interpretation 2.0 немесе visual baseline өзгертуге болмайды.
