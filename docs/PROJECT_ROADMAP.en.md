# Project Roadmap — v225.3

Updated: 18 July 2026.

This document is the **single active development sequence** for Gas Ratio Pro. Versioned roadmaps, obsolete progress/next-step documents, and parallel plans are retained only under `docs/archive/legacy_plans/`.

Localized versions: [Русский](PROJECT_ROADMAP.ru.md) · [Қазақша](PROJECT_ROADMAP.kk.md) · [English](PROJECT_ROADMAP.en.md).

## Stage 4 — Workbench UI Completion

Status: **ACTIVE**.

The current objective is to complete one user path from the workbench to Professional Print Center without independent export branches.

Completed in v225.3:

- shared physical header/footer/legend/content regions;
- page-space chrome for SVG and PDF;
- PNG generated from the same SVG pages;
- geometry signature v3;
- unified `VisualizationPageAwarePackage`;
- UI-neutral `VisualizationPrintCenterService`;
- one page-aware pipeline for LAS Viewer SVG/PDF/PNG.

Approved next work:

1. connect the localized package summary to the visible Professional Print Center;
2. pass the multi-page page-aware preview directly to DOCX/HTML;
3. remove legacy static-export branches only after automated parity verification;
4. add user-defined physical profile templates without reducing text below the approved minimum.

## Stabilization & Release Audit

Status: **Release candidate v225.3**.

Every release requires a full regression run, format parity checks, A4/A3 physical validation, synchronized Russian/Kazakh/English documentation, manifest/link checks, build-version verification, and release-archive verification.

## Petrophysical Engine

Status: **BLOCKED**.

Petrophysical Engine expansion is prohibited until Stage 4 and Stabilization & Release Audit are complete. Only critical fixes that preserve the approved calculation contract are allowed.

## Release gate

A release is ready only when all representations share one layout/signature, no silent first-page fallback exists, reference artifacts are reproducible, tests and documentation match implementation, and all three language versions remain functionally synchronized.

## Reservoir Intelligence / Interpretation 2.0

Status: **FROZEN AFTER ACCEPTANCE**. The accepted Definition of Done remains a mandatory regression contract for the existing interpretation workflow:

- Pixler rehabilitation;
- Ternary rehabilitation;
- Depth engineering panel;
- engineering interval summary and reproducible visual classification;
- Definition of Done: every approved view uses one calculation result, passes regression tests, and remains unchanged by the print/export increment.

## Open Standards and Legal Research Governance

Any external standard or third-party component is integrated only through approved policy documents, a machine-readable registry, license evidence, and an isolated adapter boundary. A research prototype cannot become a production dependency without a separate review status.
