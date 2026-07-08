# Architecture Review and Core LTS Freeze Checklist

## Purpose

This document defines the mandatory architecture review gate after Sprint 1.5 and before Sprint 2 Workspace Framework. The goal is to freeze the verified core platform contracts so Sprint 2 can extend the application without changing the foundation unexpectedly.

## Review Scope

The review covers the stable core layers:

- UI boundary
- Service Layer
- Repository Layer
- Storage Lifecycle
- Application State Controller
- Project Database and index files
- Delete workflow
- Release candidate checks

Sprint 2 functionality must not start until every required gate in this document is accepted.

## Architecture Principles

The following principles remain mandatory for all new and existing modules:

1. UI calls Service Layer only.
2. Service Layer coordinates business workflows.
3. Repository Layer owns persistent records and file metadata.
4. Storage Lifecycle owns filesystem cleanup, resource disposal, cache cleanup and index synchronization.
5. Application-owned UI state is accessed through `ApplicationStateController`.
6. Destructive operations are routed through `DeleteEngine` or an approved service method.
7. New modules must provide Repository, Service, Manager, Tests and Documentation.

## Core LTS Freeze Gates

### 1. Runtime Gate

Required result: application startup and core workflows must remain operational.

Acceptance criteria:

- application imports successfully;
- dashboard shell renders without direct storage mutation;
- project creation works through `ProjectManagerService`;
- recent project state is handled through the application state controller;
- no startup regression is introduced.

### 2. Service Boundary Gate

Required result: UI code must not bypass the service layer for core workflows.

Acceptance criteria:

- project operations go through `ProjectManagerService`;
- dataset operations go through `DatasetManagerService`;
- LAS operations go through `LasManagerService`;
- well operations go through `WellManagerService`;
- export operations go through `ExportManagerService`.

### 3. Repository Boundary Gate

Required result: repository code remains the persistence boundary.

Acceptance criteria:

- records are created, listed and deleted through repositories;
- project indexes are updated through approved index helpers;
- UI modules do not directly rewrite repository files;
- deleted data does not reappear after restart.

### 4. Storage Lifecycle Gate

Required result: all cleanup paths use the Storage Lifecycle framework.

Acceptance criteria:

- dataset deletion clears files and index entries;
- LAS deletion clears files and index entries;
- well deletion clears versions and references;
- export deletion clears export files and index entries;
- project deletion uses controlled cleanup;
- cache and resources are cleaned consistently.

### 5. Application State Gate

Required result: application-owned state has a single access boundary.

Acceptance criteria:

- direct `st.session_state` access is limited to the controller factory boundary;
- feature modules use `ApplicationStateController` helpers;
- state initialization is idempotent;
- project context, graph settings, LAS editor state and interpretation state use controller helpers;
- regression tests protect the boundary.

### 6. Documentation Gate

Required result: architecture decisions are traceable.

Acceptance criteria:

- Sprint 1.5 stabilization notes are present;
- Storage Lifecycle documentation is present;
- Service compatibility documentation is present;
- Application State final audit is present;
- this Core LTS freeze checklist is present.

### 7. Validation Gate

Required result: the project passes automated quality checks.

Acceptance criteria:

- `compileall` passes;
- full `pytest` passes;
- integration audit passes;
- release candidate audit reports no required errors;
- no known blocking regression remains open.

## Core LTS Decision

Core LTS can be marked as ready only when all gates are accepted. After the freeze:

- existing core contracts must be treated as stable;
- Sprint 2 may add modules on top of the core;
- core changes require explicit architecture-review justification;
- breaking changes require migration notes and compatibility tests.

## Sprint 2 Entry Criteria

Sprint 2 Workspace Framework may start only after:

1. Architecture Review is accepted.
2. Core LTS Freeze is accepted.
3. The latest release candidate passes validation.
4. The project progress file points to Sprint 2 as the next implementation stage.

## Review Status

Current status: ready for Architecture Review.

Next action: run final validation, accept Core LTS Freeze, then start Sprint 2 Workspace Framework.
