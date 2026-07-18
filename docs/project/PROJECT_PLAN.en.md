# Gas Ratio Pro Project Plan

Updated: 18 July 2026. Active build: `v225.5`.

## Mandatory engineering principles

- one pipeline is the source of physical geometry;
- `export_ready` requires a successful cross-format parity gate;
- user A4/A3 profiles cannot weaken readability floors;
- multi-page SVG/PNG is never collapsed to page one;
- documentation and instructions are updated synchronously in `ru / kk / en`.

## Completed stage — v225.5

- SVG/PNG/PDF/DOCX/HTML parity gate;
- page-aware package v1.3;
- persistent user profiles;
- manifest-backed static bundles;
- retirement of CompositeLog static export;
- parity status in Professional Print Center;
- tests and trilingual documentation.

## Next authorized increment — Stage 4 Acceptance & Stable Promotion

1. Run the user acceptance path for profile creation and selection.
2. Verify A4/A3 portrait/landscape and custom profiles on real data.
3. Freeze visual golden artifacts.
4. Resolve remaining legacy test failures.
5. Promote to stable only after the complete release gate passes.

## Definition of Done

- package parity is automatically proven;
- the physical profile is visible and reproducible;
- every page is retained in every format;
- no legacy first-page/static fallback remains;
- build metadata, README, instructions, status, roadmap, changelog, and manifest are synchronized.
