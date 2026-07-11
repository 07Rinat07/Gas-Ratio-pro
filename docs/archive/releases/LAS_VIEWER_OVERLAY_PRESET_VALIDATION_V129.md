# LAS Viewer Overlay Preset Validation v129

Version 129 adds compatibility inspection for portable overlay preset packages.

Implemented:

- explicit exchange schema version validation;
- renderer-neutral compatibility validation;
- package inspection report with names, count and warnings;
- legacy warning when the renderer-neutral marker is absent;
- complete package parsing before repository mutation;
- transactional collision handling for the `error` policy.

The importer remains renderer independent and preserves built-in preset protection.
