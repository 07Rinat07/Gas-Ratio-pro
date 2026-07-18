# Stable release and Workbench acceptance

Revision: 1. Applies to Gas Ratio Pro `v225.8`.

## Normal start

```powershell
.\run_app.ps1 -ForceRestart
```

The launcher reads the version from `BUILD_VERSION`, checks the port, clears Python caches on forced restart, and starts `app/streamlit_app.py` from the active project directory.

## Automated stable-release acceptance

```powershell
.\run_app.ps1 -ForceRestart -Acceptance
```

The gate starts a temporary loopback Streamlit server and verifies:

- the health endpoint;
- build version and absolute source path;
- Toolbar;
- Project Explorer;
- Workspace Host;
- Properties;
- Status Bar;
- the LAS command;
- LAS Workspace opening without a traceback.

The JSON report is written to `artifacts/acceptance/live_workbench_acceptance.json`. The stable release is accepted only when `passed: true` and every required check passes.

## Safety

Acceptance does not import or modify user LAS files. It uses the current project metadata context and safe Workbench navigation. The temporary server is always stopped after the check.
