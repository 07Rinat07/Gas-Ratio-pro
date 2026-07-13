from __future__ import annotations

"""Project-scoped persistence for unfinished Professional Export Wizard drafts.

The repository stores only user-entered export preferences. It never stores
engineering dataframes, calculated results, rendered files, or credentials.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Mapping

from reports.export_wizard import ExportWizardState, ExportWizardStep

EXPORT_WIZARD_DRAFT_SCHEMA = "gas-ratio-pro/export-wizard-draft/v1"
_SAFE_ID = re.compile(r"[^A-Za-z0-9._-]+")
_ALLOWED_SECTIONS = frozenset({"plots", "visualizations", "results", "conclusion"})


@dataclass(frozen=True)
class ExportWizardDraft:
    project_id: str
    wizard: ExportWizardState
    report_mode_id: str = "full_engineering"
    template_id: str = "engineering"
    report_title: str = "Gas Ratio Professional Report"
    sections: tuple[str, ...] = ("plots", "visualizations", "results", "conclusion")
    include_technical_appendix: bool = True
    show_page_chrome: bool = True
    print_mode: str = "Текущий интервал графиков"
    depth_top: float | None = None
    depth_bottom: float | None = None
    updated_at: str = ""

    def normalized(self) -> "ExportWizardDraft":
        project_id = str(self.project_id or "").strip()
        if not project_id:
            raise ValueError("project_id is required")
        sections = tuple(item for item in self.sections if item in _ALLOWED_SECTIONS)
        top = _finite_or_none(self.depth_top)
        bottom = _finite_or_none(self.depth_bottom)
        if top is not None and bottom is not None and top > bottom:
            top, bottom = bottom, top
        return ExportWizardDraft(
            project_id=project_id,
            wizard=self.wizard,
            report_mode_id=str(self.report_mode_id or "full_engineering").strip(),
            template_id=str(self.template_id or "engineering").strip(),
            report_title=str(self.report_title or "").strip() or "Gas Ratio Professional Report",
            sections=sections,
            include_technical_appendix=bool(self.include_technical_appendix),
            show_page_chrome=bool(self.show_page_chrome),
            print_mode=str(self.print_mode or "Текущий интервал графиков").strip(),
            depth_top=top,
            depth_bottom=bottom,
            updated_at=self.updated_at or datetime.now(timezone.utc).isoformat(),
        )

    def to_dict(self) -> dict[str, Any]:
        value = self.normalized()
        return {
            "schema": EXPORT_WIZARD_DRAFT_SCHEMA,
            "project_id": value.project_id,
            "updated_at": value.updated_at,
            "wizard": {
                "step": int(value.wizard.step),
                "source_label": value.wizard.source_label,
                "project_label": value.wizard.project_label,
                "profile": value.wizard.profile,
                "export_format": value.wizard.export_format,
                "include_figures": value.wizard.include_figures,
                "output_dir": str(value.wizard.output_dir),
                "base_name_parts": list(value.wizard.base_name_parts),
            },
            "report": {
                "mode_id": value.report_mode_id,
                "template_id": value.template_id,
                "title": value.report_title,
                "sections": list(value.sections),
                "include_technical_appendix": value.include_technical_appendix,
                "show_page_chrome": value.show_page_chrome,
            },
            "print": {
                "mode": value.print_mode,
                "depth_top": value.depth_top,
                "depth_bottom": value.depth_bottom,
            },
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ExportWizardDraft":
        if payload.get("schema") != EXPORT_WIZARD_DRAFT_SCHEMA:
            raise ValueError("unsupported export wizard draft schema")
        wizard = payload.get("wizard")
        report = payload.get("report")
        print_settings = payload.get("print")
        if not isinstance(wizard, Mapping) or not isinstance(report, Mapping) or not isinstance(print_settings, Mapping):
            raise ValueError("invalid export wizard draft payload")
        state = ExportWizardState(
            step=ExportWizardStep(int(wizard.get("step", int(ExportWizardStep.SOURCE)))),
            source_label=str(wizard.get("source_label", "")),
            project_label=str(wizard.get("project_label", "")),
            profile=str(wizard.get("profile", "engineering")),
            export_format=str(wizard.get("export_format", "pdf")),
            include_figures=bool(wizard.get("include_figures", True)),
            output_dir=Path(str(wizard.get("output_dir", "exports"))),
            base_name_parts=tuple(str(item) for item in wizard.get("base_name_parts", ()) if str(item).strip()),
        )
        return cls(
            project_id=str(payload.get("project_id", "")),
            wizard=state,
            report_mode_id=str(report.get("mode_id", "full_engineering")),
            template_id=str(report.get("template_id", "engineering")),
            report_title=str(report.get("title", "Gas Ratio Professional Report")),
            sections=tuple(str(item) for item in report.get("sections", ())),
            include_technical_appendix=bool(report.get("include_technical_appendix", True)),
            show_page_chrome=bool(report.get("show_page_chrome", True)),
            print_mode=str(print_settings.get("mode", "Текущий интервал графиков")),
            depth_top=print_settings.get("depth_top"),
            depth_bottom=print_settings.get("depth_bottom"),
            updated_at=str(payload.get("updated_at", "")),
        ).normalized()


class ExportWizardDraftRepository:
    def __init__(self, root_dir: Path | str) -> None:
        self.root_dir = Path(root_dir)

    def path_for(self, project_id: str) -> Path:
        safe_id = _SAFE_ID.sub("_", str(project_id or "").strip()).strip("._")
        if not safe_id:
            raise ValueError("project_id is required")
        return self.root_dir / safe_id / "export_wizard_draft.json"

    def save(self, draft: ExportWizardDraft) -> Path:
        value = draft.normalized()
        target = self.path_for(value.project_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(value.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(target)
        return target

    def load(self, project_id: str) -> ExportWizardDraft | None:
        target = self.path_for(project_id)
        if not target.exists():
            return None
        payload = json.loads(target.read_text(encoding="utf-8"))
        draft = ExportWizardDraft.from_dict(payload)
        if draft.project_id != str(project_id).strip():
            raise ValueError("export wizard draft belongs to another project")
        return draft

    def delete(self, project_id: str) -> bool:
        target = self.path_for(project_id)
        if not target.exists():
            return False
        target.unlink()
        return True


def _finite_or_none(value: object) -> float | None:
    if value is None:
        return None
    number = float(value)
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number
