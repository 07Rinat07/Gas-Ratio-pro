# Model Validation & Audit Workspace Specification Draft

## Purpose

The Model Validation & Audit Workspace verifies the consistency, completeness and readiness of an integrated geological model before export, reporting, visualization or further professional interpretation.

## Scope

The foundation version covers:

- dependency graph audit;
- required foundation component coverage;
- optional professional component coverage;
- broken dependency detection;
- orphan object detection;
- object metadata and traceability checks;
- readiness score calculation;
- audit manifest generation;
- Markdown audit reporting;
- UI-ready issue, check and coverage tables.

## Required foundation components

The audit expects the integrated model to contain the following core object types:

- geological model;
- structural model;
- grid;
- facies model;
- property cube;
- volumetrics case.

## Optional professional components

The following components improve model maturity but are not treated as blocking errors in the foundation audit:

- well;
- LAS dataset;
- interval;
- geostatistics job;
- interpolation job;
- simulation job;
- petrophysical case;
- report package;
- source document.

## Severity system

Issues are classified as:

- `error` — blocking issue that makes the model not ready;
- `warning` — important issue that should be reviewed;
- `info` — non-blocking recommendation or maturity indicator.

## Readiness score

The readiness score is calculated on a 0–100 scale. The foundation implementation penalizes critical errors, warnings, missing required types, orphan objects and broken dependencies.

Readiness statuses:

- `ready`;
- `partially_ready`;
- `not_ready`.

## Output

The module produces:

- audit manifest;
- audit check table;
- issue table;
- coverage table;
- Markdown audit report;
- persisted audit records in the project workspace.

## Acceptance criteria

The module is accepted when:

- it detects missing required model components;
- it detects broken dependency graph edges;
- it reports metadata and traceability warnings;
- it calculates a deterministic readiness score;
- it saves an audit record to the project workspace;
- it provides UI-ready tables and Markdown report output;
- profile tests and `compileall` pass successfully.
