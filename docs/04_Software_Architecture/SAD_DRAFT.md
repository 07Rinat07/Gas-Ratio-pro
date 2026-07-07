# Software Architecture Document — Draft

Project: GAS RATIO PRO  
Phase: II — Engineering Specification & Architecture

## 1. Architectural Style

GAS RATIO PRO follows a modular layered architecture.

## 2. Layers

```text
UI Layer
  ↓
Workspace / Module Controllers
  ↓
Service Layer
  ↓
Domain Models
  ↓
Project Storage / File Adapters
  ↓
External Files and Exports
```

## 3. Core Modules

### Core
- Application state.
- Settings.
- Logging.
- Diagnostics.
- Event bus.

### Project
- Active project.
- Metadata.
- Manifests.
- History.
- File inventory.

### LAS Platform
- LAS reader.
- LAS editor.
- LAS writer.
- LAS validator.
- Curve manager.

### Geological Modeling
- Zones.
- Facies.
- Properties.
- Contacts.
- Geometry.
- Reservoir calculations.

### Visualization
- Plot definitions.
- Preview specifications.
- Export manifests.

### Data Exchange
- Import/export profiles.
- Format adapters.
- Exchange history.

### Reports
- Report packages.
- Content blocks.
- Render manifests.
- Export jobs.

### Extensibility
- Plugin registry.
- Hook registry.
- Scripting API.

## 4. Dependency Rules

- UI may depend on service APIs.
- Services may depend on domain models.
- Domain models must not depend on Streamlit.
- Backend modules should be testable without UI.
- LAS Platform must not depend on Geological Modeling.
- Geological Modeling may consume LAS-derived data through stable data objects.
- Report Studio may consume outputs from other modules but should not mutate them.

## 5. Data Persistence

Project-level module storage should use explicit JSON files with stable schemas, for example:

- `project_index.json`
- `geological_modeling.json`
- `data_exchange.json`
- `correlation_studio.json`
- `report_studio.json`
- `plugin_sdk.json`
- `performance_optimization.json`
- future `scripting_api.json`
- future `las_platform.json`

## 6. Architecture Decisions

### AD-001: Documentation First
All new large modules require specification before implementation.

### AD-002: Licensing Deferred
License Manager and Hardware ID are not part of current engineering core.

### AD-003: AI Deferred
AI Assistant is excluded from current roadmap.

### AD-004: Safe LAS Editing
Original LAS files must never be overwritten.
