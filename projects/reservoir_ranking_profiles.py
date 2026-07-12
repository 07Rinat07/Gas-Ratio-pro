from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from core.reservoir_ranking import ReservoirRankingProfile, ReservoirRankingWeights
from projects.repository import DEFAULT_PROJECT_ID, DEFAULT_PROJECTS_ROOT, safe_project_id

FILE_NAME = "reservoir_ranking_profiles.json"
SCHEMA_VERSION = 1


def _path(root: Path | str, project_id: str) -> Path:
    return Path(root) / safe_project_id(project_id) / FILE_NAME


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_project_ranking_profiles(
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
) -> tuple[ReservoirRankingProfile, ...]:
    path = _path(root, project_id)
    if not path.exists():
        return ()
    raw = json.loads(path.read_text(encoding="utf-8"))
    items = raw.get("profiles", []) if isinstance(raw, dict) else []
    result = []
    for item in items:
        if not isinstance(item, dict):
            continue
        weights_raw = item.get("weights", {}) if isinstance(item.get("weights"), dict) else {}
        result.append(ReservoirRankingProfile(
            profile_id=str(item.get("profile_id") or "").strip(),
            name=str(item.get("name") or "Пользовательский профиль").strip(),
            weights=ReservoirRankingWeights(
                float(weights_raw.get("confidence", 30)),
                float(weights_raw.get("agreement", 30)),
                float(weights_raw.get("completeness", 20)),
                float(weights_raw.get("thickness", 20)),
            ).normalized(),
            reference_thickness=max(0.1, float(item.get("reference_thickness", 20.0))),
            description=str(item.get("description") or ""),
            built_in=False,
        ))
    return tuple(profile for profile in result if profile.profile_id)


def save_project_ranking_profiles(
    profiles: Sequence[ReservoirRankingProfile],
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
) -> Path:
    path = _path(root, project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "project_id": safe_project_id(project_id),
        "updated_at": _utc_now(),
        "profiles": [
            {
                "profile_id": profile.profile_id,
                "name": profile.name,
                "weights": asdict(profile.weights.normalized()),
                "reference_thickness": profile.reference_thickness,
                "description": profile.description,
            }
            for profile in profiles if not profile.built_in
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
