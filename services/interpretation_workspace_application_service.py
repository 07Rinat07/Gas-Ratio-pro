from __future__ import annotations

"""Project-scoped application boundary for manual interpretation workspaces.

UI modules receive application operations from this service and never construct
persistence repositories directly. Context-specific operation gateways are
created lazily and cached inside the project-scoped service instance.
"""

from pathlib import Path
from typing import Any, MutableMapping

from projects.interpretation_catalog import InterpretationCatalogRepository
from projects.interpretation_access import InterpretationActor
from projects.interpretation_interval_batch import InterpretationIntervalBatchService
from projects.interpretation_interval_comparison import InterpretationIntervalTransferService
from projects.interpretation_interval_manager import InterpretationIntervalManager
from projects.interpretation_interval_merge import InterpretationIntervalMergeService
from projects.interpretation_interval_properties import InterpretationIntervalPropertiesService
from projects.interpretation_publication import InterpretationPublicationService
from projects.interpretation_interval_filter_presets import InterpretationIntervalFilterPresetRepository
from projects.interpretation_interval_types import InterpretationIntervalTypeRepository
from projects.interpretation_revisions import InterpretationRevisionRepository
from projects.repository import DEFAULT_PROJECTS_ROOT, safe_project_id
from projects.well_cards import safe_well_id
from projects.interpretation_intervals import _safe_interpretation_id


class _RepositoryOperations:
    """Narrow application-layer gateway around one repository instance."""

    __slots__ = ("_repository",)

    def __init__(self, repository: Any) -> None:
        self._repository = repository

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        attribute = getattr(self._repository, name)
        if not callable(attribute):
            raise AttributeError(name)
        return attribute


