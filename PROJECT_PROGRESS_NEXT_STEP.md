# GAS RATIO PRO — Project Progress

Current version: `las-correlation-settings-state-controller`

## Completed in this step

- Moved LAS correlation saved-settings session handling behind `ApplicationStateController`.
- Replaced direct project LAS selection cache cleanup with controller-managed removal.
- Read dashboard layout state through the controller instead of direct Streamlit state access.
- Added regression tests that verify LAS correlation settings UI and start tab do not use direct `st.session_state` access.

## Validation

- `compileall`: PASS
- `pytest`: 942 passed / 0 failed

## Next recommended step

Continue ApplicationStateController cleanup for the remaining LAS correlation Studio keys:

- `las_correlation_studio_markers`
- `las_correlation_comparison_curve`
- correlation marker defaults and comparison curve persistence
