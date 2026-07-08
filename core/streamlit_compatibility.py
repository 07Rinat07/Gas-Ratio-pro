from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StreamlitCompatibilityFinding:
    """Single Streamlit compatibility finding."""

    file: str
    line: int
    detail: str


@dataclass(frozen=True)
class StreamlitCompatibilityReport:
    """Compatibility report for deprecated Streamlit APIs used by the project."""

    findings: tuple[StreamlitCompatibilityFinding, ...]

    @property
    def ok(self) -> bool:
        return not self.findings

    def as_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "findings": [
                {"file": finding.file, "line": finding.line, "detail": finding.detail}
                for finding in self.findings
            ],
        }


DEPRECATED_WIDTH_KEYWORD = "use_container_width"
DEPRECATED_WIDTH_DETAIL = "Deprecated Streamlit width argument. Use width='stretch' or width='content'."


def _relative(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _scan_file(path: Path, root: Path) -> tuple[StreamlitCompatibilityFinding, ...]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (SyntaxError, UnicodeDecodeError):
        return ()

    findings: list[StreamlitCompatibilityFinding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for keyword in node.keywords:
            if keyword.arg == DEPRECATED_WIDTH_KEYWORD:
                findings.append(
                    StreamlitCompatibilityFinding(
                        file=_relative(path, root),
                        line=getattr(keyword, "lineno", getattr(node, "lineno", 0)),
                        detail=DEPRECATED_WIDTH_DETAIL,
                    )
                )
    return tuple(findings)


def scan_streamlit_deprecations(root: Path | str) -> StreamlitCompatibilityReport:
    """Find deprecated Streamlit API keyword usage in Python call syntax.

    Sprint 1.5 keeps runtime stable before Sprint 2.  Streamlit warns that the
    old width keyword should be replaced by the newer ``width`` argument.  This
    AST-based check prevents the deprecated call keyword from returning without
    flagging documentation or test text that merely mentions the old name.
    """

    root_path = Path(root)
    findings: list[StreamlitCompatibilityFinding] = []
    for path in sorted(root_path.rglob("*.py")):
        if any(part in {".venv", "__pycache__", ".pytest_cache"} for part in path.parts):
            continue
        findings.extend(_scan_file(path, root_path))
    return StreamlitCompatibilityReport(findings=tuple(findings))
