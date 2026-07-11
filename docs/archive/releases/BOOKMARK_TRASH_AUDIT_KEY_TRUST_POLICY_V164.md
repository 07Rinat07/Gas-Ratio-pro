# Bookmark Trash Audit Key Trust Policy v164

Signed bookmark-trash audit journals now support trust policies for signing keys.

A trusted key may be configured as a plain string/bytes value (legacy mode) or as a policy object:

```python
{
    "key": "secret",
    "not_before_ns": 1_000,
    "expires_at_ns": 2_000,
    "disabled": False,
}
```

The journal export timestamp must fall inside the configured validity window. Disabled keys are rejected. Rotated keyrings and legacy single-key configurations remain compatible.
