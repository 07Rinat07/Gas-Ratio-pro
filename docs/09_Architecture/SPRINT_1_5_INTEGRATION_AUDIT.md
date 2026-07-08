# Sprint 1.5 — Integration Audit

## Purpose

This document records the first source-level Integration & Stabilization pass after Sprint 1. The goal is not to add new engineering features, but to make the platform reliable enough for Sprint 2.

## Implemented in this pass

- Added `core/integration_audit.py`.
- Added automated checks for direct destructive filesystem calls.
- Added automated checks for direct repository imports from the Streamlit shell.
- Added automated tracking of direct `st.session_state` writes in the monolithic UI shell.
- Added regression tests in `tests/test_integration_audit.py`.

## Current acceptance status

### Blocking rules

The audit treats direct destructive file operations as blocking errors:

- `shutil.rmtree(...)`
- `os.remove(...)`
- `os.rmdir(...)`
- `Path.unlink()`
- `Path.rmdir()`

These operations must go through the Storage Lifecycle Framework and `DeleteEngine`.

### Migration warnings

The following items are still warning-level during Sprint 1.5 because `app/streamlit_app.py` remains a large legacy shell:

- direct repository imports from UI;
- direct `st.session_state` writes.

They are documented as migration debt for Workspace Framework and ApplicationState cleanup.

## Next pass

The next Sprint 1.5 pass should focus on reducing warning-level migration debt in `streamlit_app.py` without adding new user-facing functionality.
