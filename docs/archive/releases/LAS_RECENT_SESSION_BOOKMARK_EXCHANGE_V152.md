# LAS Recent Session Bookmark Exchange v152

Version 152 adds a renderer-neutral JSON contract for exporting and importing LAS recent-session bookmarks between workspaces.

Features:
- atomic JSON export;
- portable session matching by session key, project/LAS identity, or filename;
- conflict policies: skip, overwrite, error;
- transactional error handling;
- import diagnostics for conflicts and missing sessions.
