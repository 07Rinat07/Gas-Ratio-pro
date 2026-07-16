import json
from pathlib import Path
from string import Formatter

from core.internationalization import LocalizationService

ROOT = Path(__file__).resolve().parents[1]
CATALOGS = ROOT / "resources" / "i18n"


def test_v222_22_workbench_catalogs_have_matching_placeholders() -> None:
    catalogs = {code: json.loads((CATALOGS / f"{code}.json").read_text(encoding="utf-8")) for code in ("ru", "kk", "en")}
    keys = set(catalogs["ru"])
    assert all(set(catalog) == keys for catalog in catalogs.values())
    for key in keys:
        placeholders = []
        for code in ("ru", "kk", "en"):
            text = catalogs[code][key]
            placeholders.append({field for _, field, _, _ in Formatter().parse(text) if field})
        assert placeholders[0] == placeholders[1] == placeholders[2], key


def test_v222_22_kazakh_workbench_navigation_strings() -> None:
    service = LocalizationService.from_directory(CATALOGS, language="kk")
    assert service("menu.file.open_project") == "Жобаны ашу"
    assert service("project.explorer.no_results") == "Жоба нысандары табылмады."
    assert service("workspace.quick.open_reports") == "Есептерді ашу"
    assert "ERR-42" in service("error.workspace_open", error_id="ERR-42")


def test_v222_22_renderer_uses_translation_keys_for_migrated_states() -> None:
    source = (ROOT / "app" / "workbench_renderer.py").read_text(encoding="utf-8")
    required = (
        "menu.file.open_project",
        "menu.project.no_recent",
        "project.explorer.search.placeholder",
        "project.explorer.matches",
        "workspace.empty.text",
        "workspace.quick.open_reports",
        "properties.confirmation.help",
        "error.workspace_open",
    )
    assert all(key in source for key in required)
    assert 'st_module.info("No project objects found.")' not in source
    assert 'st_module.markdown("#### Действия")' not in source
