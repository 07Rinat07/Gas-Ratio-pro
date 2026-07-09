from __future__ import annotations

import json
import subprocess
import sys

from scripts.export_smoke import build_sample_export_frame, run_export_smoke


def test_sample_export_frame_contains_multilingual_text() -> None:
    frame = build_sample_export_frame()
    text = " ".join(frame["interpretation"].astype(str).tolist())

    assert "Газовая" in text
    assert "Мұнай" in text


def test_run_export_smoke_creates_bundle_files(tmp_path) -> None:
    summary = run_export_smoke(tmp_path)

    assert summary["ok"] is True
    for key in ("html", "pdf", "docx", "manifest"):
        assert tmp_path in __import__("pathlib").Path(summary[key]).parents or __import__("pathlib").Path(summary[key]).parent == tmp_path
        assert __import__("pathlib").Path(summary[key]).exists()


def test_export_smoke_script_prints_json(tmp_path) -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/export_smoke.py", "--output-dir", str(tmp_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["ok"] is True
    assert payload["profile"] == "engineering"
