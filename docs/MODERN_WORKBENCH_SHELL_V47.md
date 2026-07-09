# Modern Workbench Shell V47

## Purpose

This increment starts the Modern Workbench sprint after the P0 export QA stabilization track.

The implementation adds framework-neutral Workbench foundations. Streamlit UI can render these models later, but the shell itself does not import Streamlit and does not perform business calculations.

## Added modules

- `core.command_framework`
  - `WorkbenchCommand`
  - `WorkbenchCommandRegistry`
  - `CommandExecutionResult`
  - `default_workbench_commands`

- `core.workbench_shell`
  - `WorkbenchPanel`
  - `WorkbenchStatus`
  - `WorkbenchShellModel`
  - `WorkbenchShellBuilder`

## Architecture rules preserved

- UI remains free of business logic.
- Commands are plain descriptors and can be used by buttons, toolbar actions, keyboard shortcuts or a future command palette.
- Command execution publishes an application event through the existing event bus.
- Workbench shell state is built from the application state controller and workspace session keys.
- The model is serializable, which makes it safe for tests, Streamlit rendering and future plugin integration.

## Default shell regions

- Project Explorer
- Workspace Toolbar
- Workspace Area
- Properties
- Status Bar

## Default commands

- Open workspace
- Save session
- Restore session
- Reset workspace
- Export bundle

## QA

Added `tests/test_workbench_shell_foundation.py`.

Validated behavior:

- default command descriptors are present;
- command execution runs an optional handler;
- command execution publishes an event;
- shell model includes core regions;
- status payload reflects active project, well, LAS, workspace and recent exports;
- shell model can be serialized for future UI rendering.

## Next step

Connect this shell model to a Streamlit renderer boundary without moving calculations or persistence logic into UI code.
