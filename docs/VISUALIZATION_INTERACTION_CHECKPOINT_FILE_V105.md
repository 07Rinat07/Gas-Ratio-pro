# Visualization Interaction Checkpoint File v105

Version 105 adds durable UTF-8 JSON persistence for interaction checkpoint stores.

## Properties

- deterministic JSON serialization;
- SHA-256 integrity verification;
- atomic replacement through a temporary file and `os.replace`;
- automatic parent-directory creation;
- explicit schema and version validation;
- restoration of bounded checkpoint stores between application runs.

The persistence service is renderer-neutral and contains no UI logic.
