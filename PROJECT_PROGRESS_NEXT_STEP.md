# Project Progress — Next Step

Current version: `gas-ratio-pro-curve-rename-merge-state-controller`

Completed in this step:

- Moved LAS curve rename history state behind `ApplicationStateController`.
- Moved LAS curve merge history state behind `ApplicationStateController`.
- Removed direct UI access to `st.session_state` from rename/merge history workflows.
- Kept existing LAS editor behavior and undo workflows compatible.
- Verified full project test suite.

Validation:

- `compileall`: PASS
- `pytest`: 937 passed / 0 failed

Next recommended step:

- Continue ApplicationStateController cleanup for LAS editor session sheet/summary state.
