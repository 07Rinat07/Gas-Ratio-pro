# LAS Viewer Recent Session Pagination v143

Adds renderer-neutral pagination for recent LAS Viewer sessions.

## Capabilities

- deterministic page slicing after filtering and sorting;
- total item and page counts;
- previous/next navigation flags;
- one-based visible range metadata;
- empty out-of-range pages without exceptions;
- serialized contract for future Workbench adapters.

The service layer owns pagination logic. UI code only requests a page and renders the returned contract.
