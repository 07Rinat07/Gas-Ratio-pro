"""Minimal platform-health check for the new UI abstraction boundary."""
from __future__ import annotations
from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    required = (
        ROOT / "ui_platform" / "theme" / "tokens.py",
        ROOT / "ui_platform" / "theme" / "engine.py",
        ROOT / "ui_platform" / "components" / "contracts.py",
        ROOT / "ui_platform" / "adapters" / "streamlit.py",
    )
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    if missing:
        print("UI PLATFORM: FAIL")
        print("Missing:", ", ".join(missing))
        return 1
    for path in required:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    print("UI PLATFORM: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
