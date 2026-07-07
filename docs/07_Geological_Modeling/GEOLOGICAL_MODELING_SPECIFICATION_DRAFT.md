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
