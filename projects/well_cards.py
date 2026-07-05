from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
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
PROJECT_WELL_COORDINATE_KEYS = ("x", "y", "latitude", "longitude")
PROJECT_WELL_KB_METADATA_KEY = "kb_m"
PROJECT_WELL_GL_METADATA_KEY = "gl_m"
PROJECT_WELL_PLANNED_TD_METADATA_KEY = "planned_td_m"
PROJECT_WELL_ACTUAL_TD_METADATA_KEY = "actual_td_m"
PROJECT_WELL_SPUD_DATE_METADATA_KEY = "spud_date"
PROJECT_WELL_OPERATOR_METADATA_KEY = "operator"
PROJECT_WELL_FIELD_METADATA_KEY = "field"


@dataclass(frozen=True)
class ProjectWellCoordinates:
    """Validated optional well coordinates stored in card metadata.

    X/Y are project-local or field coordinate values and therefore only need to
    be finite numeric values. Latitude and longitude are geographic values and
    are range-checked when provided. Empty UI fields are stored as ``None`` so a
    partially known well card remains valid.
    """

    x: float | None = None
    y: float | None = None
    latitude: float | None = None
    longitude: float | None = None

    @property
    def has_any(self) -> bool:
        return any(value is not None for value in (self.x, self.y, self.latitude, self.longitude))

    @property
    def geographic_label(self) -> str:
        if self.latitude is None or self.longitude is None:
            return ""
        return f"{self.latitude:.6f}, {self.longitude:.6f}"

    @property
    def projected_label(self) -> str:
        if self.x is None or self.y is None:
            return ""
        return f"X={self.x:.6f}".rstrip("0").rstrip(".") + "; " + f"Y={self.y:.6f}".rstrip("0").rstrip(".")


@dataclass(frozen=True)
class ProjectWellDepthReference:
    """Validated optional depth reference and total-depth metadata for a well card.

    KB (Kelly Bushing / rotary table reference elevation) and GL (Ground Level)
    are elevations in meters. Planned/actual TD values are measured depths in
    meters. All values are metadata-only and do not rewrite LAS versions.
    """

    kb_m: float | None = None
    gl_m: float | None = None
    planned_td_m: float | None = None
    actual_td_m: float | None = None

    @property
    def has_kb(self) -> bool:
        return self.kb_m is not None

    @property
    def has_gl(self) -> bool:
        return self.gl_m is not None

    @property
    def has_planned_td(self) -> bool:
        return self.planned_td_m is not None

    @property
    def has_actual_td(self) -> bool:
        return self.actual_td_m is not None

    @property
    def has_td(self) -> bool:
        return self.has_planned_td or self.has_actual_td

    @property
    def has_any(self) -> bool:
        return self.has_kb or self.has_gl or self.has_td

    @staticmethod
    def _format_elevation(label: str, value: float | None) -> str:
        if value is None:
            return ""
        return f"{label}={value:.3f} м".replace(".000 м", " м")

    @property
    def kb_label(self) -> str:
        return self._format_elevation("KB", self.kb_m)

    @property
    def gl_label(self) -> str:
        return self._format_elevation("GL", self.gl_m)

    @property
    def planned_td_label(self) -> str:
        return self._format_elevation("План TD", self.planned_td_m)

    @property
    def actual_td_label(self) -> str:
        return self._format_elevation("Факт TD", self.actual_td_m)

    @property
    def datum_labels(self) -> tuple[str, ...]:
        return tuple(label for label in (self.kb_label, self.gl_label) if label)

    @property
    def td_labels(self) -> tuple[str, ...]:
        return tuple(label for label in (self.planned_td_label, self.actual_td_label) if label)

    @property
    def kb_above_gl_m(self) -> float | None:
        if self.kb_m is None or self.gl_m is None:
            return None
        return self.kb_m - self.gl_m

    @property
    def kb_above_gl_label(self) -> str:
        value = self.kb_above_gl_m
        if value is None:
            return ""
        return f"KB-GL={value:.3f} м".replace(".000 м", " м")




@dataclass(frozen=True)
class ProjectWellDrillingDates:
    """Validated optional drilling date metadata for a well card.

    Dates are stored as ISO ``YYYY-MM-DD`` strings so JSON metadata remains
    stable, readable and easy to compare in audits. Empty UI fields are stored
    as ``None`` and do not make the card invalid.
    """

    spud_date: str | None = None

    @property
    def has_spud_date(self) -> bool:
        return self.spud_date is not None

    @property
    def has_any(self) -> bool:
        return self.has_spud_date

    @property
    def spud_date_label(self) -> str:
        if not self.spud_date:
            return ""
        return f"Дата бурения={self.spud_date}"

    @property
    def labels(self) -> tuple[str, ...]:
        return tuple(label for label in (self.spud_date_label,) if label)


