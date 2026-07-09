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
