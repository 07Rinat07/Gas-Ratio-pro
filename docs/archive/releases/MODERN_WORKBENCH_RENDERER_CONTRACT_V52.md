# Modern Workbench Renderer Contract v52

## Purpose

The renderer contract is a stable boundary between the Modern Workbench core model and future UI adapters.
It allows Streamlit or another renderer to display the Workbench without importing calculation, persistence or export logic into the UI layer.

## Contract sections

- `context` — current application context.
- `status` — compact footer/status information.
- `navigation` — visible navigation entries.
- `dock_regions` — dock pane ids grouped by region.
- `panels` — visible panel descriptors.
- `commands` — visible command descriptors for toolbar and command palette.
- `interaction` — active navigation and active dock pane.
- `actions` — renderer-safe actions mapped to command ids and payload schemas.

## UI rule

A renderer must not mutate Workbench session state directly.
It should render the contract and dispatch command ids with payloads through `WorkbenchCommandRegistry`.

## Current actions

- `action.select_navigation` dispatches `workbench.navigation.select` with `navigation_id`.
- `action.activate_dock_pane` dispatches `workbench.dock.activate` with `pane_id`.
