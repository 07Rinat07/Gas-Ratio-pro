from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FORMAT_MARKERS = (
    "LAS 1.x/2.x/3.x",
    "DLIS",
    "LIS79",
    "SEG-Y",
    "GeoPackage",
    "GeoTIFF",
    "GRDECL",
    "RESQML",
    "HDF5",
    "NetCDF",
)


def test_root_readme_reflects_current_and_planned_format_platform():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    for marker in REQUIRED_FORMAT_MARKERS:
        assert marker in text


def test_localized_readmes_cover_current_industry_formats():
    for name in ("README.ru.md", "README.kk.md", "README.en.md"):
        text = (ROOT / name).read_text(encoding="utf-8")
        for marker in ("LAS 1.x/2.x/3.x", "DLIS", "LIS79", "SEG-Y"):
            assert marker in text


def test_root_readme_links_public_format_documentation_without_internal_governance_links():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    target = "docs/user/ru/supported_formats_and_legal_sources.md"
    assert f"]({target})" in text
    assert (ROOT / target).is_file()
    for internal in ("docs/PROJECT_ROADMAP.md", "docs/PROJECT_STATUS.md", "docs/CHANGELOG.md"):
        assert internal not in text
