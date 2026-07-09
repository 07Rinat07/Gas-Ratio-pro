# Dependencies

Gas Ratio Pro uses optional renderer backends for professional exports.

## PDF export

PDF export uses `reportlab` and is listed in `requirements.txt`.

If Streamlit fails with:

```text
ModuleNotFoundError: No module named 'reportlab'
```

install dependencies from the project root:

```bash
python -m pip install -r requirements.txt
```

The application must not fail on startup only because the PDF backend is missing. PDF export should show a clear runtime message if the dependency is not installed.

## DOCX export

DOCX export uses `python-docx` and is listed in `requirements.txt`.
The import name inside Python is `docx`, but the package installation name is `python-docx`.

If Streamlit fails with:

```text
ModuleNotFoundError: No module named 'docx'
```

install dependencies from the project root:

```bash
python -m pip install -r requirements.txt
```

or install the package directly:

```bash
python -m pip install python-docx
```

The application must not fail on startup only because the DOCX backend is missing. DOCX export should show a clear runtime message if the dependency is not installed.


## Export smoke QA

Use the reproducible export smoke command before handing a build to users:

```bash
python scripts/export_smoke.py --output-dir tmp/export-smoke
```

The command generates one multilingual engineering report bundle: HTML, PDF, DOCX and a bundle manifest. It intentionally contains Russian and Kazakh text so missing PDF Unicode fonts are detected before a real engineering report is exported.

## Startup dependency rule

Heavy export backends must be imported lazily:

- `reportlab` is required only for PDF export.
- `python-docx` is required only for DOCX export.
- The Streamlit interface, command palette and normal calculations must start without importing PDF/DOCX renderers eagerly.

Preflight diagnostics must report professional export readiness without failing application startup. Missing `reportlab`, `docx` or Unicode PDF fonts are warnings, not startup errors. The concrete export command must still raise a clear runtime message when a required backend or font is absent.

## PDF Unicode fonts

PDF export requires a Unicode TrueType/OpenType font. On Windows the renderer
uses standard system fonts such as Arial, Segoe UI or Calibri. On Linux it uses
DejaVu Sans or Noto Sans when available. For custom deployments set
`GAS_RATIO_PRO_PDF_FONT` and `GAS_RATIO_PRO_PDF_FONT_BOLD` to valid `.ttf` files.
This is required for Russian, Kazakh and English multilingual reports.
