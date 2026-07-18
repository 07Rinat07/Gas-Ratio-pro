from pathlib import Path

from services.visualization_physical_golden_artifacts import (
    CERTIFIED_PHYSICAL_PROFILE_IDS,
    VisualizationPhysicalGoldenArtifactService,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tests" / "fixtures" / "visualization" / "reference_physical_ten_tracks.json"
ARTIFACTS = ROOT / "tests" / "fixtures" / "physical_golden_artifacts"


def test_committed_physical_golden_artifacts_are_complete_and_valid():
    manifest = VisualizationPhysicalGoldenArtifactService().verify(ARTIFACTS)
    assert manifest.ok is True
    assert tuple(profile.profile_id for profile in manifest.profiles) == CERTIFIED_PHYSICAL_PROFILE_IDS
    assert all(profile.page_count == len(profile.pages) for profile in manifest.profiles)
    assert all(page.chrome_primitive_count > 0 for profile in manifest.profiles for page in profile.pages)


def test_regenerated_physical_golden_artifacts_match_approved_visual_baseline(tmp_path):
    service = VisualizationPhysicalGoldenArtifactService()
    approved = service.verify(ARTIFACTS)
    regenerated = service.generate(SOURCE, tmp_path)

    assert regenerated.ok is True
    assert [item.structural_signature() for item in regenerated.profiles] == [
        item.structural_signature() for item in approved.profiles
    ]


def test_four_profiles_have_expected_orientation_and_track_partition():
    manifest = VisualizationPhysicalGoldenArtifactService().verify(ARTIFACTS)
    by_id = {item.profile_id: item for item in manifest.profiles}
    assert by_id["a4_portrait"].page_size == "A4"
    assert by_id["a4_portrait"].orientation == "portrait"
    assert by_id["a4_landscape"].orientation == "landscape"
    assert by_id["a3_portrait"].page_size == "A3"
    assert by_id["a3_landscape"].orientation == "landscape"
    for entry in manifest.profiles:
        flattened = [track for page in entry.pages for track in page.track_ids]
        assert flattened == [f"track.{index:02d}" for index in range(1, 11)]
