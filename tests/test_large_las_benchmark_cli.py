from __future__ import annotations

import json
from pathlib import Path

import scripts.run_large_las_benchmark as benchmark_cli


class _PassingReport:
    passed = True

    def to_dict(self):
        return {"schema": "visualization.performance.acceptance", "passed": True}

    def to_markdown(self):
        return "## Large-LAS performance gates\n\n**Status:** PASS\n"


def test_cli_writes_json_markdown_and_github_summary(tmp_path, monkeypatch) -> None:
    json_path = tmp_path / "report.json"
    markdown_path = tmp_path / "report.md"
    github_path = tmp_path / "github-summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(github_path))
    monkeypatch.setattr(benchmark_cli, "run_visualization_benchmark_suite", lambda cases, gate: _PassingReport())

    exit_code = benchmark_cli.main(
        [
            "--points", "100",
            "--curves", "2",
            "--output", str(json_path),
            "--summary-output", str(markdown_path),
            "--github-summary",
        ]
    )

    assert exit_code == 0
    assert json.loads(json_path.read_text(encoding="utf-8"))["passed"] is True
    assert "Status:** PASS" in markdown_path.read_text(encoding="utf-8")
    assert "Status:** PASS" in github_path.read_text(encoding="utf-8")
