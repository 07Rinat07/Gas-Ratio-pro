# LAS bookmark backup v154

Version 154 adds portable ZIP backup and restore for recent LAS session bookmarks.

The archive contains only `manifest.json` and `bookmarks.json`. The manifest stores the schema version and SHA-256 digest of the bookmark payload. Restore validates archive members, contract compatibility, payload checksum, and then reuses the transactional bookmark import path with the selected conflict policy.
