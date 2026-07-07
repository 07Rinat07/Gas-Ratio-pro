# Correlation Workspace Redesign Specification v4.0


## Phase C — Correlation Workspace 2.0 Backend State

Implemented backend foundation for professional interwell correlation.

### Supported objects

- Stratigraphic boundaries: top/base markers for horizons and layers.
- Lithology intervals: colored depth intervals per well.
- Fluid contacts and fluids: OWC/ВНК, GOC/ГНК, GWC/ГВК, oil, gas, water, gas condensate.
- Correlation lines: generated from matching boundaries or supplied manually.
- Result table: unified rows for UI, export and printing.

### Safety rules

- Source LAS/well data is not mutated.
- All workspace state is built from normalized copies of user tables.
- Missing wells are reported as errors.
- Out-of-range depths are reported as warnings.

### Backend API

- `normalize_stratigraphic_boundaries`
- `normalize_lithology_intervals`
- `normalize_fluid_contacts`
- `boundaries_to_markers`
- `validate_correlation_workspace_v2`
- `build_correlation_result_table`
- `build_correlation_workspace_v2`
