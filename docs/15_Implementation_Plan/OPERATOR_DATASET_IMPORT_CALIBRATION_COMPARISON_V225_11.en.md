# v225.11 implementation plan — Operator Dataset Import & Calibration Comparison

Status: **IMPLEMENTED / verification pending**.

Goals: accept only operator-owned or legally cleared packages; create immutable source/rights fingerprints; keep storage project-scoped; compare baseline and operator versions; create versioned project authorization packages before rendering; preserve production formulas and Stage 5/5.1 gates.

Implementation covers ZIP security, data-rights/expiration validation, stored-checksum revalidation, comparison metrics, baseline fallback, export-cache isolation, evidence CLI, a trilingual Print Center panel, and export-history schema v5.

Definition of Done: import/tamper/version tests, renderer blocking when rights are insufficient, Stage 5.1 fallback, Live Workbench 14/14, full regression with zero failures, and synchronized ru/kk/en documentation.
