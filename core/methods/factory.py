from __future__ import annotations

from core.methods.haworth import HaworthMethod
from core.methods.pixler import PixlerMethod
from core.methods.registry import MethodRegistry
from core.methods.ternary import TernaryMethod


def build_default_method_registry() -> MethodRegistry:
    return MethodRegistry((PixlerMethod(), TernaryMethod(), HaworthMethod()))
