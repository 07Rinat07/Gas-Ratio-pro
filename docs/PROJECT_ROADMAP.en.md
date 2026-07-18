# Project Roadmap — v225.4

Updated: 18 July 2026.

This document is the **single active development sequence** for Gas Ratio Pro. Versioned roadmaps and parallel progress/next-step files are retained only under `docs/archive/legacy_plans/`.

Localized versions: [Русский](PROJECT_ROADMAP.ru.md) · [Қазақша](PROJECT_ROADMAP.kk.md) · [English](PROJECT_ROADMAP.en.md).

## Stage 4 — Workbench UI Completion

Status: **ACTIVE**.

Completed in v225.4:

- visible Professional Print Center consumes one physical page-aware package;
- exact profile and every preview page are available before launch;
- DOCX/HTML receive canonical multi-page preview directly;
- the shared strict normalizer prevents silent first-page fallback;
- `bundle` is included in the unified export path;
- `ru/kk/en` preview localization is synchronized.

Approved next work:

1. automated UI/PDF/DOCX/HTML/SVG/PNG parity matrix for A4/A3 portrait/landscape;
2. legacy static-export retirement after the parity gate passes;
3. user physical profiles without reducing text below the approved minimum;
4. close Stage 4 after validating the real user path.

## Stabilization & Release Audit

Status: **Release candidate v225.4**.

Every release requires regression, format parity, physical A4/A3 checks, synchronized `ru/kk/en` documentation, manifest/link/version-metadata checks, and archive integrity verification.

## Petrophysical Engine

Status: **BLOCKED**.

Petrophysical Engine expansion is prohibited until Stage 4 and Stabilization & Release Audit are complete.

## Release gate

A release is ready only with one layout and geometry signature, a complete multi-page contract, no silent fallback, reproducible artifacts, tests and documentation matching code, and synchronized three-language coverage.

## Reservoir Intelligence / Interpretation 2.0

Status: **FROZEN AFTER ACCEPTANCE**. The accepted Definition of Done remains a mandatory regression contract:

- Pixler rehabilitation;
- Ternary rehabilitation;
- Depth engineering panel;
- engineering interval summary and reproducible visual classification;
- Definition of Done: all approved views use one calculation result and remain unchanged by print/export increments.
