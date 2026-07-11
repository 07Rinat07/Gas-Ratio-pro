"""Responsive and accessibility contracts for Modern Workbench.

The module is renderer-neutral.  It describes supported viewport classes,
keyboard/focus behavior and presentation readability without importing a UI
framework or mutating application/domain state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable


@dataclass(frozen=True, slots=True)
class WorkbenchResponsiveProfile:
    id: str
    min_width_px: int
    max_width_px: int | None
    navigation_mode: str
    dock_strategy: str
    columns: int
    min_touch_target_px: int = 44
    horizontal_scroll: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "min_width_px": self.min_width_px,
            "max_width_px": self.max_width_px,
            "navigation_mode": self.navigation_mode,
            "dock_strategy": self.dock_strategy,
            "columns": self.columns,
            "min_touch_target_px": self.min_touch_target_px,
            "horizontal_scroll": self.horizontal_scroll,
        }


DEFAULT_WORKBENCH_RESPONSIVE_PROFILES: tuple[WorkbenchResponsiveProfile, ...] = (
    WorkbenchResponsiveProfile("phone", 0, 599, "compact", "single-column", 1),
    WorkbenchResponsiveProfile("tablet", 600, 1023, "compact", "priority-stack", 1),
    WorkbenchResponsiveProfile("laptop", 1024, 1599, "rail", "docked", 2),
    WorkbenchResponsiveProfile("wide", 1600, None, "expanded", "docked", 3),
)


@dataclass(frozen=True, slots=True)
class WorkbenchAccessibleElement:
    id: str
    role: str
    label: str
    description: str
    focus_order: int
    target: str
    keyboard_shortcut: str = ""
    current: bool = False
    disabled: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role,
            "label": self.label,
            "description": self.description,
            "focus_order": self.focus_order,
            "target": self.target,
            "keyboard_shortcut": self.keyboard_shortcut,
            "current": self.current,
            "disabled": self.disabled,
        }


@dataclass(frozen=True, slots=True)
class WorkbenchContrastCheck:
    id: str
    foreground: str
    background: str
    ratio: float
    required_ratio: float

    @property
    def passed(self) -> bool:
        return self.ratio >= self.required_ratio

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "foreground": self.foreground,
            "background": self.background,
            "ratio": round(self.ratio, 2),
            "required_ratio": self.required_ratio,
            "passed": self.passed,
        }


@dataclass(frozen=True, slots=True)
class WorkbenchAccessibilityAudit:
    standard: str
    responsive_profiles: tuple[WorkbenchResponsiveProfile, ...]
    elements: tuple[WorkbenchAccessibleElement, ...]
    contrast_checks: tuple[WorkbenchContrastCheck, ...]
    landmarks: tuple[dict[str, str], ...] = field(default_factory=tuple)

    @property
    def passed(self) -> bool:
        focus_orders = [item.focus_order for item in self.elements if not item.disabled]
        return (
            bool(self.responsive_profiles)
            and all(not profile.horizontal_scroll for profile in self.responsive_profiles)
            and focus_orders == sorted(focus_orders)
            and len(focus_orders) == len(set(focus_orders))
            and all(item.label and item.role and item.description for item in self.elements)
            and all(check.passed for check in self.contrast_checks)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "standard": self.standard,
            "passed": self.passed,
            "responsive_profiles": [item.to_dict() for item in self.responsive_profiles],
            "focus_order": [item.id for item in self.elements if not item.disabled],
            "elements": [item.to_dict() for item in self.elements],
            "landmarks": [dict(item) for item in self.landmarks],
            "contrast_checks": [item.to_dict() for item in self.contrast_checks],
            "keyboard": {
                "tab": "move to next focusable Workbench control",
                "shift+tab": "move to previous focusable Workbench control",
                "enter": "activate focused control",
                "space": "activate focused button",
                "escape": "return focus to active workspace",
            },
        }


def _hex_to_rgb(value: str) -> tuple[float, float, float]:
    text = str(value or "").strip().lstrip("#")
    if len(text) == 3:
        text = "".join(character * 2 for character in text)
    if len(text) != 6:
        raise ValueError(f"Invalid hex colour: {value!r}")
    return tuple(int(text[index:index + 2], 16) / 255.0 for index in (0, 2, 4))  # type: ignore[return-value]


def _relative_luminance(value: str) -> float:
    def channel(component: float) -> float:
        return component / 12.92 if component <= 0.04045 else ((component + 0.055) / 1.055) ** 2.4

    red, green, blue = _hex_to_rgb(value)
    return 0.2126 * channel(red) + 0.7152 * channel(green) + 0.0722 * channel(blue)


def contrast_ratio(foreground: str, background: str) -> float:
    first = _relative_luminance(foreground)
    second = _relative_luminance(background)
    lighter, darker = max(first, second), min(first, second)
    return (lighter + 0.05) / (darker + 0.05)


def default_contrast_checks() -> tuple[WorkbenchContrastCheck, ...]:
    pairs = (
        ("body-text", "#17202A", "#FFFFFF", 4.5),
        ("muted-text", "#4B5563", "#FFFFFF", 4.5),
        ("primary-action", "#FFFFFF", "#155E75", 4.5),
        ("focus-indicator", "#0B63CE", "#FFFFFF", 3.0),
        ("status-text", "#1F2937", "#F3F4F6", 4.5),
    )
    return tuple(
        WorkbenchContrastCheck(item_id, foreground, background, contrast_ratio(foreground, background), required)
        for item_id, foreground, background, required in pairs
    )


def build_workbench_accessibility_audit(
    *,
    navigation: Iterable[Any],
    dock_panes: Iterable[Any],
    actions: Iterable[Any],
    active_navigation_id: str = "",
    active_dock_pane_id: str = "",
) -> WorkbenchAccessibilityAudit:
    """Build deterministic focus and accessibility metadata from shell objects."""

    elements: list[WorkbenchAccessibleElement] = []
    focus_order = 10

    for item in navigation:
        if not bool(getattr(item, "visible", True)):
            continue
        item_id = str(getattr(item, "id", ""))
        title = str(getattr(item, "title", item_id))
        workspace = str(getattr(item, "workspace", "workspace"))
        elements.append(
            WorkbenchAccessibleElement(
                id=f"focus.{item_id}",
                role="link",
                label=title,
                description=f"Открыть рабочий раздел {title} ({workspace}).",
                focus_order=focus_order,
                target=item_id,
                keyboard_shortcut="Enter",
                current=item_id == active_navigation_id,
                disabled=not bool(getattr(item, "enabled", True)),
            )
        )
        focus_order += 10

    for pane in dock_panes:
        if not bool(getattr(pane, "opened", True)) or bool(getattr(pane, "collapsed", False)):
            continue
        pane_id = str(getattr(pane, "id", ""))
        title = str(getattr(pane, "title", pane_id))
        region = str(getattr(pane, "region", "center"))
        elements.append(
            WorkbenchAccessibleElement(
                id=f"focus.{pane_id}",
                role="region",
                label=title,
                description=f"Панель {title}, область {region}.",
                focus_order=focus_order,
                target=pane_id,
                keyboard_shortcut="Enter",
                current=pane_id == active_dock_pane_id,
            )
        )
        focus_order += 10

    for action in actions:
        normalized = action.normalized() if hasattr(action, "normalized") else action
        action_id = str(getattr(normalized, "id", ""))
        title = str(getattr(normalized, "title", action_id))
        target = str(getattr(normalized, "target", "workbench"))
        elements.append(
            WorkbenchAccessibleElement(
                id=f"focus.{action_id}",
                role="button",
                label=title,
                description=f"Выполнить действие «{title}» для {target}.",
                focus_order=focus_order,
                target=action_id,
                keyboard_shortcut="Enter Space",
                disabled=not bool(getattr(normalized, "enabled", True)),
            )
        )
        focus_order += 10

    return WorkbenchAccessibilityAudit(
        standard="WCAG 2.2 AA",
        responsive_profiles=DEFAULT_WORKBENCH_RESPONSIVE_PROFILES,
        elements=tuple(elements),
        contrast_checks=default_contrast_checks(),
        landmarks=(
            {"id": "landmark.navigation", "role": "navigation", "label": "Workbench navigation"},
            {"id": "landmark.main", "role": "main", "label": "Active engineering workspace"},
            {"id": "landmark.status", "role": "status", "label": "Workbench status"},
        ),
    )
