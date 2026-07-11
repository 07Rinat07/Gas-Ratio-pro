# LAS Viewer Overlay Preset Backup v131

Version 131 adds a renderer-neutral backup lifecycle for LAS Viewer overlay preset repositories.

Implemented capabilities:

- atomic ZIP backup creation;
- manifest with payload size and SHA-256 checksum;
- backup validation before loading;
- atomic restoration to the JSON repository file;
- safe custom preset deletion with a recovery backup;
- builtin preset deletion protection.

The service is independent from UI and renderers.
