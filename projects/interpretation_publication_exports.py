from __future__ import annotations

"""Portable exports for interpretation approval/publication audit history."""

import csv
import io
import json
from dataclasses import asdict
from typing import Iterable

from openpyxl import Workbook

from projects.interpretation_publication import InterpretationPublicationEvent

AUDIT_EXPORT_SCHEMA = "gas-ratio-pro/interpretation-publication-audit/v1"


def _rows(events: Iterable[InterpretationPublicationEvent]) -> list[dict[str, str]]:
    return [
        {
            "id": item.id,
            "created_at": item.created_at,
            "action": item.action,
            "from_status": item.from_status,
            "to_status": item.to_status,
            "actor_id": item.actor_id,
            "actor_name": item.actor_name,
            "actor_role": item.actor_role,
            "comment": item.comment,
            "revision_id": item.revision_id,
        }
        for item in events
    ]


def export_publication_audit_json(
    events: Iterable[InterpretationPublicationEvent],
    *, project_id: str,
    well_id: str,
    interpretation_id: str,
) -> bytes:
    payload = {
        "schema": AUDIT_EXPORT_SCHEMA,
        "project_id": str(project_id),
        "well_id": str(well_id),
        "interpretation_id": str(interpretation_id),
        "events": _rows(events),
    }
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def export_publication_audit_csv(events: Iterable[InterpretationPublicationEvent]) -> bytes:
    rows = _rows(events)
    fields = ["id", "created_at", "action", "from_status", "to_status", "actor_id", "actor_name", "actor_role", "comment", "revision_id"]
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    return ("\ufeff" + stream.getvalue()).encode("utf-8")


def export_publication_audit_xlsx(
    events: Iterable[InterpretationPublicationEvent],
    *, project_id: str,
    well_id: str,
    interpretation_id: str,
) -> bytes:
    rows = _rows(events)
    fields = ["id", "created_at", "action", "from_status", "to_status", "actor_id", "actor_name", "actor_role", "comment", "revision_id"]
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "publication_audit"
    sheet.append(fields)
    for row in rows:
        sheet.append([row[field] for field in fields])
    metadata = workbook.create_sheet("metadata")
    metadata.append(["schema", AUDIT_EXPORT_SCHEMA])
    metadata.append(["project_id", str(project_id)])
    metadata.append(["well_id", str(well_id)])
    metadata.append(["interpretation_id", str(interpretation_id)])
    metadata.append(["event_count", len(rows)])
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
