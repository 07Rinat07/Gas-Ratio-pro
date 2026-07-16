"""Thin Streamlit adapter for GAS RATIO PRO UI component contracts."""
from __future__ import annotations
from html import escape
from typing import Any
from ui_platform.components.contracts import ButtonSpec, EmptyStateSpec
from ui_platform.theme.engine import ThemeEngine

class StreamlitUIAdapter:
    def __init__(self, st_module: Any, *, theme_engine: ThemeEngine | None = None) -> None:
        self.st = st_module
        self.theme_engine = theme_engine or ThemeEngine()

    def button(self, spec: ButtonSpec) -> bool:
        kind = "primary" if spec.variant in {"primary", "danger"} else "secondary"
        kwargs = {
            "key": spec.key,
            "disabled": spec.disabled,
            "help": spec.help_text or None,
            "type": kind,
        }
        # Modern Streamlit supports content-sized controls; test doubles may not.
        try:
            return bool(self.st.button(spec.label, width="content", **kwargs))
        except TypeError:
            return bool(self.st.button(spec.label, **kwargs))

    def empty_state(self, spec: EmptyStateSpec) -> bool:
        tokens = self.theme_engine.active.tokens
        details = "".join(f"<li>{escape(item)}</li>" for item in spec.details)
        detail_html = f"<ul>{details}</ul>" if details else ""
        html = f"""
        <section class="gr-empty-state" style="border:1px solid {tokens.colors.border};background:{tokens.colors.surface};border-radius:{tokens.radius.lg}px;padding:{tokens.spacing.xl}px;">
          <h3 style="margin:0 0 {tokens.spacing.sm}px;color:{tokens.colors.text};">{escape(spec.title)}</h3>
          <p style="margin:0;color:{tokens.colors.text_muted};">{escape(spec.message)}</p>
          {detail_html}
        </section>
        """
        self.st.markdown(html, unsafe_allow_html=True)
        return self.button(spec.action) if spec.action else False
