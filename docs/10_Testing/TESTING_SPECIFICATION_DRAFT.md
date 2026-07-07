# Testing Specification — Draft

## 1. Purpose

This document defines quality expectations for GAS RATIO PRO after Phase II.

## 2. Test Levels

### 2.1 Unit Tests
Required for backend modules and algorithms.

### 2.2 Integration Tests
Required for workflows that connect project storage, import/export and calculation.

### 2.3 Regression Tests
Required for previously fixed bugs and UI/data behavior.

### 2.4 Preflight Checks
Required before release candidates.

## 3. Required Checks After Code Changes

- `python -m compileall` for changed modules or whole project.
- Targeted `pytest` for changed modules.
- Full `pytest` when dependencies are available.
- Documentation update check.

## 4. Priority Test Areas

- LAS creation and validation.
- LAS safe export.
- Curve operations.
- Property calculations.
- Import/export profiles.
- Project storage migration.
- Report manifests.
- Plugin registry validation.

## 5. Acceptance Criteria

A module is ready when:

- Tests exist for core behavior.
- Invalid inputs are tested.
- Persistence is tested.
- Export/manifest behavior is tested if applicable.
- Documentation is updated.
