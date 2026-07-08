"""Application service layer for GAS RATIO PRO.

Services are the boundary between Streamlit UI and repositories/storage.
UI modules should call services instead of deleting files or mutating
repository manifests directly.
"""

from services.project_manager_service import (
    ProjectCreateResult,
    ProjectDeleteResult,
    ProjectManagerService,
)

__all__ = [
    "ProjectCreateResult",
    "ProjectDeleteResult",
    "ProjectManagerService",
    "WellDeleteResult",
    "WellManagerService",
    "WellSaveResult",
    "WellVersionDeleteResult",
]
from services.las_manager_service import LasManagerService

from services.dataset_manager_service import DatasetManagerService
