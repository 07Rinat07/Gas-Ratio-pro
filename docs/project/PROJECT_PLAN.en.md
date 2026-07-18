# Gas Ratio Pro Project Plan

Updated: 18 July 2026. Active build: `v225.6`.

## Completed stage — v225.6

- four physical golden baselines for A4/A3 portrait/landscape;
- reproducible golden regeneration and checksum verification;
- full Professional Print Center acceptance path;
- raster preview auto-scaling against the actual PDF frame;
- machine-readable audit of all 51 legacy regressions;
- replacement policy with no silent `xfail`;
- trilingual documentation and release governance.

## Next authorized increment — Legacy Contract Remediation

1. Fix architecture-boundary violations without weakening audit policy.
2. Move brittle source assertions to view-model and runtime behavior tests.
3. Approve visual rebaseline through golden artifacts.
4. Delete obsolete tests only after replacement tests exist.
5. Repeat the full regression and stable promotion gate.

## Definition of Done

- all four golden profile manifests pass without checksum drift;
- E2E acceptance creates valid HTML/PDF/DOCX and SVG/PNG output;
- every legacy contract has a disposition and replacement;
- release-blocking architecture debt is zero;
- version, instructions, status, roadmap, changelog, and manifest are synchronized in `ru/kk/en`.
