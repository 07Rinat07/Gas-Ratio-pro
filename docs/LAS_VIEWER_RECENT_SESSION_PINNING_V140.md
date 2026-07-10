# LAS Viewer recent session pinning v140

Version v140 adds persistent pinning and deterministic ordering for recent LAS Viewer sessions.

Pinned sessions are listed before unpinned sessions. Items inside each group remain sorted by modification time and filename. Pin preferences are stored atomically in a renderer-neutral JSON file beside the autosave repository and are removed when the related session is deleted.
