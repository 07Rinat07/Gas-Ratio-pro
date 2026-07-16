"""Application service for the LAS Viewer open-file workflow.

The workflow reuses the existing LAS importer and project LAS storage.  It
returns compact viewer/session contracts and never exposes a raw DataFrame to
UI session state.
"""

from __future__ import annotations

from dataclasses import dataclass
from tempfile import NamedTemporaryFile
from pathlib import Path
from typing import Any, BinaryIO, Mapping

from importers.las_importer import read_las
from projects.repository import DEFAULT_PROJECTS_ROOT, safe_project_id
from services.data_platform_application_service import DataPlatformApplicationService
from services.las_curve_metadata_service import DEPTH_MNEMONICS
from services.las_manager_service import LasManagerService
from services.las_viewer_session import LasViewerSession
from services.las_visualization_payload_service import LasVisualizationPayloadService


@dataclass(frozen=True, slots=True)
class LasViewerOpenResult:
    project_id: str
    las_id: str
    file_name: str
    row_count: int
    curve_count: int
    depth_curve: str
    quality_flags: tuple[str, ...]
    payload: Mapping[str, Any]
    viewer_state: Mapping[str, Any]
    dataset_id: str = ""
    dataset_version: int = 0
    dataset_validation_codes: tuple[str, ...] = ()
    dataset_duplicate_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "las.viewer.open_result",
            "version": "1.0",
            "project_id": self.project_id,
            "las_id": self.las_id,
            "file_name": self.file_name,
            "row_count": self.row_count,
            "curve_count": self.curve_count,
            "depth_curve": self.depth_curve,
            "quality_flags": list(self.quality_flags),
            "payload": dict(self.payload),
            "viewer_state": dict(self.viewer_state),
            "dataset_id": self.dataset_id,
            "dataset_version": self.dataset_version,
            "dataset_validation_codes": list(self.dataset_validation_codes),
            "dataset_duplicate_ids": list(self.dataset_duplicate_ids),
            "raw_dataframe_included": False,
        }


def _source_bytes(source: str | Path | BinaryIO | Any) -> bytes:
    if isinstance(source, (str, Path)):
        return Path(source).read_bytes()
    if hasattr(source, "getvalue"):
        return bytes(source.getvalue())
    if hasattr(source, "read"):
        position = source.tell() if hasattr(source, "tell") else None
        data = source.read()
        if position is not None and hasattr(source, "seek"):
            source.seek(position)
        return bytes(data)
    raise TypeError("Unsupported LAS input type.")


def _source_name(source: Any, explicit_name: str | None) -> str:
    if explicit_name and explicit_name.strip():
        return explicit_name.strip()
    if isinstance(source, (str, Path)):
        return Path(source).name
    name = str(getattr(source, "name", "") or "").strip()
    return Path(name).name if name else "source.las"


class LasViewerOpenWorkflow:
    """Validate, persist and open one LAS file in the existing viewer stack."""

    def __init__(self, root: Path | str = DEFAULT_PROJECTS_ROOT) -> None:
        self.root = Path(root)
        self.manager = LasManagerService(self.root)
        self.payload_service = LasVisualizationPayloadService(self.root, manager=self.manager)
        self.data_platform = DataPlatformApplicationService(self.root)

    def open(
        self,
        project_id: str,
        source: str | Path | BinaryIO | Any,
        *,
        file_name: str | None = None,
        well_name: str = "",
        curve_limit: int = 8,
        sample_limit: int = 240,
    ) -> LasViewerOpenResult:
        clean_project_id = safe_project_id(project_id)
        resolved_name = _source_name(source, file_name)
        if not resolved_name.lower().endswith(".las"):
            raise ValueError("LAS Viewer can open only .las files.")

        # Validation must happen before project storage is mutated.
        frame = read_las(source)
        if frame.empty:
            raise ValueError("LAS file does not contain data rows.")
        depth_columns = {str(column).strip().upper() for column in frame.columns}
        if not depth_columns.intersection({item.upper() for item in DEPTH_MNEMONICS}):
            raise ValueError("LAS file does not contain a supported depth channel.")

        data = _source_bytes(source)
        save_result = self.manager.save_file(
            project_id=clean_project_id,
            data=data,
            file_name=resolved_name,
            well_name=well_name,
            version_label="Opened in LAS Viewer",
            metadata={"source": "las_viewer_open_workflow"},
        )
        las_id = save_result.record.id
        temp_path: Path | None = None
        try:
            if isinstance(source, (str, Path)):
                registration_source = Path(source)
            else:
                suffix = Path(resolved_name).suffix or ".las"
                with NamedTemporaryFile(mode="wb", suffix=suffix, delete=False) as handle:
                    handle.write(data)
                    temp_path = Path(handle.name)
                registration_source = temp_path
            registration = self.data_platform.register_source_file_result(
                project_id=clean_project_id,
                source=registration_source,
                format_id="las",
                well_id="",
                metadata={
                    "source": "las_viewer_open_workflow",
                    "las_record_id": las_id,
                    "well_name_override": well_name,
                },
            )
        except Exception:
            self.manager.delete_file(clean_project_id, las_id)
            raise
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
        payload_model = self.payload_service.build(
            clean_project_id,
            las_id,
            curve_limit=curve_limit,
            sample_limit=sample_limit,
        )
        payload = payload_model.to_dict()
        if "missing_depth_curve" in payload_model.quality_flags:
            self.manager.delete_file(clean_project_id, las_id)
            raise ValueError("LAS file does not contain a supported depth channel.")
        if "no_numeric_visualization_curves" in payload_model.quality_flags:
            self.manager.delete_file(clean_project_id, las_id)
            raise ValueError("LAS file does not contain numeric curves for visualization.")

        viewer_state = LasViewerSession(payload).state.to_dict()
        return LasViewerOpenResult(
            project_id=clean_project_id,
            las_id=las_id,
            file_name=resolved_name,
            row_count=len(frame),
            curve_count=len(payload_model.curves),
            depth_curve=payload_model.depth_curve,
            quality_flags=payload_model.quality_flags,
            payload=payload,
            viewer_state=viewer_state,
            dataset_id=registration.manifest.dataset_id,
            dataset_version=registration.manifest.version,
            dataset_validation_codes=tuple(item.code for item in registration.validation_findings),
            dataset_duplicate_ids=registration.duplicate_dataset_ids,
        )
