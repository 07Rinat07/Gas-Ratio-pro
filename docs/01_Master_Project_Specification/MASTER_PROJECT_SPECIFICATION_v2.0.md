# MASTER PROJECT SPECIFICATION v2.0

Project: GAS RATIO PRO  
Phase: II — Engineering Specification & Architecture  
Status: Draft 2.0

## 1. Vision

GAS RATIO PRO is a professional modular engineering platform for well data processing, LAS editing, petrophysical interpretation, geological modeling, property calculation, visualization, reporting and controlled data exchange.

The system must evolve from a prototype/foundation application into a coherent engineering product with documented architecture, reproducible calculations, strong LAS support and expandable modules.

## 2. Current Baseline

The project already contains foundation implementations for:

- Dashboard / engineer workspace.
- Project Manager.
- Well Manager.
- LAS Explorer.
- LAS Editor Professional foundation.
- Formation Manager.
- Plot Studio.
- Statistics Center.
- Formula Builder.
- Interpretation Workspace.
- Report Studio.
- Workspace Infrastructure.
- Plugin API / Plugin SDK foundation.
- Correlation Studio.
- Geological Modeling foundation and Zone Manager.
- Data Quality & Validation Center.
- Batch Processing Center.
- Template & Workflow Manager.
- Data Exchange Center foundation.
- Advanced Plot Studio foundation.
- Advanced Correlation Studio foundation.
- Advanced Report Studio foundation.
- Scripting API foundation.
- Performance & Optimization foundation.
- Release Candidate diagnostic layer.

## 3. Strategic Correction

The project is not ready for final release packaging. Phase II must correct the roadmap and specify missing engineering functionality before more modules are implemented.

Critical observations:

- LAS Editor still lacks full LAS creation from scratch.
- LAS editing must be expanded before commercial packaging.
- Property modeling functionality should be planned explicitly.
- Geological modeling should be extended using workflows such as facies modeling, petrophysical modeling, fluid contacts, geometry and property cubes.
- Licensing / Hardware ID / activation is deferred or optional.
- AI Assistant is deferred and not part of the current engineering roadmap.

## 4. Product Scope for Current Roadmap

Included in current professional roadmap:

- LAS Platform Professional.
- LAS creation wizard.
- Curve Manager.
- Header Editor.
- ASCII table editor.
- LAS validation and quality control.
- Curve calculator.
- Data quality and repair tools.
- Property Manager.
- Property Calculator.
- Facies Modeling.
- Petrophysical Modeling.
- Fluid Contact Modeling.
- Geometrical Modeling.
- Reservoir Calculator.
- Function Studio.
- Variogram Studio.
- Crossplot Studio.
- Workflow Engine.
- Data Exchange Professional.
- Visualization Professional.
- Report Studio Professional.
- Plugin SDK and scripting extensions.
- Performance and stabilization.

Deferred:

- AI Assistant.
- Licensing / Hardware ID / activation.
- Cloud collaboration.
- Enterprise user roles.
- Telemetry.

## 5. Required Documentation Set

Phase II must produce and maintain:

1. Master Project Specification v2.0.
2. Roadmap v3.0.
3. Software Requirements Specification.
4. Software Architecture Document.
5. LAS Platform Specification.
6. Calculation Engine Specification.
7. Geological Modeling Specification.
8. UI/UX Guidelines.
9. Database Specification.
10. Testing Specification.

## 6. Core Architecture Blocks

### A. Platform Core

Responsibilities:

- Application state.
- Project context.
- Event bus.
- Command system.
- Undo/redo.
- Settings.
- Logging.
- Diagnostics.
- Version migration.

### B. Project System

Responsibilities:

- Project creation/opening.
- Project metadata.
- Project file inventory.
- History.
- Backup.
- Import/export.
- Manifest validation.

### C. LAS Platform

Responsibilities:

- LAS reading.
- LAS creation.
- LAS editing.
- Curve management.
- Header editing.
- ASCII editing.
- Validation.
- Safe export.
- Templates.

### D. Well Management

Responsibilities:

- Well cards.
- Coordinates.
- Trajectory metadata.
- Formations.
- Perforations.
- Intervals.
- Groups and search.

### E. Interpretation Platform

Responsibilities:

- Formation Manager.
- Zone Manager.
- Pick Manager.
- Correlation Studio.
- Crossplots.
- Interval calculations.

### F. Geological Modeling Platform

Responsibilities:

- Structural framework.
- Zone Manager.
- Facies Modeling.
- Petrophysical Modeling.
- Property cubes.
- Contacts.
- Geometry.
- Reservoir calculations.

### G. Calculation Engine

Responsibilities:

- Formula parsing.
- Safe expression execution.
- Curve calculations.
- Property calculations.
- Statistics.
- Interpolation.
- Filtering.
- Quality checks.

### H. Visualization Platform

Responsibilities:

- LAS plots.
- Multi-track plots.
- Crossplots.
- Histograms.
- Maps.
- Sections.
- Slices.
- Property previews.
- Export to PNG/SVG/PDF.

### I. Data Exchange

Responsibilities:

- LAS.
- CSV.
- XLSX.
- JSON.
- GeoJSON.
- ZIP project exchange.
- Future DLIS/LIS/SEGY/SHAPE compatibility.

### J. Reports

Responsibilities:

- Report packages.
- Content blocks.
- Templates.
- HTML previews.
- Export jobs.
- PDF/Word/Excel/HTML outputs.

### K. Extensibility

Responsibilities:

- Plugin SDK.
- Scripting API.
- Hook registry.
- API documentation.
- Safe extension boundaries.

## 7. Documentation-First Implementation Rule

A new implementation stage may start only when these items exist:

- Module purpose.
- User scenarios.
- Data model.
- API contract.
- UI requirements.
- Validation rules.
- Test acceptance criteria.
- Migration impact.

## 8. Immediate Priority After Phase II Documents

The first implementation block after documentation should be:

B. LAS Platform Professional

Priority tasks:

1. LAS creation wizard.
2. LAS template system.
3. Curve Manager Professional.
4. Header Editor.
5. ASCII Editor.
6. LAS Validator.
7. Safe export writer.
8. Import curves from CSV/XLSX.
9. Curve calculator.
10. LAS Quality Control.

## 9. Acceptance Criteria for Phase II

Phase II is complete when:

- All major specification documents exist.
- Roadmap v3.0 replaces the old linear stage list.
- Licensing and AI are explicitly marked deferred/optional.
- LAS Platform gaps are documented.
- Geological/property modeling roadmap is documented.
- Project documentation structure is reorganized.
- README and CHANGELOG reference Phase II.

## Phase II — B.7 Reference Sources Manager

Статус: реализовано foundation.

Добавлена подсистема хранения доказательных PDF-источников внутри проекта. Локальные пути вида `C:\Users\...` больше не должны использоваться как основная ссылка в документации. Источники регистрируются через относительные пути и проверяются валидатором.

