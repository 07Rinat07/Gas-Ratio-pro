import json
from pathlib import Path
from string import Formatter

from core.internationalization import LocalizationService

ROOT = Path(__file__).resolve().parents[1]
CATALOGS = ROOT / "resources" / "i18n"


def test_v222_23_catalogs_cover_dashboard_and_status_keys() -> None:
    required = {
        "status.bar.label", "status.ready", "dashboard.title",
        "dashboard.search.placeholder", "dashboard.section.projects",
        "dashboard.metric.wells", "dashboard.footer.version",
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
        assert placeholders[0] == placeholders[1] == placeholders[2]


def test_v222_23_kazakh_dashboard_and_status_labels() -> None:
    service = LocalizationService.from_directory(CATALOGS, language="kk")
    assert service("dashboard.title") == "Жобаның жұмыс кеңістігі"
    assert service("status.ready") == "Дайын"
    assert "2.0.0" in service("dashboard.footer.version", version="2.0.0", time="10:00")


def test_v222_23_renderers_use_i18n_keys() -> None:
    dashboard = (ROOT / "app" / "streamlit_app.py").read_text(encoding="utf-8")
    workbench = (ROOT / "app" / "workbench_renderer.py").read_text(encoding="utf-8")
    assert 'i18n("dashboard.title")' in dashboard
    assert 'i18n("dashboard.search.placeholder")' in dashboard
    assert 'i18n("dashboard.section.projects")' in dashboard
    assert "i18n('status.ready')" in workbench
    assert "● Ready" not in workbench
