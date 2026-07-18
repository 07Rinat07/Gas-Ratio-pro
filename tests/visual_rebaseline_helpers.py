from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from services.visual_rebaseline_registry import VisualRebaselineRegistryService


REGISTRY_PATH = Path(__file__).resolve().parents[1] / "config" / "visual_rebaseline_contracts_v225_7.json"


def assert_visual_rebaseline(nodeid: str, actual: Mapping[str, Any]) -> None:
    VisualRebaselineRegistryService().assert_semantic(REGISTRY_PATH, nodeid, actual)
