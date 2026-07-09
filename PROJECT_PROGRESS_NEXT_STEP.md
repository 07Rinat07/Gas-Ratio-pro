# Next Step

Active module: Hydrocarbon Interval Engine.

Completed in the latest step:

- expanded interval schema to v5;
- added directional `gas_oil` and `oil_gas` classifications;
- added `water` and `uncertain` classes;
- extended graph marker rows for new interval classes;
- added tests for refined classification behavior;
- added explicit-gap preservation so productive intervals separated by Clay/Claystone/Shale/Tight barrier are not merged by default.

Next implementation target:

- preserve explicit lithological/barrier gaps between productive intervals;
- expose source-row coverage for each interval;
- add confidence/evidence quality flags after interval continuity policy is locked;
- keep Hydrocarbon Interval Engine as the only active module until Definition of Done is reached.

Validation status:

- compileall: PASS;
- pytest: 1043 passed / 0 failed.

## Historical stage markers retained for regression tests

- Architecture Review
- Core LTS Freeze
- Sprint 2
- Workspace Dashboard cards
- Project Explorer shortcuts
- Workspace UI smoke tests
- LAS Workspace 3.0 UI entry point
- LAS creation wizard UI

These completed markers remain in the plan for compatibility with previous implementation-stage tests. They do not change the current active module lock: Hydrocarbon Interval Engine remains the only active implementation stage.

Compatibility markers:
- Sprint 2 Workspace Framework
- LasWorkspaceController.create_las_working_copy

## Hydrocarbon Interval Engine v7 — Structured Evidence and Quality Flags

The active interval model now separates printable evidence from machine-readable evidence.
Every interpreted interval may expose:

- `evidence_items` — structured method/parameter/value/direction/weight records;
- `quality_flags` — machine-readable QA markers such as `single_sample_interval`,
  `limited_numeric_evidence`, `no_numeric_gas_ratios`, `contains_missing_ratio_values`,
  and `uncertain_fluid_character`;
- legacy printable `evidence` strings remain available for current HTML/report tables.

This keeps the Hydrocarbon Interval Engine as the single source of truth for later
Interpretation Engine, graph markers, PDF reports and dashboards. Report modules must
consume the existing interval model and must not recalculate their own evidence.


## Hydrocarbon Interval Engine v8 — Confidence Scoring

Implemented inside the active module only.

- Added numeric `confidence_score` from 0 to 100.
- Added `confidence_factors` for audit and future reports.
- Confidence now uses structured evidence and quality flags.
- Barrier-aware interval separation remains unchanged.
- Next step: validate confidence behavior on weak / uncertain / water / real LAS cases before moving to another module.
