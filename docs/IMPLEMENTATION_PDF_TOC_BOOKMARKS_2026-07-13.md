# PDF Table of Contents and Bookmarks

Implemented in the renderer-neutral PDF pipeline.

- `PresentationPdfOptions.include_table_of_contents`
- `PresentationPdfOptions.include_pdf_bookmarks`
- multi-pass ReportLab document build for final page numbers
- PDF outline entries for report title and headings
- Brief mode disables navigation pages; Standard and Full Engineering enable them

Verification: 62 reporting/export tests passed.
