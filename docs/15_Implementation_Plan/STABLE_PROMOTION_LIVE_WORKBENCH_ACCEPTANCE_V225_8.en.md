# v225.8 — Stable Promotion & Live Workbench Acceptance

## Goal

Promote Stage 4 from release candidate to stable using reproducible runtime evidence rather than a manual sign-off.

## Completed

1. Added a real temporary Streamlit server health gate.
2. Added AppTest acceptance for all five Workbench regions.
3. Verified build/source identity and entry-point SHA-256.
4. Exercised LAS command navigation and LAS Workspace opening without a traceback.
5. Added a CLI and `run_app.ps1 -Acceptance` mode.
6. Switched the build channel to `stable` only after 14/14 checks passed.
