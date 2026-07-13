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

## PDF Preview compact layout and metrics

- Added optional one-column and compact two-column thumbnail layouts.
- Added measured render duration, source PDF size, total thumbnail size and average thumbnail size.
- Layout selection does not invalidate the raster cache because it changes presentation only.
- Next step: add selective page-range preview and explicit preview-cache cleanup.

## Selective PDF page-range preview and cache cleanup

- Added selection of the first page for a bounded preview range.
- Included the starting page in the preview cache signature to prevent stale page sets.
- Added explicit cleanup of the current project's in-memory PDF thumbnail cache.
- Preserved actual page numbers for both PyMuPDF and `pdftoppm` backends.
- Next step: add previous/next page navigation and optional bounded DPI selection.

## PDF Preview navigation and bounded DPI

- Added previous/next navigation that moves by the selected bounded page group.
- Added optional raster quality control with fixed safe values: 72, 90, 110, 144 and 180 DPI.
- DPI participates in the preview cache signature, so quality changes cannot reuse stale thumbnails.
- Navigation clamps to the first and last valid page group when the exact PDF page count is known.
- Next step: add direct page-jump validation feedback and an optional lightweight preview prefetch for the adjacent page group.

## PDF Preview direct page-jump validation

- Added renderer-neutral validation for direct page jumps.
- Page numbers below 1 and beyond the known document end are normalized safely.
- The UI now explains when a requested page was adjusted and uses the normalized page consistently for cache signatures, rendering and navigation.
- Next step: add optional adjacent-range prefetch without increasing default rendering cost.

## Исправление runtime-сбоя панели экспорта

- Диапазон печати теперь вычисляется до формирования сигнатуры предпросмотра.
- Устранён `UnboundLocalError` для `print_top` и `print_bottom`.
- Виджеты Report Designer больше не задают одновременно значение через Session State и параметр `index`/`value`/`default`.
- Добавлены регрессионные тесты порядка вычислений и наличия кнопки отправки формы.