class InterpretationWorkspaceApplicationService:
    """Own repository lifecycle for one project interpretation workspace."""

    def __init__(
        self,
        *,
        project_id: str,
        root: Path | str = DEFAULT_PROJECTS_ROOT,
    ) -> None:
        self.root = Path(root)
        self.project_id = safe_project_id(project_id)
        self._catalogs: dict[str, _RepositoryOperations] = {}
        self._presets: dict[tuple[str, str], _RepositoryOperations] = {}
        self._revisions: dict[tuple[str, str], _RepositoryOperations] = {}
        self._types: _RepositoryOperations | None = None
        self._managers: dict[tuple[int, str, str], InterpretationIntervalManager] = {}
        self._properties: dict[tuple[int, str, str], InterpretationIntervalPropertiesService] = {}
        self._batch: dict[tuple[int, str, str], InterpretationIntervalBatchService] = {}

    def catalog(self, *, well_id: str) -> _RepositoryOperations:
        clean_well = safe_well_id(well_id)
        if clean_well not in self._catalogs:
            self._catalogs[clean_well] = _RepositoryOperations(
                InterpretationCatalogRepository(
                    root=self.root,
                    project_id=self.project_id,
                    well_id=clean_well,
                )
            )
        return self._catalogs[clean_well]

    def interval_types(self) -> _RepositoryOperations:
        if self._types is None:
            self._types = _RepositoryOperations(
                InterpretationIntervalTypeRepository(root=self.root, project_id=self.project_id)
            )
        return self._types

    def filter_presets(self, *, well_id: str, interpretation_id: str) -> _RepositoryOperations:
        key = (safe_well_id(well_id), _safe_interpretation_id(interpretation_id))
        if key not in self._presets:
            self._presets[key] = _RepositoryOperations(
                InterpretationIntervalFilterPresetRepository(
                    root=self.root,
                    project_id=self.project_id,
                    well_id=key[0],
                    interpretation_id=key[1],
                )
            )
        return self._presets[key]

    def revisions(self, *, well_id: str, interpretation_id: str) -> _RepositoryOperations:
        key = (safe_well_id(well_id), _safe_interpretation_id(interpretation_id))
        if key not in self._revisions:
            self._revisions[key] = _RepositoryOperations(
                InterpretationRevisionRepository(
                    root=self.root,
                    project_id=self.project_id,
                    well_id=key[0],
                    interpretation_id=key[1],
                )
            )
        return self._revisions[key]

    def interval_manager(
        self,
        *,
        state: MutableMapping[str, Any],
        well_id: str,
        interpretation_id: str,
    ) -> InterpretationIntervalManager:
        clean_well = safe_well_id(well_id)
        clean_interpretation = _safe_interpretation_id(interpretation_id)
        key = (id(state), clean_well, clean_interpretation)
        if key not in self._managers:
            self._managers[key] = InterpretationIntervalManager(
                state,
                root=self.root,
                project_id=self.project_id,
                well_id=clean_well,
                interpretation_id=clean_interpretation,
            )
        return self._managers[key]

    def interval_properties(
        self,
        *,
        state: MutableMapping[str, Any],
        well_id: str,
        interpretation_id: str,
    ) -> InterpretationIntervalPropertiesService:
        manager = self.interval_manager(
            state=state, well_id=well_id, interpretation_id=interpretation_id
        )
        key = (id(state), manager.well_id, manager.interpretation_id)
        if key not in self._properties:
            self._properties[key] = InterpretationIntervalPropertiesService(manager)
        return self._properties[key]

    def interval_batch(
        self,
        *,
        state: MutableMapping[str, Any],
        well_id: str,
        interpretation_id: str,
    ) -> InterpretationIntervalBatchService:
        manager = self.interval_manager(
            state=state, well_id=well_id, interpretation_id=interpretation_id
        )
        key = (id(state), manager.well_id, manager.interpretation_id)
        if key not in self._batch:
            self._batch[key] = InterpretationIntervalBatchService(manager)
        return self._batch[key]

    def publication(
        self,
        *,
        well_id: str,
        interpretation_id: str,
        actor: InterpretationActor,
    ) -> InterpretationPublicationService:
        return InterpretationPublicationService(
            root=self.root,
            project_id=self.project_id,
            well_id=safe_well_id(well_id),
            interpretation_id=_safe_interpretation_id(interpretation_id),
            actor=actor,
        )

    def interval_transfer(
        self,
        *,
        state: MutableMapping[str, Any],
        well_id: str,
        source_interpretation_id: str,
        target_interpretation_id: str,
    ) -> InterpretationIntervalTransferService:
        return InterpretationIntervalTransferService(
            state,
            root=self.root,
            project_id=self.project_id,
            well_id=safe_well_id(well_id),
            source_interpretation_id=_safe_interpretation_id(source_interpretation_id),
            target_interpretation_id=_safe_interpretation_id(target_interpretation_id),
        )

    def interval_merge(
        self,
        *,
        state: MutableMapping[str, Any],
        well_id: str,
        source_interpretation_id: str,
        target_interpretation_id: str,
        conflict_policy: str,
        reject_overlaps: bool,
    ) -> InterpretationIntervalMergeService:
        return InterpretationIntervalMergeService(
            state,
            root=self.root,
            project_id=self.project_id,
            well_id=safe_well_id(well_id),
            source_interpretation_id=_safe_interpretation_id(source_interpretation_id),
            target_interpretation_id=_safe_interpretation_id(target_interpretation_id),
            conflict_policy=conflict_policy,
            reject_overlaps=reject_overlaps,
        )

    def health_snapshot(self) -> dict[str, Any]:
        return {
            "service": type(self).__name__,
            "project_id": self.project_id,
            "root": str(self.root.resolve()),
            "catalog_scopes": len(self._catalogs),
            "preset_scopes": len(self._presets),
            "revision_scopes": len(self._revisions),
            "interval_types_initialized": self._types is not None,
            "manager_scopes": len(self._managers),
            "properties_scopes": len(self._properties),
            "batch_scopes": len(self._batch),
        }
