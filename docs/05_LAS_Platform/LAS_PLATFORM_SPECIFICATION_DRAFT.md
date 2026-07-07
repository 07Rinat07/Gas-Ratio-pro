# LAS Platform Specification — Draft

Project: GAS RATIO PRO  
Priority: Highest after Phase II documentation

## 1. Purpose

LAS Platform is the core subsystem for reading, creating, editing, validating, calculating and exporting LAS files.

## 2. Current Gap

The current LAS Editor foundation supports several editing operations, but it does not yet provide full professional LAS creation and complete editing workflows.

## 3. Required Modules

### 3.1 LAS Creation Wizard

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
