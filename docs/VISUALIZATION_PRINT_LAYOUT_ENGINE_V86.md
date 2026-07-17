# Visualization Print Layout Engine — physical profiles and pagination

## Purpose

`VisualizationPrintLayoutEngine` converts the existing renderer-neutral visualization layout into physical pages. It does not read LAS rows or recalculate curves, axes, intervals or engineering scales.

## Shared profiles

Canonical profiles live in `core/physical_print_profiles.py`:

| Profile | Font floor | Line floor | Track floor | Max tracks/page |
|---|---:|---:|---:|---:|
| A4 portrait | 7.5 pt | 0.50 pt | 28 mm | 4 |
| A4 landscape | 7.5 pt | 0.50 pt | 28 mm | 6 |
| A3 portrait | 8.0 pt | 0.55 pt | 30 mm | 6 |
| A3 landscape | 8.0 pt | 0.55 pt | 30 mm | 9 |

A2/A1 remain supported with compatible larger-sheet profiles. Explicit overrides may increase readability floors or reduce page capacity, but cannot lower the canonical floor.

## Pagination contract

`visualization.print.layout` version 2 contains:

- `profile_id` and physical readability floors;
- physical page and printable bounds in points;
- per-page content and source bounds;
- ordered `track_ids` for every page;
- reserved legend region and page count metadata.

The paginator groups contiguous tracks greedily. It starts a new page before a group would exceed profile capacity or reduce a track below its physical width floor. Each track is covered once, in source order. The depth domain, curve scales and overlays are never recomputed.

## Renderer behavior

- PDF iterates the shared page list and emits the same physical number of pages.
- SVG exposes `page_svgs`; every page uses point dimensions and the same page transform.
- PNG rasterizes `page_svgs` at explicit DPI and publishes the same geometry signature.
- HTML/PDF/DOCX report renderers embed all prepared pages.
- Font and stroke floors are applied after the page transform, not only in source-pixel space.

## Pipeline position

```text
Domain Model → Scene → Layout → Axis/Grid → Track Model
             → Label/Legend → Print Layout → Render Model → PDF/SVG/PNG
```

The next increment should make Professional Print Center consume one page-aware asset package and add shared page headers, numbering and repeated legend primitives.
