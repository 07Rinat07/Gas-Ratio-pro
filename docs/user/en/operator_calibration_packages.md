# Operator calibration packages — revision 1

Stage 5.2 allows operator-owned calibration data to be attached to a project without changing Gas Ratio Pro production formulas.

## Package contents

A supported ZIP contains exactly three root files:

- `manifest.json` — project scope, owner, legal basis, permissions, and SHA-256 records;
- `calibration_registry.json` — acceptance thresholds, sensitivity, and uncertainty policy;
- `calibration_dataset.json` — calibration cases, inputs, parameters, observations, and units.

Directories, extra members, absolute paths, and `..` members are rejected.

## Data-rights requirements

A package is accepted only when:

- `legal_status` is `operator_owned`, `licensed`, or `public_domain`;
- owner and legal basis are present;
- local processing and derivative analysis are allowed;
- the current project is included in `project_scope`;
- the rights have not expired;
- final-report use is declared separately.

Redistribution permission is not required for a local operator-owned package. Such a package stays inside the project and is not included in release archives.

## Import through Professional Print Center

1. Open **Print and Export Center**.
2. Expand **Project operator calibration**.
3. Select the ZIP and choose **Import and validate**.
4. Select the imported version and choose **Set active**.
5. Run **Compare with baseline calibration**.

The panel shows operator, version, legal status, method count, final-report rights, active state, and a shortened fingerprint.

## Immutability and versions

A `package_id + version` pair cannot be reused with a different fingerprint. The source ZIP, registry, dataset, rights fingerprint, and import evidence are stored immutably under the project. Any stored-file modification blocks comparison and export.

## Comparison

A package can be compared with the project baseline or another imported version. Per-method evidence includes pass/fail, RMSE delta, maximum-error delta, uncertainty-envelope delta, and `improved`, `degraded`, `equivalent`, `target_only`, or `reference_only` status.

Comparison never changes formulas and never selects a method automatically.

## Final export

When an active package exists, the export boundary rechecks numerical validation, operator calibration, report policy, current data rights, and the source fingerprint. It creates a versioned project authorization package whose ID, gate IDs, and operator fingerprint are written to the artifact and export history. A diagnostic-only package blocks final PDF/DOCX/HTML before the renderer starts.

## Building a package

```bash
python scripts/build_operator_calibration_package.py \
  --registry calibration_registry.json \
  --dataset calibration_dataset.json \
  --output operator_calibration.zip \
  --package-id operator-field-a \
  --version 1.0.0 \
  --project-id default \
  --operator-name "Example Operator" \
  --organization-id OP-001 \
  --owner "Example Operator" \
  --legal-status operator_owned \
  --legal-basis "Internal approval OP-001" \
  --final-report-use-allowed
```

Use `--redistribution-allowed` only when the operator has explicitly granted redistribution rights.
