# LAS Platform Specification — Draft

Project: GAS RATIO PRO  
Priority: Highest after Phase II documentation

## 1. Purpose

LAS Platform is the core subsystem for reading, creating, editing, validating, calculating and exporting LAS files.

## 2. Current Gap

The current LAS Editor foundation supports several editing operations. Phase II implementation has now started closing the largest gap: LAS creation from scratch. Full professional editing workflows are still being expanded incrementally.

## 3. Required Modules

### 3.1 LAS Creation Wizard

Status: **Implemented backend foundation in Phase II B.1**.

The wizard must allow creation of a valid LAS file from scratch.

Required inputs:

- LAS version/profile.
- Well name.
- UWI/API.
- Field.
- Company/operator.
- Start depth.
- Stop depth.
- Step.
- Null value.
- Depth unit.
- Default curve set.

Generated sections:

- `~Version`
- `~Well`
- `~Curve`
- `~Parameter`
- `~Other`
- `~Ascii`

### 3.2 Header Editor

Must support editing:

- Version section.
- Well section.
- Curve section.
- Parameter section.
- Other section.

### 3.3 Curve Manager

Must support:

- Add curve.
- Delete curve.
- Rename curve.
- Reorder curve.
- Change unit.
- Change description.
- Assign category.
- Apply alias.
- Validate mnemonic uniqueness.

### 3.4 ASCII Data Editor

Must support:

- View table.
- Edit values.
- Insert row.
- Delete row.
- Insert depth sample.
- Delete depth sample.
- Replace nulls.
- Bulk fill.

### 3.5 LAS Validator

Must check:

- Mandatory sections.
- Required well metadata.
- Curve count vs ASCII columns.
- Depth monotonicity.
- Duplicate depth values.
- Null value consistency.
- Invalid units.
- Empty curve mnemonic.
- Unsafe overwrite attempt.

### 3.6 Safe LAS Writer

Rules:

- Never overwrite source file.
- Always save edited LAS under a new name.
- Write export manifest.
- Attach validation report.

### 3.7 Curve Calculator

Supported operations:

- Arithmetic formulas.
- Conditional formulas.
- Moving average.
- Median filter.
- Despike.
- Smoothing.
- Normalization.
- Gas ratios.

### 3.8 Import External Curves

Supported sources:

- CSV.
- XLSX.

Required behavior:

- Select depth column.
- Select imported curves.
- Match/resample depth.
- Detect conflicts.
- Create new LAS version.

## 4. Acceptance Criteria

The LAS Platform Professional milestone is complete when:

- A user can create a valid LAS from scratch.
- A user can add/edit/delete curves.
- A user can edit header sections.
- A user can edit ASCII values safely.
- A user can validate LAS before export.
- A user can export only to a new LAS file.
- Unit tests cover validator, writer, creation wizard backend and curve operations.


## 5. Phase II B.1 Implementation Notes

Implemented backend capabilities:

- `LasCreationSpec` for wizard input.
- `LasCurveSpec` for curve definition.
- Built-in templates: empty, mud gas and petrophysics.
- Depth grid generation from start/stop/step.
- Mandatory LAS sections: `~Version`, `~Well`, `~Curve`, `~Parameter`, `~ASCII`.
- Safe in-memory LAS text and bytes generation.
- Mnemonic and unit normalization.
- Basic validation issues for depth range, depth step, duplicate curves and required sections.
- Curve add/delete helpers that protect the depth curve from deletion.

Remaining LAS Platform work:

- UI wizard integration.
- Full header editor.
- ASCII table editor.
- Strict LAS profile validation.
- Curve import from CSV/XLSX into created LAS files.
- Formula-based Curve Calculator.
- LAS Quality Control Professional.
