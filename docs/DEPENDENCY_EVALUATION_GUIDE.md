# Dependency Evaluation Guide

Evaluate candidate libraries against:

- specification coverage and conformance;
- license compatibility;
- maintenance activity and release history;
- Python/platform support;
- bounded/streaming I/O;
- security posture and parser hardening;
- ability to isolate the dependency behind an adapter;
- deterministic behavior and testability;
- large-file performance;
- Unicode and ru/kk/en presentation requirements;
- export/redistribution obligations.

A library is a replaceable implementation detail. Domain models, Dataset Manifests, QC codes and Workbench contracts must not expose library-specific objects.