@dataclass(frozen=True)
class ProjectWellOperator:
    """Validated optional operator metadata for a well card.

    The operator is stored as a short human-readable organization name. It is
    deliberately metadata-only: saving it does not touch LAS versions, saved
    calculations or project exports.
    """

    operator: str | None = None

    @property
    def has_operator(self) -> bool:
        return self.operator is not None

    @property
    def has_any(self) -> bool:
        return self.has_operator

    @property
    def operator_label(self) -> str:
        if not self.operator:
            return ""
        return f"Оператор={self.operator}"

    @property
    def labels(self) -> tuple[str, ...]:
        return tuple(label for label in (self.operator_label,) if label)


@dataclass(frozen=True)
class ProjectWellField:
    """Validated optional field metadata for a well card.

    The field name is stored as a short human-readable project metadata value.
    It is intentionally independent from LAS headers because one project may use
    corrected field naming without rewriting source LAS files.
    """

    field: str | None = None

    @property
    def has_field(self) -> bool:
        return self.field is not None

    @property
    def has_any(self) -> bool:
        return self.has_field

    @property
    def field_label(self) -> str:
        if not self.field:
            return ""
        return f"Месторождение={self.field}"

    @property
    def labels(self) -> tuple[str, ...]:
        return tuple(label for label in (self.field_label,) if label)


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

    @property
    def coordinates(self) -> ProjectWellCoordinates:
        return coordinates_from_metadata(self.metadata or {})

    @property
    def depth_reference(self) -> ProjectWellDepthReference:
        return depth_reference_from_metadata(self.metadata or {})

    @property
    def drilling_dates(self) -> ProjectWellDrillingDates:
        return drilling_dates_from_metadata(self.metadata or {})

    @property
    def operator(self) -> ProjectWellOperator:
        return operator_from_metadata(self.metadata or {})

    @property
    def field(self) -> ProjectWellField:
        return field_from_metadata(self.metadata or {})


@dataclass(frozen=True)
class ProjectWellCardTableRow:
    well_id: str
    name: str
    status: str
    status_label: str
    note: str
    updated_at: str
    coordinate_x: float | None = None
    coordinate_y: float | None = None
    latitude: float | None = None
    longitude: float | None = None
    coordinates_label: str = ""
    kb_m: float | None = None
    kb_label: str = ""
    gl_m: float | None = None
    gl_label: str = ""
    planned_td_m: float | None = None
    planned_td_label: str = ""
    actual_td_m: float | None = None
    actual_td_label: str = ""
    td_status_label: str = ""
    kb_above_gl_m: float | None = None
    kb_above_gl_label: str = ""
    spud_date: str | None = None
    spud_date_label: str = ""
    operator: str | None = None
    operator_label: str = ""
    field: str | None = None
    field_label: str = ""


def _optional_float(value: Any, field_label: str) -> float | None:
    """Normalize optional numeric metadata from UI strings or JSON values."""

    if value is None:
        return None
    if isinstance(value, str):
        clean = value.strip().replace(",", ".")
        if not clean:
            return None
        value = clean
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_label}: ожидается число.") from exc
    if number != number or number in (float("inf"), float("-inf")):
        raise ValueError(f"{field_label}: значение должно быть конечным числом.")
    return number


def validate_project_well_coordinates(
    x: Any = None,
    y: Any = None,
    latitude: Any = None,
    longitude: Any = None,
) -> ProjectWellCoordinates:
    """Validate optional projected and geographic well coordinates."""

    coords = ProjectWellCoordinates(
        x=_optional_float(x, "X"),
        y=_optional_float(y, "Y"),
        latitude=_optional_float(latitude, "Широта"),
        longitude=_optional_float(longitude, "Долгота"),
    )
    if coords.latitude is not None and not -90.0 <= coords.latitude <= 90.0:
        raise ValueError("Широта должна быть в диапазоне от -90 до 90.")
    if coords.longitude is not None and not -180.0 <= coords.longitude <= 180.0:
        raise ValueError("Долгота должна быть в диапазоне от -180 до 180.")
    return coords


def coordinates_to_metadata(coords: ProjectWellCoordinates) -> dict[str, float | None]:
    return {
        "x": coords.x,
        "y": coords.y,
        "latitude": coords.latitude,
        "longitude": coords.longitude,
    }


