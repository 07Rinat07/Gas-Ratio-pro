# LAS bookmark audit key rotation v163

Signed bookmark-trash audit journals now support key identifiers and multiple trusted keys per signer.

- `key_id` is stored in new HMAC-SHA256 signatures.
- A signer can be configured with a keyring `{key_id: key}`.
- Legacy single-key trust configuration remains supported.
- Revoked key identifiers can be rejected explicitly during import or merge.
- Unknown, missing, empty, or revoked rotated keys fail before journal state is modified.
