# GAS RATIO PRO — Project Progress

Current version: `las-correlation-studio-state-controller`

## Completed in this step

- Moved LAS Correlation Studio marker state behind `ApplicationStateController`.
- Moved comparison curve persistence behind `ApplicationStateController`.
- Replaced remaining direct `st.session_state` reads/writes in `streamlit_app.py` with controller calls, except the single controller factory boundary.
- Added regression coverage for LAS correlation Studio state handling.

## Validation

- `compileall`: PASS
- `pytest`: 943 passed / 0 failed

## Next recommended step

Run the final ApplicationStateController audit and start preparing Architecture Review / Core LTS Freeze documentation.
