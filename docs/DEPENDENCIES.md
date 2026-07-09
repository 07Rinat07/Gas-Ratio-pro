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

## Startup dependency rule

Heavy export backends must be imported lazily:

- `reportlab` is required only for PDF export.
- `python-docx` is required only for DOCX export.
- The Streamlit interface, command palette and normal calculations must start without importing PDF/DOCX renderers eagerly.
