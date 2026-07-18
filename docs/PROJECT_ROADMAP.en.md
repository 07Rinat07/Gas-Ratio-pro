# Project Roadmap — v225.7

Updated: July 18, 2026.

This document is the only active Gas Ratio Pro development sequence.

## Stage 4 — Workbench UI Completion

Status: **ACTIVE / Release candidate v225.7**.

Completed:

1. unified page-aware package, physical profiles, and cross-format parity gate;
2. A4/A3 portrait/landscape visual golden artifacts and Print Center E2E acceptance;
3. removal of all nine architecture-boundary violations;
4. replacement of 26 brittle source assertions with executable behavior contracts (18 legacy, one Print Center contract, and seven PDF preview contracts);
5. controlled visual rebaseline of 13 contracts through a semantic snapshot manifest;
6. replacement of historical version pins and obsolete Workbench assertions;
7. resolution of all 51 legacy regression contracts with evidence and replacement contracts;
8. one `BUILD_VERSION` source and synchronized `ru/kk/en` documentation;
9. complete regression suite: **2855 passed, 0 failed**.

Next authorized work:

1. perform live acceptance through `run_app.ps1 -ForceRestart`;
2. verify build/source identity and all five Workbench regions;
3. promote v225.7 to stable only after successful acceptance;
4. open the next engineering stage only after stable promotion.

## Stabilization & Release Audit

Architecture boundaries must not be weakened. A visual baseline may change only through the approved semantic manifest and controlled rebaseline. Silent `xfail`, hidden failures, and test deletion without a replacement contract are prohibited.

## Reservoir Intelligence / Interpretation 2.0

Status: **FROZEN AFTER ACCEPTANCE**. The accepted Definition of Done remains a mandatory regression contract:

- Pixler rehabilitation;
- Ternary rehabilitation;
- Depth engineering panel;
- engineering interval summary and reproducible visual classification;
- all approved views consume one calculation result and are not changed by print/export increments.

## Open Standards and Legal Research Governance

External standards and third-party components are integrated only through policy, a machine-readable registry, license confirmation, and an isolated adapter boundary.

## Petrophysical Engine

Status: **BLOCKED** until Stage 4 stable promotion. Only critical fixes that do not change the approved calculation contract are allowed.
