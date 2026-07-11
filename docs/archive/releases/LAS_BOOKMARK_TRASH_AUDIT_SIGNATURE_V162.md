# LAS Bookmark Trash Audit Signature v162

Portable bookmark trash audit journals can now be signed with HMAC-SHA256.

The export contract accepts a signer identifier and secret key. Import and merge operations can require signatures and verify them against an explicit trusted signer registry. Unsigned legacy exports remain supported unless strict signature verification is enabled.

All source journals are validated before a merge changes persisted state, preserving transactional behavior.