def coordinates_from_metadata(metadata: dict[str, Any]) -> ProjectWellCoordinates:
    return validate_project_well_coordinates(
        x=metadata.get("x"),
        y=metadata.get("y"),
        latitude=metadata.get("latitude"),
        longitude=metadata.get("longitude"),
    )


def merge_project_well_coordinates_metadata(
    metadata: dict[str, Any] | None = None,
    *,
    x: Any = None,
    y: Any = None,
    latitude: Any = None,
    longitude: Any = None,
) -> dict[str, Any]:
    """Return card metadata with validated coordinate keys updated in place."""

    clean_metadata = dict(metadata or {})
    coords = validate_project_well_coordinates(x=x, y=y, latitude=latitude, longitude=longitude)
    clean_metadata.update(coordinates_to_metadata(coords))
    return clean_metadata



def validate_project_well_depth_reference(
    kb_m: Any = None,
    gl_m: Any = None,
    planned_td_m: Any = None,
    actual_td_m: Any = None,
) -> ProjectWellDepthReference:
    """Validate optional KB and GL elevations stored in meters.

    The helper accepts UI strings with either comma or dot decimal separators.
    Empty values are stored as ``None``. A broad engineering range keeps the
    metadata flexible while still catching accidental feet values with extra
    symbols, infinities and obviously wrong numbers.
    """

    kb_value = _optional_float(kb_m, "KB")
    gl_value = _optional_float(gl_m, "GL")
    planned_td_value = _optional_float(planned_td_m, "Плановая TD")
    actual_td_value = _optional_float(actual_td_m, "Фактическая TD")
    if kb_value is not None and not -1000.0 <= kb_value <= 10000.0:
        raise ValueError("KB должен быть в диапазоне от -1000 до 10000 м.")
    if gl_value is not None and not -1000.0 <= gl_value <= 10000.0:
        raise ValueError("GL должен быть в диапазоне от -1000 до 10000 м.")
    if planned_td_value is not None and not 0.0 < planned_td_value <= 15000.0:
        raise ValueError("Плановая TD должна быть в диапазоне от 0 до 15000 м.")
    if actual_td_value is not None and not 0.0 < actual_td_value <= 15000.0:
        raise ValueError("Фактическая TD должна быть в диапазоне от 0 до 15000 м.")
    if (
        planned_td_value is not None
        and actual_td_value is not None
        and actual_td_value > planned_td_value * 1.5
    ):
        raise ValueError("Фактическая TD подозрительно больше плановой TD; проверьте единицы измерения.")
    return ProjectWellDepthReference(
        kb_m=kb_value,
        gl_m=gl_value,
        planned_td_m=planned_td_value,
        actual_td_m=actual_td_value,
    )


def validate_project_well_kb(kb_m: Any = None) -> ProjectWellDepthReference:
    """Backward-compatible KB-only validation helper."""

    return validate_project_well_depth_reference(kb_m=kb_m)


def validate_project_well_gl(gl_m: Any = None) -> ProjectWellDepthReference:
    """Validate optional GL elevation stored in meters."""

    return validate_project_well_depth_reference(gl_m=gl_m)


def depth_reference_to_metadata(reference: ProjectWellDepthReference) -> dict[str, float | None]:
    return {
        PROJECT_WELL_KB_METADATA_KEY: reference.kb_m,
        PROJECT_WELL_GL_METADATA_KEY: reference.gl_m,
        PROJECT_WELL_PLANNED_TD_METADATA_KEY: reference.planned_td_m,
        PROJECT_WELL_ACTUAL_TD_METADATA_KEY: reference.actual_td_m,
    }


def depth_reference_from_metadata(metadata: dict[str, Any]) -> ProjectWellDepthReference:
    return validate_project_well_depth_reference(
        kb_m=metadata.get(PROJECT_WELL_KB_METADATA_KEY),
        gl_m=metadata.get(PROJECT_WELL_GL_METADATA_KEY),
        planned_td_m=metadata.get(PROJECT_WELL_PLANNED_TD_METADATA_KEY),
        actual_td_m=metadata.get(PROJECT_WELL_ACTUAL_TD_METADATA_KEY),
    )


