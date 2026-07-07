# GAS RATIO PRO — ROADMAP v3.0

Phase: II — Engineering Specification & Architecture  
Status: Draft

## Roadmap Policy

Roadmap v3.0 replaces the previous long numeric stage sequence. Development is now grouped by functional blocks. Each item must be specified before implementation.

Licensing / Hardware ID / Activation is optional and deferred to the last commercial packaging phase. AI Assistant is not part of the current roadmap.

---

## A. Platform Core

### A.1 Core Architecture Review
- Define module boundaries.
- Define public/private APIs.
- Define event bus rules.
- Define command pattern for undoable operations.

### A.2 Project Context
- Active project lifecycle.
- Project metadata.
- Project manifest.
- Project file inventory.
- Migration rules.

### A.3 Command System
- Command registration.
- Undo/redo framework.
- Operation history.
- Error rollback policy.

### A.4 Diagnostics
- Preflight audit.
- Module health checks.
- Import/export diagnostics.
- Release readiness report.

---

## B. LAS Platform Professional

### B.1 LAS Creation Wizard
- Create LAS from scratch.
- Define well name, UWI/API, start/stop/step/null value.
- Generate depth index.
- Select LAS version/profile.
- Create mandatory sections.

### B.2 LAS Template System
- Built-in templates.
- User templates.
- Mud gas template.
- Petrophysics template.
- Empty well template.

### B.3 Header Editor
- Version section editor.
- Well section editor.
- Curve section editor.
- Parameter section editor.
- Other section editor.

### B.4 Curve Manager Professional
- Add curve.
- Delete curve.
- Rename curve.
- Change units.
- Change description.
- Reorder curves.
- Category mapping.
- Alias dictionary integration.

### B.5 ASCII Editor
- Table editing.
- Insert/delete rows.
- Insert/delete depth samples.
- Edit cell values.
- Null value handling.
- Bulk operations.

### B.6 Safe LAS Writer
- Never overwrite source LAS.
- Save as new LAS.
- Validate before export.
- Export report.

### B.7 LAS Validator
- Mandatory sections check.
- Depth monotonicity.
- Duplicate depths.
- Missing values.
- Curve mnemonic validation.
- Unit validation.
- ASCII column count validation.

### B.8 Curve Import
- Import curves from CSV.
- Import curves from XLSX.
- Depth matching.
- Resampling.
- Merge policy.
- Conflict report.

### B.9 Curve Calculator
- Formula-based curve creation.
- Safe expression parser.
- Moving average.
- Despike.
- Smoothing.
- Normalization.
- Gas ratio formulas.

### B.10 LAS Quality Control
- Missing intervals.
- Spikes.
- Flat lines.
- Outliers.
- Negative/invalid values.
- Unit mismatch warnings.

---

## C. Well Management

### C.1 Well Card Professional
- Full well metadata.
- Coordinate system fields.
- Elevations.
- Drilling dates.
- Operator and field.

### C.2 Trajectory Support
- MD/TVD/TVDSS.
- Inclination/azimuth table.
- Position logs.
- Trajectory validation.

### C.3 Intervals and Perforations
- Interval manager.
- Perforation manager.
- Test intervals.
- Completion intervals.

---

## D. Interpretation Platform

### D.1 Formation Manager Professional
- Formation hierarchy.
- Stratigraphic order.
- Top/base markers.
- Zone linking.

### D.2 Pick Manager
- Manual picks.
- Pick categories.
- Pick validation.
- Import/export picks.

### D.3 Correlation Studio Professional II
- Marker validation.
- Tie-line conflict detection.
- Multi-well section persistence.
- Formation-aware correlation.

### D.4 Crossplot Studio
- GR/RHOB/NPHI/DT crossplots.
- User-defined X/Y/Z.
- Filters.
- Regression.
- Facies coloring.

---

## E. Geological Modeling Professional

### E.1 Structural Framework
- Horizons.
- Zones.
- Layers.
- Stratigraphic framework.
- Model boundary.

### E.2 Facies Modeling
- Facies dictionary.
- Discrete color tables.
- Vertical proportion analysis.
- Horizontal trend maps.
- Facies statistics.
- Simulation-ready data structures.

