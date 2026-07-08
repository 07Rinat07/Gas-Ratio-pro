# Sprint 1.5 — Integration & Stabilization

## Current pass

This pass starts the stabilization phase after Sprint 1 service and storage refactoring.
The goal is not to add engineering features, but to make the existing platform layers work as one system.

## Completed in this pass

- Verified full Python compilation with `python -m compileall -q .`.
- Integrated LAS deletion with the Storage Lifecycle Framework.
- Routed Dataset Manager `las` section deletion through `LasManagerService`.
- Added targeted regression tests for LAS lifecycle deletion and Dataset Manager LAS section routing.

## Storage lifecycle rule

All destructive operations must follow this chain:

```text
UI
↓
Service
↓
DeleteEngine
↓
ResourceManager / FileHandleManager / CacheManager
↓
Repository / Manifest update
↓
IndexManager
↓
UI refresh
```

## Known unrelated test failures before full stabilization

The full test suite still contains legacy failures in dashboard/documentation smoke tests and older well repository compatibility tests. They are tracked for later Sprint 1.5 passes and are not caused by the LAS lifecycle integration in this pass.

## Next pass

Continue Sprint 1.5 with Project/Well/Export runtime verification and legacy test reconciliation.