def merge_project_well_depth_reference_metadata(
    metadata: dict[str, Any] | None = None,
    *,
    kb_m: Any = None,
    gl_m: Any = None,
    planned_td_m: Any = None,
    actual_td_m: Any = None,
) -> dict[str, Any]:
    """Return card metadata with validated KB/GL elevations updated."""

    clean_metadata = dict(metadata or {})
    clean_metadata.update(
        depth_reference_to_metadata(
            validate_project_well_depth_reference(
                kb_m=kb_m,
                gl_m=gl_m,
                planned_td_m=planned_td_m,
                actual_td_m=actual_td_m,
            )
        )
    )
    return clean_metadata


def merge_project_well_td_metadata(
    metadata: dict[str, Any] | None = None,
    *,
    planned_td_m: Any = None,
    actual_td_m: Any = None,
) -> dict[str, Any]:
    """Return card metadata with validated planned/actual total depth updated."""

    clean_metadata = dict(metadata or {})
    reference = depth_reference_from_metadata(clean_metadata)
    clean_metadata.update(
        depth_reference_to_metadata(
            validate_project_well_depth_reference(
                kb_m=reference.kb_m,
                gl_m=reference.gl_m,
                planned_td_m=planned_td_m,
                actual_td_m=actual_td_m,
            )
        )
    )
    return clean_metadata


def merge_project_well_kb_metadata(
    metadata: dict[str, Any] | None = None,
    *,
    kb_m: Any = None,
) -> dict[str, Any]:
    """Return card metadata with validated KB elevation updated."""

    clean_metadata = dict(metadata or {})
    reference = depth_reference_from_metadata(clean_metadata)
    clean_metadata.update(
        depth_reference_to_metadata(validate_project_well_depth_reference(
            kb_m=kb_m,
            gl_m=reference.gl_m,
            planned_td_m=reference.planned_td_m,
            actual_td_m=reference.actual_td_m,
        ))
    )
    return clean_metadata


def merge_project_well_gl_metadata(
    metadata: dict[str, Any] | None = None,
    *,
    gl_m: Any = None,
) -> dict[str, Any]:
    """Return card metadata with validated GL elevation updated."""

    clean_metadata = dict(metadata or {})
    reference = depth_reference_from_metadata(clean_metadata)
    clean_metadata.update(
        depth_reference_to_metadata(validate_project_well_depth_reference(
            kb_m=reference.kb_m,
            gl_m=gl_m,
            planned_td_m=reference.planned_td_m,
            actual_td_m=reference.actual_td_m,
        ))
    )
    return clean_metadata


def build_project_well_td_status_label(reference: ProjectWellDepthReference, max_las_depth_m: Any = None) -> str:
    """Return a compact TD status for UI tables and tests.

    Without a LAS depth argument the function reports only planned/factual TD
    consistency. When `max_las_depth_m` is provided, it also flags LAS curves
    that extend below the saved actual TD.
    """

    if not reference.has_td:
        return "TD не указана"
    target_td = reference.actual_td_m if reference.actual_td_m is not None else reference.planned_td_m
    if target_td is None:
        return "TD не указана"
    max_depth = _optional_float(max_las_depth_m, "Максимальная глубина LAS")
    if max_depth is not None and max_depth > target_td + 0.001:
        return f"LAS глубже TD на {max_depth - target_td:.3f} м".replace(".000 м", " м")
    if reference.actual_td_m is not None and reference.planned_td_m is not None:
        delta = reference.actual_td_m - reference.planned_td_m
        if abs(delta) <= 0.001:
            return "Фактическая TD совпадает с плановой"
        sign = "+" if delta > 0 else ""
        return f"Факт TD {sign}{delta:.3f} м к плану".replace(".000 м", " м")
    return "TD указана"



def _optional_iso_date(value: Any, field_label: str) -> str | None:
    """Normalize optional ISO date metadata from UI strings or JSON values."""

    if value is None:
        return None
    if isinstance(value, str):
        clean = value.strip()
        if not clean:
            return None
        value = clean
    if isinstance(value, date) and not isinstance(value, datetime):
        return value.isoformat()
    if not isinstance(value, str):
        raise ValueError(f"{field_label}: ожидается дата в формате YYYY-MM-DD.")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field_label}: ожидается дата в формате YYYY-MM-DD.") from exc
    if parsed.year < 1900 or parsed.year > 2100:
        raise ValueError(f"{field_label}: год должен быть в диапазоне 1900..2100.")
    return parsed.isoformat()


def validate_project_well_drilling_dates(spud_date: Any = None) -> ProjectWellDrillingDates:
    """Validate optional drilling dates stored in the well card metadata."""

    return ProjectWellDrillingDates(spud_date=_optional_iso_date(spud_date, "Дата бурения"))


