# Sprint 1.5 — UI Repository Boundary Cleanup

## Purpose

This pass continues Integration & Stabilization by reducing direct repository dependencies from the monolithic Streamlit shell.

## Implemented

- Removed the direct `wells.repository.DEFAULT_WELLS_ROOT` import from `app/streamlit_app.py`.
- Exposed `DEFAULT_WELLS_STORAGE_ROOT` from `services/well_manager_service.py` as the service-layer storage constant.
- Kept `WELLS_STORAGE_ROOT` behavior unchanged while moving the dependency behind the service boundary.
- Added regression tests to ensure Streamlit UI does not import the well repository directly.

## Current audit status

`core.integration_audit.audit_streamlit_app()` now reports:

- 0 blocking errors;
- 0 direct repository import warnings;
- remaining warnings are direct `st.session_state` writes in the legacy monolithic UI shell.

The remaining session-state warnings are tracked as migration debt for ApplicationState cleanup and Workspace Framework extraction.

## Next pass

Continue Sprint 1.5 with a focused ApplicationState migration pass. The first target should be project/workspace state keys that affect deletion, rerun, and active project switching.
