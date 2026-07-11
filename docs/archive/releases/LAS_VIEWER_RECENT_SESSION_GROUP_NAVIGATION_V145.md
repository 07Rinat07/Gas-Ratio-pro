# LAS Viewer Recent Session Group Navigation v145

Adds renderer-neutral pagination for grouped recent LAS sessions.

## Contract

`LasViewerRecentSessionGroupPage` contains grouped items, page metadata,
aggregate group and item counts, and deterministic navigation flags.

Filtering and item sorting are applied before grouping. Pagination is applied
after groups are built so a group is never split across pages.