def drilling_dates_to_metadata(dates: ProjectWellDrillingDates) -> dict[str, str | None]:
    return {PROJECT_WELL_SPUD_DATE_METADATA_KEY: dates.spud_date}


def drilling_dates_from_metadata(metadata: dict[str, Any]) -> ProjectWellDrillingDates:
    return validate_project_well_drilling_dates(spud_date=metadata.get(PROJECT_WELL_SPUD_DATE_METADATA_KEY))


def merge_project_well_drilling_dates_metadata(
    metadata: dict[str, Any] | None = None,
    *,
    spud_date: Any = None,
) -> dict[str, Any]:
    """Return card metadata with validated drilling date keys updated."""

    clean_metadata = dict(metadata or {})
    clean_metadata.update(drilling_dates_to_metadata(validate_project_well_drilling_dates(spud_date=spud_date)))
    return clean_metadata


def _optional_text(value: Any, field_label: str, *, max_length: int = 120) -> str | None:
    """Normalize optional short text metadata from UI strings or JSON values."""

    if value is None:
        return None
    clean = str(value).strip()
    if not clean:
        return None
    clean = re.sub(r"\s+", " ", clean)
    if len(clean) > max_length:
        raise ValueError(f"{field_label}: длина не должна превышать {max_length} символов.")
    if any(ch in clean for ch in "\r\n\t"):
        raise ValueError(f"{field_label}: значение должно быть одной строкой.")
    return clean


def validate_project_well_operator(operator: Any = None) -> ProjectWellOperator:
    """Validate optional well operator metadata."""

    return ProjectWellOperator(operator=_optional_text(operator, "Оператор"))


def operator_to_metadata(operator: ProjectWellOperator) -> dict[str, str | None]:
    return {PROJECT_WELL_OPERATOR_METADATA_KEY: operator.operator}


def operator_from_metadata(metadata: dict[str, Any]) -> ProjectWellOperator:
    return validate_project_well_operator(operator=metadata.get(PROJECT_WELL_OPERATOR_METADATA_KEY))


def merge_project_well_operator_metadata(
    metadata: dict[str, Any] | None = None,
    *,
    operator: Any = None,
) -> dict[str, Any]:
    """Return card metadata with validated operator key updated."""

    clean_metadata = dict(metadata or {})
    clean_metadata.update(operator_to_metadata(validate_project_well_operator(operator=operator)))
    return clean_metadata


def validate_project_well_field(field: Any = None) -> ProjectWellField:
    """Validate optional well field metadata."""

    return ProjectWellField(field=_optional_text(field, "Месторождение"))


def field_to_metadata(field: ProjectWellField) -> dict[str, str | None]:
    return {PROJECT_WELL_FIELD_METADATA_KEY: field.field}


def field_from_metadata(metadata: dict[str, Any]) -> ProjectWellField:
    return validate_project_well_field(field=metadata.get(PROJECT_WELL_FIELD_METADATA_KEY))


def merge_project_well_field_metadata(
    metadata: dict[str, Any] | None = None,
    *,
    field: Any = None,
) -> dict[str, Any]:
    """Return card metadata with validated field key updated."""

    clean_metadata = dict(metadata or {})
    clean_metadata.update(field_to_metadata(validate_project_well_field(field=field)))
    return clean_metadata


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
            coordinate_x=card.coordinates.x,
            coordinate_y=card.coordinates.y,
            latitude=card.coordinates.latitude,
            longitude=card.coordinates.longitude,
            coordinates_label="; ".join(
                label for label in (card.coordinates.projected_label, card.coordinates.geographic_label) if label
            ),
            kb_m=card.depth_reference.kb_m,
            kb_label=card.depth_reference.kb_label,
            gl_m=card.depth_reference.gl_m,
            gl_label=card.depth_reference.gl_label,
            planned_td_m=card.depth_reference.planned_td_m,
            planned_td_label=card.depth_reference.planned_td_label,
            actual_td_m=card.depth_reference.actual_td_m,
            actual_td_label=card.depth_reference.actual_td_label,
            td_status_label=build_project_well_td_status_label(card.depth_reference),
            kb_above_gl_m=card.depth_reference.kb_above_gl_m,
            kb_above_gl_label=card.depth_reference.kb_above_gl_label,
            spud_date=card.drilling_dates.spud_date,
            spud_date_label=card.drilling_dates.spud_date_label,
            operator=card.operator.operator,
            operator_label=card.operator.operator_label,
            field=card.field.field,
            field_label=card.field.field_label,
        )
        for card in list_project_well_cards(root, project_id)
    )
