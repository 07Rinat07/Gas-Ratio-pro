# Geological Modeling Specification — Draft

## 1. Purpose

This document defines the planned geological and property modeling capabilities of GAS RATIO PRO.

## 2. Data Inputs

Potential data inputs:

- Well coordinates.
- Well trajectories.
- Formation tops.
- LAS curves.
- Interpreted properties.
- Core data.
- Fluid contacts.
- Surfaces.
- Polygons.
- Trend maps.

## 3. Modeling Workflow

Professional workflow:

1. Data preparation.
2. Structural/stratigraphic framework.
3. Zone and layer definition.
4. Well data upscaling/blocking.
5. Facies/lithology modeling.
6. Property modeling.
7. Fluid contact modeling.
8. Geometrical property calculation.
9. Saturation modeling.
10. Reservoir volume calculation.
11. Validation and reporting.

## 4. Planned Modules

### 4.1 Facies Modeling
- Facies dictionary.
- Discrete facies properties.
- Vertical proportion analysis.
- Horizontal trend usage.
- Facies statistics.

### 4.2 Petrophysical Modeling
- Porosity.
- Permeability.
- Water saturation.
- Oil/gas saturation.
- Rock type.
- Facies-conditioned properties.

### 4.3 Fluid Contacts
- OWC.
- GOC.
- GWC.
- Constant depth contacts.
- Surface contacts.
- Zone-specific contacts.

### 4.4 Geometry
- Cell height.
- Bulk volume.
- Depth.
- Above contact.
- Relative depth.
- Net volume.

### 4.5 Reservoir Calculator
- OOIP.
- OGIP.
- HCPV.
- Net pay.
- Volume summary.

### 4.6 Variogram Studio
- Experimental variograms.
- Directional variograms.
- Model fitting.
- Variogram templates.

## 5. Acceptance Criteria

- Each modeling operation must have input/output definitions.
- Property lineage must be recorded.
- Validation reports must be available.
- UI helper tables must be generated for model objects.

### Phase II — C.1 Property Modeling Workspace Foundation

Status: Implemented.

Implemented backend foundation for property modeling:

- property cube metadata registry;
- facies/lithology discrete property foundation;
- Net/Gross calculation `NG = If(Facies in sand_values, 1, 0)`;
- POR/PERM/SW/SO/SG property placeholders;
- fluid contacts foundation: OWC, GOC, GWC;
- geometry properties foundation: bulk volume, absolute depth, above contact;
- manifest, UI-ready tables and Markdown reporting.

### Phase II — C.3 Geostatistics Workspace Foundation

Status: Implemented.

The geostatistics foundation defines the first backend layer for spatial property interpolation.
The module supports experimental variogram calculation from spatial samples, theoretical models
(spherical, exponential, gaussian, linear, nugget), deterministic parameter fitting, search ellipsoid
configuration and job manifests for future interpolation workflows.

This module prepares the project for Kriging, Sequential Gaussian Simulation and facies/property
modeling workflows that require documented variogram and neighborhood parameters.


## Phase II C.4 — Interpolation Engine Foundation

The interpolation engine provides the backend layer for transferring well/property samples into grid targets. The foundation includes regular grid generation, normalized sample models, nearest-neighbor interpolation, IDW interpolation, simple kriging foundation metadata, interpolation jobs, manifests, UI-ready tables and Markdown reports.

The module is intentionally deterministic and conservative so that future Kriging, SGS and co-kriging algorithms can reuse the same public API without breaking existing workflows.

## Phase II C.5 — Property Simulation Engine Foundation

The Property Simulation Engine defines the backend layer for stochastic geological property modeling.

The foundation includes:

- Sequential Gaussian Simulation foundation for continuous properties;
- Sequential Indicator Simulation foundation for discrete facies/lithology properties;
- explicit simulation seed for reproducibility;
- realization number tracking;
- per-cell uncertainty and confidence metadata;
- simulation job registry;
- manifest generation;
- UI-ready tables;
- Markdown reporting.

The current implementation is intentionally conservative and deterministic where required. It creates a stable API for future full geostatistical SGS/SIS, co-kriging, co-simulation and uncertainty workflows.

## Phase II C.8 — Geological Model Workspace Foundation

The Geological Model Workspace introduces a single integrated model object that connects interpretation, petrophysics, property modeling, fluid contacts, volumetrics and future 3D visualization.

### Objects

- `GeologicalModel` — main model metadata, status, CRS and version.
- `GridDefinition` — 3D grid metadata: type, dimensions, spacing, source and status.
- `HorizonDefinition` — stratigraphic boundaries linked to surfaces.
- `ZoneDefinition` — model zones between top and base horizons, including layer count.
- `SurfaceDefinition` — horizon, contact, map or fault surface metadata.
- `FaultDefinition` — structural fault foundation.
- `ModelLink` — traceable links to wells, intervals, facies, property cubes, contacts and volumetrics.

### Validation

The workspace checks missing surfaces, missing top/base horizons and invalid zone configuration. This is a foundation layer; actual grid arrays and 3D rendering remain separate modules.

## C.11 Model Validation & Audit Workspace

The geological modeling stack includes a validation and audit workspace that checks the integrated model registry, dependency graph, required foundation components, optional professional components, object metadata and readiness score. The output is an audit manifest, UI-ready tables and a Markdown engineering audit report.
