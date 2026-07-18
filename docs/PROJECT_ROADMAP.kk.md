# Project Roadmap — v225.9 Stable

Жаңартылған күні: 2026 жылғы 18 шілде. Бұл құжат Gas Ratio Pro дамуының жалғыз белсенді реттілігі.

## Stage 4 — Workbench UI Completion

Күйі: **COMPLETED / Stable v225.8**. Live Workbench Acceptance: 14/14.

## Stage 5 — Petrophysical Engine Validation Foundation

Күйі: **COMPLETED / Stable v225.9**.

Орындалды:

1. формулаларды өзгертпей 10 production method freeze;
2. machine-readable provenance, source/legal metadata және report policy;
3. inputs, parameters және outputs үшін unit contracts;
4. expected results бар 10 synthetic reference dataset;
5. absolute/relative tolerances және uncertainty metadata;
6. application-service gate, CLI және JSON evidence;
7. calculation manifests ішінде method provenance және contract fingerprint;
8. foundation Dual Water үшін final-report block;
9. PDF/DOCX/HTML үшін A3 landscape adaptive full-frame layout және v225.9 visual baseline.

## Stabilization & Release Audit

Stable v225.8 Live Workbench Acceptance remains mandatory: **14/14 passed**. Architecture boundaries, controlled visual baselines, replacement contracts, and the v225.9 petrophysical validation gate may not be bypassed.

## Stage 5.1 — Field Calibration & Report Authorization Integration

Күйі: **NEXT AUTHORIZED**.

1. тек field-owned немесе legally cleared calibration datasets қосу;
2. parameter distributions және sensitivity/uncertainty envelopes сипаттау;
3. final-report authorization функциясын export application service-ке қосу;
4. formulas өзгертпейтін read-only validation diagnostics қосу;
5. full regression және Live Workbench Acceptance қайталау.

## Reservoir Intelligence / Interpretation 2.0

Күйі: **FROZEN AFTER ACCEPTANCE**. Pixler, Ternary, Depth engineering panel және бірыңғай calculation result тек explicit validation evidence арқылы өзгереді.

## Definition of Done

- Stable v225.8 Workbench acceptance қайталанады;
- petrophysical gate барлық method contract-тарды өткізеді;
- final report `blocked_final_report` әдісін қолдана алмайды;
- full regression suite failures қамтымайды;
- landscape есептері тұрақты тар бағансыз нақты frame-ды пайдаланады;
- құжаттама орыс, қазақ және ағылшын тілдерінде синхрондалған.

## Open Standards and Legal Research Governance

Сыртқы әдістер, стандарттар және datasets тек source/legal registry және оқшауланған adapter boundary арқылы қосылады.

Any third-party component requires a machine-readable license/source record and an isolated adapter boundary.
