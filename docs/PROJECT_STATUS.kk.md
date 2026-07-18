# Ағымдағы күй — v225.11 Stable

Жаңартылды: 18 шілде 2026 жыл.

## Белсенді кезең

**Stage 5.2 — Operator Dataset Import & Calibration Comparison аяқталды.** Production формулалар өзгермеді.

- ZIP тек `manifest.json`, `calibration_registry.json`, `calibration_dataset.json` файлдарын қамтиды;
- тек `operator_owned`, `licensed`, `public_domain` деректері қабылданады;
- project scope, owner, legal basis, processing/derivative permissions және expiration блоктаушы;
- package/file/rights fingerprints импортта және әр пайдалануда тексеріледі;
- `package_id + version` immutable;
- private operator data тек жоба repository ішінде қалады және релиз архивіне кірмейді;
- baseline және package versions 10 әдіс бойынша салыстырылады;
- versioned project authorization package renderer алдында жасалады;
- export history v5 authorization package ID және operator fingerprint сақтайды;
- active context өзгерсе export cache тазарады;
- foundation Dual Water `blocked_final_report` күйінде қалады.

Evidence: `artifacts/validation/petrophysical_operator_calibration_v225_11.json`; Stage 5.2 gate — import 1/1, comparison 10/10, authorization 9/9; full regression **2915 passed, 0 failed**; Live Workbench **14/14**.

## Stabilization & Release Audit

Stage 5/5.1 gates, architecture boundaries, controlled visual baselines және full-frame report layout міндетті. `.github/workflows` пайдаланушы архивіне кірмейді.

Reservoir Intelligence / Interpretation 2.0, Pixler rehabilitation, Ternary rehabilitation және Depth engineering panel explicit validation evidence болмаса өзгермейді.

## Келесі кезең

**Stage 5.3 — Calibration Package Trust & Review Workflow:** detached signatures, trust registry, reviewer approval, revocation және controlled project promotion.
