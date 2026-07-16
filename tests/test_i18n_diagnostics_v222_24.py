import json
from pathlib import Path
from string import Formatter

from core.internationalization import LocalizationService

ROOT = Path(__file__).resolve().parents[1]
CATALOGS = ROOT / "resources" / "i18n"


def test_v222_24_catalogs_cover_diagnostics_keys_with_placeholder_parity() -> None:
    required = {
        "diagnostics.title",
        "diagnostics.binding",
        "diagnostics.render",
        "diagnostics.no_incidents",
        "diagnostics.section.repository_health",
        "diagnostics.repository_scan_truncated",
        "diagnostics.download_baseline",
        "properties.collapse",
        "properties.restore",
    }
    catalogs = {
        code: json.loads((CATALOGS / f"{code}.json").read_text(encoding="utf-8"))
        for code in ("ru", "kk", "en")
    }
    assert all(required <= set(catalog) for catalog in catalogs.values())
    for key in required:
        placeholders = [
            {field for _, field, _, _ in Formatter().parse(catalogs[code][key]) if field}
            for code in ("ru", "kk", "en")
        ]
        assert placeholders[0] == placeholders[1] == placeholders[2], key


def test_v222_24_kazakh_diagnostics_labels() -> None:
    service = LocalizationService.from_directory(CATALOGS, language="kk")
    assert service("diagnostics.title") == "Әзірлеуші диагностикасы"
    assert service("diagnostics.section.repository_health") == "Репозиторий күйі"
    assert "route.main" in service(
        "diagnostics.binding",
        route="route.main",
        renderer="streamlit",
        provider="workbench",
        loaded=service("common.yes"),
    )


def test_v222_24_workbench_diagnostics_use_i18n_contract() -> None:
    source = (ROOT / "app" / "workbench_renderer.py").read_text(encoding="utf-8")
    required = (
        'i18n("diagnostics.title")',
        'i18n("diagnostics.binding"',
        'i18n("diagnostics.render"',
        'i18n("diagnostics.no_incidents")',
        'i18n("diagnostics.repository_scan_truncated")',
        'i18n("diagnostics.download_baseline")',
        'i18n("properties.collapse")',
        'i18n("properties.restore")',
    )
    assert all(item in source for item in required)
    assert 'with st_module.expander("Developer Diagnostics"' not in source
    assert 'st_module.success("No captured runtime incidents.")' not in source
