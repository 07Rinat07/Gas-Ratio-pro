# Adaptive engineering report layout

Revision 1 · Gas Ratio Pro v225.9

## What changed

Page orientation and content size now share one physical contract. In A3 landscape, plots, labels, tables, and narrative sections use the actual printable frame instead of the former fixed widths designed for a smaller page.

## Default behaviour

- the selected A4/A3 orientation is applied to the real PDF page and DOCX section;
- a plot is scaled to the available width and height while preserving its aspect ratio;
- metadata, legends, statistics, and narrative tables use the full working width;
- HTML plots use a responsive 100%-width container;
- minimum font, line, and track sizes remain protected by the physical profile;
- page-aware preview and final export use the same geometry.

## A3 landscape result

An engineering panel no longer appears as a narrow column on the left side of an A3 landscape sheet. It uses almost the entire printable width and height. Narrative reports and wide tables also span the available frame, eliminating the unjustified empty area on the right.

## Supported formats

- **PDF:** dimensions come from the actual ReportLab frame;
- **DOCX:** width comes from the current section settings;
- **HTML:** a responsive 100%-width container is used;
- **SVG/PNG preview:** page-aware physical geometry is preserved.

## Verification

The `print-readability/v1.1` contract requires the `available-frame` policy, a page-aware aspect ratio, and at least 90% permitted landscape-frame utilisation for wide content. This behaviour may change only through a controlled visual rebaseline.
