# Audit verification report comparison v169

Version 169 adds deterministic comparison of two validated signature verification report exports.

The comparison contract reports added, removed, and unchanged events together with total, accepted, and rejected deltas. Both inputs are integrity-checked before comparison, and repository state is never modified.
