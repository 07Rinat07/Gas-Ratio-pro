# Adaptive report layout architecture

Revision 1 · Gas Ratio Pro v225.9

## Purpose

The contract removes the mismatch between physical page orientation and content geometry. A renderer must not use a fixed width when the actual page/frame contract is already available.

## PDF

`reports/presentation_pdf.py` derives `content_width` and `content_height` from the page size and margins. Metadata, tables, and plots receive those values. `_AutoScaleRasterImage` and `_AutoScaleSvgDrawing` constrain content to the real ReportLab frame rather than the former 185/160 mm constants. Raster height is selected using the page aspect ratio.

## DOCX

`reports/presentation_docx.py` obtains usable width from the current section: page width minus left and right margins. Images, metadata tables, document tables, legends, and statistics use that width or proportional column widths.

## HTML

`reports/presentation_html.py` renders Plotly with `responsive=True`, a 100%-width container, and a landscape/portrait CSS class. HTML does not maintain a separate fixed print width.

## Contract and rebaseline

The governing contract ID is `print-readability/v1.1`.

Version 1.1 of `reports/print_readability_contract.py` records:

- `layout_width_policy = available-frame`;
- `plot_aspect_policy = page-aware`;
- `landscape_minimum_frame_utilization = 0.90`;
- `narrative_table_width_policy = full-frame`.

The active semantic baseline is `config/visual_rebaseline_contracts_v225_9.json`. Any geometry/readability-policy change requires a new manifest, SHA-256, and behavioural test.

## Acceptance

`tests/test_report_landscape_frame_utilization_v225_9.py` verifies A3 landscape PDF, DOCX, and HTML output. It confirms that the final track and a wide table reach the right side of the working frame and that the DOCX plot uses the wide section.
