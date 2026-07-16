# ADR-001 — Framework-independent UI Platform

Status: Approved

## Decision
Workbench and engineering modules shall depend on the GAS RATIO PRO UI SDK rather than directly on Streamlit. Streamlit remains the current adapter/runtime. Future Qt, Tauri or web adapters may be added without changing application or domain services.

## Consequences
- New UI work uses design tokens and SDK components.
- Existing direct `st.*` calls are migrated incrementally during v223.x.
- Business data, repositories and application services remain UI-neutral.
- Adapter-specific objects must not cross into core contracts or session persistence.
