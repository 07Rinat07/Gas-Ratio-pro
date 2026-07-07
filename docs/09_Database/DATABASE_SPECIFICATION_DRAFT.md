# Database and Project Storage Specification — Draft

## 1. Purpose

This document defines project storage principles for GAS RATIO PRO.

## 2. Storage Strategy

Current project storage uses JSON files for module-specific metadata. This approach remains acceptable for local project workflows, but schemas must be documented and versioned.

## 3. Existing Project Storage Files

Examples:

- `project_index.json`
- `geological_modeling.json`
- `data_exchange.json`
- `correlation_studio.json`
- `report_studio.json`
- `plugin_sdk.json`
- `performance_optimization.json`
- `release_candidate.json`

## 4. Planned Storage Files

- `las_platform.json`
- `scripting_api.json`
- `property_modeling.json`
- `facies_modeling.json`
- `petrophysics.json`
- `reservoir_calculator.json`
- `workflow_engine.json`

## 5. Schema Rules

Each JSON storage file should include:

- `schema_version`.
- `project_id` when applicable.
- `updated_at`.
- Object list/dictionary.
- History or provenance where needed.
- Validation issues where needed.

## 6. Migration Rules

- New versions must not break old projects without migration.
- Migrations must be deterministic.
- Migration results must be logged.
