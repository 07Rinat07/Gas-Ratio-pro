# Calculation Engine Specification — Draft

## 1. Purpose

The Calculation Engine provides safe, reproducible calculations for curves, properties, statistics and reservoir workflows.

## 2. Calculation Groups

### 2.1 Curve Calculations
- Arithmetic operations.
- Conditional IF/CASE.
- Moving average.
- Median filter.
- Despike.
- Smoothing.
- Normalization.
- Log transform.
- Gas ratio formulas.

### 2.2 Property Calculations
- Net/Gross.
- Facies mask.
- Lithology mask.
- POR/PERM transforms.
- SW/SO/SG transforms.
- Above-contact filters.

### 2.3 Statistics
- Mean.
- Median.
- Mode.
- Variance.
- Standard deviation.
- P10/P50/P90.
- Histogram.
- Box plot.
- QQ plot.
- Correlation.
- Regression.

### 2.4 Reservoir Calculations
- Bulk rock volume.
- Net rock volume.
- Pore volume.
- HCPV.
- OOIP.
- OGIP.
- Average properties.

### 2.5 Function Studio
- Linear functions.
- Polynomial functions.
- Spline functions.
- Exponential functions.
- Piecewise functions.
- Lookup tables.

## 3. Safety Requirements

- Formula execution must not allow arbitrary unsafe code.
- All formulas must expose input curves/properties.
- All generated curves/properties must preserve lineage.
- Errors must be user-readable.

## 4. Acceptance Criteria

- Formula parser documented.
- Supported functions listed.
- Error handling documented.
- Tests cover basic formulas and invalid expressions.
