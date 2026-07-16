import json

from services.user_locale_preference_service import UserLocalePreferenceService


def test_locale_preference_round_trip_and_normalization(tmp_path):
    service = UserLocalePreferenceService(tmp_path / "locale.json")
    assert service.load() == "ru"
    assert service.save("kk-KZ") == "kk"
    assert service.load() == "kk"
    payload = json.loads(service.path.read_text(encoding="utf-8"))
    assert payload["language"] == "kk"
    assert payload["schema"] == service.SCHEMA


def test_locale_preference_rejects_unknown_and_malformed_payload(tmp_path):
    path = tmp_path / "locale.json"
    path.write_text('{"schema":"wrong","language":"en"}', encoding="utf-8")
    service = UserLocalePreferenceService(path)
    assert service.load() == "ru"
    assert service.save("../../etc/passwd") == "ru"
    assert service.load() == "ru"


def test_locale_preference_snapshot_is_json_serializable(tmp_path):
    service = UserLocalePreferenceService(tmp_path / "locale.json")
    service.save("en_US")
    snapshot = service.snapshot()
    assert snapshot["language"] == "en"
    json.dumps(snapshot)


def test_workbench_localization_context_persists_selected_language(tmp_path, monkeypatch):
    from core.command_framework import WorkbenchCommandRegistry
    from app import workbench_renderer

    class FakeStreamlit:
        def selectbox(self, _label, *, options, index, format_func, key, help):
            assert tuple(options) == ("ru", "kk", "en")
            assert format_func("kk") == "Қазақша"
            assert key == "workbench_language_selector"
            assert help
            return "kk"

    locale_path = tmp_path / "locale.json"
    monkeypatch.setattr(workbench_renderer, "_USER_LOCALE_PATH", locale_path)
    state = {}
    registry = WorkbenchCommandRegistry(state)
    i18n = workbench_renderer._localization_context(registry, FakeStreamlit())

    assert i18n.language == "kk"
    assert i18n("menu.project") == "Жоба"
    assert state[workbench_renderer.WORKBENCH_LANGUAGE_KEY] == "kk"
    assert UserLocalePreferenceService(locale_path).load() == "kk"
