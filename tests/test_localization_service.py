import json
from pathlib import Path

import pytest

from core.application_service_container import application_service_container
from core.internationalization import LocalizationService, normalize_language
from services.localization_application_service import LocalizationApplicationService


CATALOGS = Path(__file__).resolve().parents[1] / "resources" / "i18n"


def test_language_normalization_is_allow_listed() -> None:
    assert normalize_language("kk-KZ") == "kk"
    assert normalize_language("en_US") == "en"
    assert normalize_language("../../etc/passwd") == "ru"


def test_three_catalogs_are_complete_and_aligned() -> None:
    service = LocalizationService.from_directory(CATALOGS, language="kk")
    snapshot = service.snapshot()

    assert [item["code"] for item in snapshot["supported_languages"]] == ["ru", "kk", "en"]
    assert all(item["missing_count"] == 0 for item in snapshot["catalogs"].values())
    json.dumps(snapshot, ensure_ascii=False)


def test_translation_switch_and_safe_fallback() -> None:
    service = LocalizationService.from_directory(CATALOGS, language="en")
    assert service("common.open") == "Open"
    assert service.set_language("kk-KZ") == "kk"
    assert service("common.open") == "Ашу"
    assert service("unknown.key") == "unknown.key"


def test_parameter_formatting_does_not_evaluate_input() -> None:
    service = LocalizationService.from_directory(CATALOGS, language="ru")
    value = "{__import__('os').system('false')}"
    rendered = service("project.open.success", project_name=value)
    assert value in rendered


def test_missing_parameter_returns_unformatted_template() -> None:
    service = LocalizationService.from_directory(CATALOGS, language="en")
    assert service("project.open.success") == "Project “{project_name}” opened"
    assert service("project.open.success", unrelated="x") == "Project “{project_name}” opened"


def test_invalid_catalog_value_is_rejected() -> None:
    with pytest.raises(ValueError):
        LocalizationService({"ru": {"key": 42}})  # type: ignore[dict-item]


def test_application_service_is_reused_and_language_is_mutable() -> None:
    state: dict[str, object] = {}
    container = application_service_container(state)
    first = container.localization(catalogs_dir=CATALOGS, language="ru")
    second = container.localization(catalogs_dir=CATALOGS, language="en")

    assert first is second
    assert isinstance(first, LocalizationApplicationService)
    assert first.language == "ru"
    first.set_language("en")
    assert second("common.save") == "Save"
    assert second.health()["status"] == "ok"
