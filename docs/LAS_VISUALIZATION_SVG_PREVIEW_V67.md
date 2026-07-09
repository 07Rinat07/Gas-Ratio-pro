# LAS Visualization SVG Preview V67

This increment adds a lightweight renderer-neutral SVG preview to the LAS visualization payload.

## Scope

- The preview is generated in the service layer, not in Streamlit.
- The preview is schematic and compact, intended for Workbench cards and report preview handoff.
- The payload does not include raw DataFrame content.
- Tracks, sampled curves and interval overlays are converted into a small SVG string with export metadata.

## Contract

`payload["preview"]` contains:

- `kind`: `svg_preview`
- `format`: `svg`
- `width` and `height`
- `track_count`
- `curve_count`
- `overlay_count`
- `export_ready`
- `contains_raw_dataframe`
- `svg`

## Architecture note

The UI still consumes only prepared data. It can display `preview.svg` directly, but it must not calculate tracks, scales, intervals or curve normalization.
