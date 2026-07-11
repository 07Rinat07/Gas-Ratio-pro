# Visualization Interaction Journal v103

Adds a renderer-neutral append-only interaction journal for viewport, cursor and selection events.

Capabilities:

- deterministic event sequence;
- revision tracking and no-op detection;
- JSON-safe serialization;
- replay into a fresh interaction session;
- optional cursor-event skipping when a render model is unavailable;
- model resolver hook for workspace restore.

The journal does not duplicate interaction logic. Events are replayed through the existing dispatcher and session services.
