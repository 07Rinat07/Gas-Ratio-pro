# V71 Visualization Asset Index

## Completed

- Added a machine-readable visualization asset index for bundle exports.
- The index is written beside SVG previews under `assets/` and records asset id, role, format, relative path, size, SHA-256 digest and renderer metadata.
- Bundle manifests now reference the visualization asset index through `files.visualization_asset_index` and `visualization.asset_index`.
- Release export QA now reports a compact visualization asset summary without rebuilding LAS plots.
- Bundle validation checks the index file together with HTML, PDF, DOCX, their manifests and visualization SVG assets.

## Engineering value

The export bundle now has a deterministic asset catalogue that external tools, CI checks and future PDF/DOCX renderers can consume without scanning the filesystem or parsing embedded HTML. This keeps Visualization Engine outputs auditable and renderer-neutral.

## Next step

Use indexed SVG visualization assets as concrete renderer inputs for PDF/DOCX output instead of placeholder-only preview handling.
