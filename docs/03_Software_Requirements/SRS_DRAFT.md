# Software Requirements Specification — Draft

Project: GAS RATIO PRO  
Version: Draft for Phase II

## 1. Purpose

This document defines high-level software requirements for GAS RATIO PRO. Detailed module requirements will be expanded in subsequent iterations.

## 2. Functional Requirement Groups

### FR-A Platform Core

- The system shall support modular feature registration.
- The system shall maintain active project context.
- The system shall provide diagnostic and preflight checks.
- The system shall support backward-compatible project metadata where possible.

### FR-B LAS Platform

- The system shall read LAS files.
- The system shall create new LAS files from scratch.
- The system shall edit LAS headers and curves.
- The system shall validate LAS structure before export.
- The system shall never overwrite source LAS files.
- The system shall export edited LAS as a new file.

### FR-C Well Management

- The system shall store well metadata.
- The system shall support grouping and searching wells.
- The system shall support formation and interval metadata.

### FR-D Interpretation

- The system shall support formation, zone, marker and correlation data.
- The system shall validate correlation markers and tie lines.

### FR-E Geological Modeling

- The system shall support facies dictionaries and property metadata.
- The system shall support property calculation and modeling workflows.
- The system shall support fluid contacts and geometrical properties.
- The system shall support reservoir volume calculations.

### FR-F Visualization

- The system shall display LAS plots, crossplots, histograms and property previews.
- The system shall export visual outputs to common formats.

### FR-G Reports

- The system shall build report packages from content blocks.
- The system shall validate report packages before export.

### FR-H Extensibility

- The system shall support plugin metadata and extension points.
- The system shall support scripting only through controlled API boundaries.

## 3. Non-Functional Requirements

- The application shall run locally.
- The application shall support Python 3.11+.
- The application shall prefer transparent and reproducible calculations.
- The application shall minimize UI regressions.
- The application shall handle large LAS files through profiling and optimization.
- The application shall include tests for new backend modules.

## 4. Constraints

- AI Assistant is excluded from current roadmap.
- Licensing/Hardware ID is optional and deferred.
- Source LAS files must not be overwritten.
- Dashboard must not duplicate Sidebar navigation.

## 5. Acceptance Criteria

A requirement is accepted when:

- It is documented.
- It has a clear data model or UI contract.
- It has validation rules.
- It has tests if backend logic changed.
- It does not regress existing workflows.
