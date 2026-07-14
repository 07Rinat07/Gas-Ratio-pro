import csv
import io
import json
from pathlib import Path

from openpyxl import load_workbook

from projects.interpretation_access import InterpretationActor
from projects.interpretation_publication import InterpretationPublicationService
from projects.interpretation_publication_exports import (
    AUDIT_EXPORT_SCHEMA,
    export_publication_audit_csv,
    export_publication_audit_json,
    export_publication_audit_xlsx,
)


def _events(tmp_path: Path):
    service = InterpretationPublicationService(
        root=tmp_path, project_id="p", well_id="w", interpretation_id="default",
        actor=InterpretationActor(id="author-1", name="Alice", role="author"),
    )
    return service.submit_for_review(comment="ready").events


def test_publication_audit_exports_include_actor_and_scope(tmp_path: Path) -> None:
    events = _events(tmp_path)
    payload = json.loads(export_publication_audit_json(events, project_id="p", well_id="w", interpretation_id="default"))
    assert payload["schema"] == AUDIT_EXPORT_SCHEMA
    assert payload["events"][0]["actor_name"] == "Alice"
    assert payload["events"][0]["actor_role"] == "author"

    csv_text = export_publication_audit_csv(events).decode("utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(csv_text)))
    assert rows[0]["actor_id"] == "author-1"

    workbook = load_workbook(io.BytesIO(export_publication_audit_xlsx(events, project_id="p", well_id="w", interpretation_id="default")))
    assert workbook["publication_audit"]["G2"].value == "Alice"
    assert workbook["metadata"]["B5"].value == 1
