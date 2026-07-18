"""Regenerate approved A4/A3 physical golden artifacts.

Run only when an intentional visual or physical layout change has been reviewed.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.visualization_physical_golden_artifacts import VisualizationPhysicalGoldenArtifactService

SOURCE = ROOT / "tests" / "fixtures" / "visualization" / "reference_physical_ten_tracks.json"
OUTPUT = ROOT / "tests" / "fixtures" / "physical_golden_artifacts"

if __name__ == "__main__":
    manifest = VisualizationPhysicalGoldenArtifactService().generate(SOURCE, OUTPUT)
    if not manifest.ok:
        raise SystemExit("physical golden artifact generation failed")
    print(f"Generated {len(manifest.profiles)} certified physical profiles in {OUTPUT}")
