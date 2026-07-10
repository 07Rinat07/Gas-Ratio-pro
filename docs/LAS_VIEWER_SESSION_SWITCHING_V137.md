# LAS Viewer Session Switching v137

Version 137 adds a renderer-neutral coordinator for safely switching between
multiple LAS Viewer sessions.

Key guarantees:

- the active session is autosaved before another session is activated;
- failed recovery never replaces the current active session;
- recovery can target a specific project and LAS identifier;
- a fresh session is created lazily only when no compatible autosave exists;
- closing a session can autosave its latest state.

The coordinator contains no UI or rendering logic.
