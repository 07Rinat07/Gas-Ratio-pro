"""JSON-safe UI component contracts consumed by framework adapters."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Literal

ButtonVariant = Literal["primary", "secondary", "ghost", "danger"]
EmptyStateTone = Literal["neutral", "info", "warning", "error"]

@dataclass(frozen=True, slots=True)
class ButtonSpec:
    label: str
    key: str
    variant: ButtonVariant = "secondary"
    disabled: bool = False
    help_text: str = ""
    icon: str = ""
    compact: bool = False
    def to_dict(self) -> dict[str, object]:
        return asdict(self)

@dataclass(frozen=True, slots=True)
class EmptyStateSpec:
    title: str
    message: str
    tone: EmptyStateTone = "neutral"
    action: ButtonSpec | None = None
    details: tuple[str, ...] = ()
    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        return payload
