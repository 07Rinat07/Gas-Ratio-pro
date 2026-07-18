# Ағымдағы күй — v225.9 Stable

Жаңартылған күні: 2026 жылғы 18 шілде.

## Белсенді кезең

**Stage 5 — Petrophysical Engine Validation Foundation аяқталды.** Формулалар өзгертілмеді; міндетті machine-readable validation gate құрылды.

## Validation foundation

- 10 әдіс `config/petrophysical_method_registry_v225_9.json` ішінде тіркелген;
- 10 synthetic reference case `data/validation/petrophysics/petrophysical_validation_cases_v225_9.json` ішінде;
- әр әдісте provenance, units, applicability, limitations, absolute/relative tolerance және uncertainty metadata бар;
- application service нақты production-функцияларды орындайды;
- gate: **10/10 passed**, final-report eligible: **9/10**;
- `petrophysics.sw_dual_water_foundation` сандық түрде қайталанады, бірақ policy `blocked_final_report`;
- evidence: `artifacts/validation/petrophysical_validation_v225_9.json`.

## Есептердің бейімделетін макеті

- A3 landscape PDF нақты ReportLab frame ені мен биіктігін пайдаланады;
- metadata, legend, statistics және мәтіндік кестелер толық жұмыс frame-ын алады;
- DOCX ағымдағы section енін, HTML responsive 100% width қолданады;
- `print-readability/v1.1` және v225.9 visual baseline тар сол жақ бағанға қайта оралуды блоктайды.

## Stabilization & Release Audit

Stage 4 Live Workbench Acceptance (**14/14 passed**), architecture boundaries, controlled visual semantic snapshots және жабылған legacy contracts міндетті болып қалады. Silent `xfail`, failures жасыру және evidence-сіз формуланы өзгертуге тыйым салынады.

v225.9 қорытынды тексеруі: **2881 passed, 0 failed**; кеңейтілген report/export контуры: **338 passed**; Live Workbench Acceptance: **14/14**; petrophysical validation: **10/10**.

## Келесі кезең

**Stage 5.1 — Field Calibration & Report Authorization Integration.** Field-owned calibration datasets, parameter uncertainty/sensitivity, read-only diagnostics және `authorize_methods(..., final_report=True)` функциясын final export boundary-ге қосуға рұқсат.
