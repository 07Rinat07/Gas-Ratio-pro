# LAS Bookmark Trash Audit Import v160

Version v160 adds validated restoration of exported bookmark trash audit journals.

Key guarantees:
- schema and version validation;
- SHA-256 integrity verification;
- event-count consistency checks;
- append and replace import modes;
- idempotent duplicate suppression;
- transactional validation before preferences are updated.
