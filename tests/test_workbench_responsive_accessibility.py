from __future__ import annotations

import json

from app.workbench_renderer import build_workbench_responsive_css, build_streamlit_workbench_adapter
from core.workbench_accessibility import contrast_ratio


def test_renderer_contract_declares_supported_responsive_profiles() -> None:
    payload = build_streamlit_workbench_adapter({}).payload()
    profiles = payload["responsive"]["profiles"]

    assert [item["id"] for item in profiles] == ["phone", "tablet", "laptop", "wide"]
    assert all(item["horizontal_scroll"] is False for item in profiles)
    assert all(item["min_touch_target_px"] >= 44 for item in profiles)
    assert payload["responsive"]["horizontal_scroll_allowed"] is False


def test_accessibility_audit_has_deterministic_unique_focus_order() -> None:
    payload = build_streamlit_workbench_adapter({}).payload()
    audit = payload["accessibility"]
    orders = [item["focus_order"] for item in audit["elements"] if not item["disabled"]]

    assert audit["standard"] == "WCAG 2.2 AA"
    assert audit["passed"] is True
    assert orders == sorted(orders)
    assert len(orders) == len(set(orders))
    assert audit["focus_order"] == [item["id"] for item in audit["elements"] if not item["disabled"]]


def test_accessible_elements_have_labels_roles_descriptions_and_keyboard_contracts() -> None:
    audit = build_streamlit_workbench_adapter({}).payload()["accessibility"]

    assert {item["role"] for item in audit["elements"]} >= {"link", "region", "button"}
    assert all(item["label"] for item in audit["elements"])
    assert all(item["description"] for item in audit["elements"])
    assert audit["keyboard"]["tab"].startswith("move to next")
    assert audit["keyboard"]["enter"].startswith("activate")
    assert {item["role"] for item in audit["landmarks"]} == {"navigation", "main", "status"}


def test_active_navigation_and_dock_pane_are_exposed_as_current_focus_targets() -> None:
    state = {}
    payload = build_streamlit_workbench_adapter(state).payload()
    current_targets = {item["target"] for item in payload["accessibility"]["elements"] if item["current"]}

    assert payload["interaction"]["active_navigation_id"] in current_targets
    assert payload["interaction"]["active_dock_pane_id"] in current_targets


def test_contrast_audit_meets_wcag_thresholds() -> None:
    checks = build_streamlit_workbench_adapter({}).payload()["accessibility"]["contrast_checks"]

    assert all(item["passed"] for item in checks)
    assert all(item["ratio"] >= item["required_ratio"] for item in checks)
    assert contrast_ratio("#17202A", "#FFFFFF") >= 4.5


def test_accessibility_payload_is_serializable_and_excludes_runtime_objects() -> None:
    payload = build_streamlit_workbench_adapter({}).payload()
    serialized = json.dumps(payload, ensure_ascii=False)

    assert "DataFrame" not in serialized
    assert "WorkbenchCommandRegistry" not in serialized
    assert "WorkbenchAccessibilityAudit" not in serialized


def test_streamlit_responsive_css_has_all_breakpoints_and_overflow_guard() -> None:
    css = build_workbench_responsive_css()

    assert "overflow-x: hidden" in css
    assert "min-height: 44px" in css
    assert "min-width: 600px" in css
    assert "min-width: 1024px" in css
    assert "min-width: 1600px" in css
    assert ":focus-visible" in css
