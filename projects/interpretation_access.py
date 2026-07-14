from __future__ import annotations

"""Role-based access policy for interpretation workflow operations.

The desktop application is local-first and currently has no authentication
provider.  This module therefore models an explicit actor and role without
storing runtime/authentication objects in project state.  A future identity
provider can construct the same ``InterpretationActor`` value and reuse the
policy unchanged.
"""

from dataclasses import dataclass
from typing import Final

ROLE_AUTHOR: Final = "author"
ROLE_REVIEWER: Final = "reviewer"
ROLE_PUBLISHER: Final = "publisher"
ROLE_ADMINISTRATOR: Final = "administrator"
ROLES: Final = (ROLE_AUTHOR, ROLE_REVIEWER, ROLE_PUBLISHER, ROLE_ADMINISTRATOR)

PERMISSION_EDIT: Final = "edit"
PERMISSION_SUBMIT: Final = "submit_for_review"
PERMISSION_RETURN: Final = "return_to_draft"
PERMISSION_APPROVE: Final = "approve"
PERMISSION_REOPEN: Final = "reopen"
PERMISSION_PUBLISH: Final = "publish"
PERMISSION_UNPUBLISH: Final = "unpublish"

_ROLE_PERMISSIONS: Final[dict[str, frozenset[str]]] = {
    ROLE_AUTHOR: frozenset({PERMISSION_EDIT, PERMISSION_SUBMIT}),
    ROLE_REVIEWER: frozenset({PERMISSION_RETURN, PERMISSION_APPROVE, PERMISSION_REOPEN}),
    ROLE_PUBLISHER: frozenset({PERMISSION_PUBLISH, PERMISSION_UNPUBLISH}),
    ROLE_ADMINISTRATOR: frozenset({
        PERMISSION_EDIT,
        PERMISSION_SUBMIT,
        PERMISSION_RETURN,
        PERMISSION_APPROVE,
        PERMISSION_REOPEN,
        PERMISSION_PUBLISH,
        PERMISSION_UNPUBLISH,
    }),
}


@dataclass(frozen=True)
class InterpretationActor:
    id: str = "local-user"
    name: str = "Локальный пользователь"
    role: str = ROLE_ADMINISTRATOR

    def __post_init__(self) -> None:
        actor_id = str(self.id or "").strip()
        actor_name = str(self.name or "").strip()
        role = str(self.role or "").strip().lower()
        if not actor_id:
            raise ValueError("Не указан идентификатор пользователя.")
        if not actor_name:
            raise ValueError("Не указано имя пользователя.")
        if role not in ROLES:
            raise ValueError(f"Неизвестная роль пользователя: {role!r}.")
        object.__setattr__(self, "id", actor_id[:120])
        object.__setattr__(self, "name", actor_name[:160])
        object.__setattr__(self, "role", role)

    def can(self, permission: str) -> bool:
        return str(permission) in _ROLE_PERMISSIONS[self.role]


ROLE_LABELS_RU: Final[dict[str, str]] = {
    ROLE_AUTHOR: "Автор",
    ROLE_REVIEWER: "Рецензент",
    ROLE_PUBLISHER: "Публикатор",
    ROLE_ADMINISTRATOR: "Администратор",
}


def require_permission(actor: InterpretationActor, permission: str) -> None:
    if not actor.can(permission):
        label = ROLE_LABELS_RU.get(actor.role, actor.role)
        raise PermissionError(f"Роль «{label}» не разрешает операцию «{permission}».")
