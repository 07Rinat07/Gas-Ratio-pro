"""Theme registry independent from the rendering framework."""
from __future__ import annotations
from dataclasses import dataclass
from .tokens import DARK_TOKENS, DesignTokens

@dataclass(frozen=True, slots=True)
class Theme:
    theme_id: str
    display_name: str
    tokens: DesignTokens

class ThemeEngine:
    def __init__(self, themes: tuple[Theme, ...] | None = None, default_theme_id: str = "dark") -> None:
        source = themes or (Theme("dark", "Dark", DARK_TOKENS),)
        self._themes = {theme.theme_id: theme for theme in source}
        if default_theme_id not in self._themes:
            raise ValueError(f"unknown default theme: {default_theme_id}")
        self._active_id = default_theme_id

    @property
    def active(self) -> Theme:
        return self._themes[self._active_id]

    def set_active(self, theme_id: str) -> Theme:
        if theme_id not in self._themes:
            raise KeyError(theme_id)
        self._active_id = theme_id
        return self.active

    def list_themes(self) -> tuple[Theme, ...]:
        return tuple(self._themes.values())
