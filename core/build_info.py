"""Immutable runtime build identity for production diagnostics.

The identity is deliberately independent from Streamlit session state.  It lets
operators verify that the browser is connected to the expected extracted build
and not to an older process still listening on the same port.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUILD_VERSION = "v222.54"
BUILD_CHANNEL = "stable"


@dataclass(frozen=True, slots=True)
class RuntimeBuildInfo:
    version: str
    channel: str
    project_root: str
    entry_point: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def runtime_build_info() -> RuntimeBuildInfo:
    return RuntimeBuildInfo(
        version=BUILD_VERSION,
        channel=BUILD_CHANNEL,
        project_root=str(PROJECT_ROOT),
        entry_point=str(PROJECT_ROOT / "app" / "streamlit_app.py"),
    )
