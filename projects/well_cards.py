from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from projects.repository import DEFAULT_PROJECT_ID, DEFAULT_PROJECTS_ROOT, safe_project_id

PROJECT_WELL_CARDS_FILE_NAME = "well_cards.json"
PROJECT_WELL_CARDS_SCHEMA_VERSION = 1
PROJECT_WELL_CARD_STATUSES: dict[str, str] = {
    "draft": "Черновик",
    "review": "На проверке",
    "ready": "Готова",
    "archived": "Архив",
}


@dataclass(frozen=True)
class ProjectWellCard:
    """Metadata-only well card stored inside a local project.

    The first Well Manager step intentionally stores only descriptive metadata.
    Heavy LAS payloads and calculation tables remain in their own project stores.
    Later steps can safely extend the `metadata` object with coordinates, KB, GL,
    TD, drilling dates, operator and field names without changing LAS versions.
    """

    well_id: str
    name: str
    status: str = "draft"
    note: str = ""
    created_at: str = ""
    updated_at: str = ""
    metadata: dict[str, Any] | None = None

    @property
    def status_label(self) -> str:
        return PROJECT_WELL_CARD_STATUSES.get(self.status, self.status or "Черновик")


@dataclass(frozen=True)
class ProjectWellCardTableRow:
    well_id: str
    name: str
    status: str
    status_label: str
    note: str
    updated_at: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_well_id(well_id: str) -> str:
    if not re.fullmatch(r"[0-9A-Za-zА-Яа-я_-]+", well_id):
        raise ValueError("Некорректный идентификатор скважины.")
    return well_id


def _well_cards_path(root: Path | str, project_id: str) -> Path:
    return Path(root) / safe_project_id(project_id) / PROJECT_WELL_CARDS_FILE_NAME


def _card_from_dict(raw: dict[str, Any]) -> ProjectWellCard:
    well_id = safe_well_id(str(raw.get("well_id", "")))
    status = str(raw.get("status", "draft")) or "draft"
    if status not in PROJECT_WELL_CARD_STATUSES:
        status = "draft"
    return ProjectWellCard(
        well_id=well_id,
        name=str(raw.get("name", "")) or well_id,
        status=status,
        note=str(raw.get("note", "")),
        created_at=str(raw.get("created_at", "")),
        updated_at=str(raw.get("updated_at", "")),
        metadata=dict(raw.get("metadata", {}) or {}),
    )


def _card_to_dict(card: ProjectWellCard) -> dict[str, Any]:
    return {
        "well_id": safe_well_id(card.well_id),
        "name": card.name.strip() or card.well_id,
        "status": card.status if card.status in PROJECT_WELL_CARD_STATUSES else "draft",
        "note": card.note.strip(),
        "created_at": card.created_at,
        "updated_at": card.updated_at,
        "metadata": dict(card.metadata or {}),
    }


def _read_payload(root: Path | str, project_id: str) -> dict[str, Any]:
    path = _well_cards_path(root, project_id)
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _write_cards(root: Path | str, project_id: str, cards: tuple[ProjectWellCard, ...]) -> Path:
    path = _well_cards_path(root, project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": PROJECT_WELL_CARDS_SCHEMA_VERSION,
        "project_id": safe_project_id(project_id),
        "updated_at": _utc_now(),
        "well_cards": [_card_to_dict(card) for card in cards],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def list_project_well_cards(
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
) -> tuple[ProjectWellCard, ...]:
    """Return saved well cards sorted by update time without reading LAS bytes."""

    try:
        payload = _read_payload(root, project_id)
        raw_cards = payload.get("well_cards", ())
        cards = tuple(_card_from_dict(raw) for raw in raw_cards if isinstance(raw, dict))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return ()
    return tuple(sorted(cards, key=lambda card: card.updated_at, reverse=True))


def project_well_cards_by_id(
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
) -> dict[str, ProjectWellCard]:
    return {card.well_id: card for card in list_project_well_cards(root, project_id)}


def get_project_well_card(
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
    well_id: str = "",
) -> ProjectWellCard | None:
    return project_well_cards_by_id(root, project_id).get(safe_well_id(well_id))


def save_project_well_card(
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
    well_id: str = "",
    name: str = "",
    status: str = "draft",
    note: str = "",
    metadata: dict[str, Any] | None = None,
) -> ProjectWellCard:
    """Create or update a project well card.

    The card is keyed by stable `well_id`. Re-saving the same well updates only
    its metadata card and keeps LAS versions untouched.
    """

    clean_well_id = safe_well_id(well_id)
    clean_status = status if status in PROJECT_WELL_CARD_STATUSES else "draft"
    existing_cards = project_well_cards_by_id(root, project_id)
    existing = existing_cards.get(clean_well_id)
    now = _utc_now()
    card = ProjectWellCard(
        well_id=clean_well_id,
        name=name.strip() or (existing.name if existing else clean_well_id),
        status=clean_status,
        note=note.strip(),
        created_at=existing.created_at if existing else now,
        updated_at=now,
        metadata=dict(metadata if metadata is not None else (existing.metadata if existing else {})),
    )
    cards = tuple(
        sorted(
            (card, *(item for key, item in existing_cards.items() if key != clean_well_id)),
            key=lambda item: item.updated_at,
            reverse=True,
        )
    )
    _write_cards(root, project_id, cards)
    return card


def ensure_project_well_card(
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
    well_id: str = "",
    name: str = "",
) -> ProjectWellCard:
    """Return an existing card or create a minimal draft card for a known well."""

    clean_well_id = safe_well_id(well_id)
    existing = get_project_well_card(root, project_id, clean_well_id)
    if existing:
        return existing
    return save_project_well_card(
        root=root,
        project_id=project_id,
        well_id=clean_well_id,
        name=name or clean_well_id,
        status="draft",
    )


def build_project_well_card_table(
    root: Path | str = DEFAULT_PROJECTS_ROOT,
    project_id: str = DEFAULT_PROJECT_ID,
) -> tuple[ProjectWellCardTableRow, ...]:
    """Build compact rows for UI previews, CSV export or tests."""

    return tuple(
        ProjectWellCardTableRow(
            well_id=card.well_id,
            name=card.name,
            status=card.status,
            status_label=card.status_label,
            note=card.note,
            updated_at=card.updated_at,
        )
        for card in list_project_well_cards(root, project_id)
    )
