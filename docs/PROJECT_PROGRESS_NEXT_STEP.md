# Next Step

Completed in v37: Workspace Session Manager for Modern UI.

The application can now capture, save, load and restore a lightweight workspace session: active project, well, LAS, workspace, selected intervals, active report, active plot, recent exports and window layout.

Next recommended increment: Modern Workspace shell foundation — Project Explorer, central workspace area, toolbar/status boundary and integration points for session restore/reset/export actions.

## PDF Preview foundation

- Added bounded raster preview generation for already-rendered PDF artifacts.
- The service prefers PyMuPDF and falls back to local `pdftoppm`.
- Preview rendering is limited to 1–12 pages and 72–180 DPI.
- Temporary source and page files are isolated outside project `data/` and removed automatically.
- Next step: connect the service to the Report Designer UI and cache previews by report signature.


## PDF Preview UI integration

- Connected bounded PDF page thumbnails to the Professional Export panel.
- Preview is generated only on explicit request after a matching PDF artifact exists.
- Thumbnails are cached by the actual PDF bytes, export request signature, page limit and DPI.
- Cache is invalidated when a new export artifact is completed or export settings are reset.
- The UI keeps download available when no local rasterizer is installed.
- Next step: add an optional compact two-column thumbnail layout and preview performance metrics.
