from pathlib import Path
import re

from core.build_info import BUILD_CHANNEL, BUILD_VERSION, PROJECT_ROOT, runtime_build_info


def test_current_build_identity_is_consistent_across_runtime_and_deployment_metadata():
    assert re.fullmatch(r"v\d+\.\d+", BUILD_VERSION)
    assert BUILD_CHANNEL in {"release-candidate", "stable"}
    assert Path(runtime_build_info().project_root).resolve() == PROJECT_ROOT.resolve()
    deployment = (PROJECT_ROOT / "DEPLOYMENT_BUILD.txt").read_text(encoding="utf-8").strip()
    assert deployment == f"Gas Ratio Pro {BUILD_VERSION}"


def test_runtime_entry_point_exists_in_current_project():
    info = runtime_build_info()
    entry = Path(info.entry_point)
    assert entry.exists()
    assert PROJECT_ROOT in entry.parents