### E.3 Property Manager
- Store model properties.
- Property metadata.
- Discrete/continuous property types.
- Property templates.
- Property tables.

### E.4 Property Calculator
- IF/CASE formulas.
- Net/Gross.
- Lithology masks.
- Custom properties.

### E.5 Petrophysical Modeling
- POR model.
- PERM model.
- SW/SO/SG models.
- Rock type support.
- Facies-conditioned properties.

### E.6 Fluid Contact Modeling
- OWC.
- GOC.
- GWC.
- Constant contacts.
- Surface contacts.
- Contact set properties.

### E.7 Geometrical Modeling
- Bulk volume.
- Cell height.
- Depth/elevation.
- Above contact.
- Relative depth.
- Net volume.

### E.8 Reservoir Calculator
- OOIP.
- OGIP.
- HCPV.
- Net pay.
- Average POR/PERM/SW.
- Volume summary.

### E.9 Function Studio
- Linear functions.
- Polynomial functions.
- Spline functions.
- Piecewise functions.
- Lookup tables.

### E.10 Variogram Studio
- Experimental variogram.
- Directional variogram.
- Omni variogram.
- Model fitting.
- Variogram library.

---

## F. Data Quality & Validation

### F.1 Data Quality Professional
- Data profiling.
- Missing value analysis.
- Range checks.
- Outlier detection.
- Duplicate detection.

### F.2 Repair Recommendations
- Suggested fixes.
- Safe automatic repair.
- Manual review mode.
- Repair history.

---

## G. Visualization Professional

### G.1 Plot Studio Professional II
- Track presets.
- Template validation.
- Multi-well layouts.
- Export profiles.

### G.2 Grid and Property Preview
- Slice preview.
- I/J/K direction playback.
- Property color maps.
- Animation export.

### G.3 Map and Section Studio
- Well basemap.
- Formation maps.
- Property maps.
- Correlation sections.

---

## H. Data Exchange Professional

### H.1 LAS Export Professional
- Strict LAS writer.
- LAS profile validation.
- Export audit.

### H.2 Tabular Exchange
- CSV/XLSX profiles.
- Column mapping.
- Unit mapping.
- Validation report.

### H.3 Geological Exchange
- GeoJSON.
- SHP/DXF future adapters.
- XYZ grids.
- Surface import/export.

### H.4 Project Exchange
- ZIP package.
- Manifest.
- Data lineage.
- Compatibility check.

---

## I. Reports and Documentation

### I.1 Report Studio Professional II
- Report templates.
- Table blocks.
- Plot blocks.
- Validation blocks.
- Export job manager.

### I.2 Documentation Center
- User guide browser.
- Methodology notes.
- Formula reference.
- Workflow examples.

---

## J. Workflow and Automation

### J.1 Workflow Engine Professional
- Workflow graph.
- Step dependencies.
- Run/pause/resume.
- History.
- Error handling.

### J.2 Batch Processing Professional
- Multi-well operations.
- Batch LAS validation.
- Batch export.
- Batch reporting.

### J.3 Scripting API Professional
- Project storage.
- Script registry.
- Execution logs.
- Safer sandbox.
- API context.

---

## K. Extensibility

### K.1 Plugin SDK Professional
- Extension points.
- Hook registry.
- Plugin templates.
- Plugin validation.

### K.2 Developer Documentation
- API reference.
- Plugin examples.
- Test plugin.

---

## L. Performance and Stabilization

### L.1 Performance Final
- Large LAS profiling.
- DataFrame optimization.
- Cache policies.
- Plot rendering optimization.

### L.2 Regression Testing
- UI regression checklist.
- Import/export regression.
- Calculation regression.

### L.3 Release Candidate 2
- Full preflight.
- Documentation audit.
- Project migration audit.
- Known limitations.

---

## M. Optional / Deferred

### M.1 Licensing and Activation
Status: Deferred / Optional.

May include later:
- License Manager.
- Offline activation.
- Hardware ID.
- Trial mode.

### M.2 AI Assistant
Status: Not planned for current roadmap.

Reason:
- Heavy architecture.
- Requires separate training/configuration.
- Can slow the core product.
- Not necessary before stable engineering core.

### M.3 Cloud and Collaboration
Status: Deferred.
