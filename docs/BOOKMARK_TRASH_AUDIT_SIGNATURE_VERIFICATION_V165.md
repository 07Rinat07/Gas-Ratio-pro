# Bookmark Trash Audit Signature Verification v165

Version 165 adds persistent renderer-neutral audit records for signed journal verification.

Recorded fields include source filename, operation, signer ID, key ID, acceptance status, timestamp, and the exact validation failure reason. Import and merge workflows automatically write verification audit records. A public verification method allows Workbench and diagnostics layers to inspect a journal without importing it.
