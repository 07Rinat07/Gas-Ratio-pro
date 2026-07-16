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
from projects.interpretation_interval_display_settings import (
    InterpretationIntervalDisplaySettings,
    load_interpretation_interval_display_settings,
    normalize_interval_display_settings,
    save_interpretation_interval_display_settings,
)
from projects.repository import DEFAULT_PROJECTS_ROOT, safe_project_id
from projects.well_cards import safe_well_id
from projects.interpretation_intervals import _safe_interpretation_id


class _FilterPresetUseCases:
    __slots__ = ("_repository",)

    def __init__(self, repository: InterpretationIntervalFilterPresetRepository) -> None:
        self._repository = repository

    def list(self): return self._repository.list()
    def get(self, preset_id: str): return self._repository.get(preset_id)
    def save(self, **values: Any): return self._repository.save(**values)
    def delete(self, preset_id: str): return self._repository.delete(preset_id)
    def replace_all(self, presets: Any): return self._repository.replace_all(presets)


class _RevisionUseCases:
    __slots__ = ("_repository",)

    def __init__(self, repository: InterpretationRevisionRepository) -> None:
        self._repository = repository

    def list(self): return self._repository.list()
    def create(self, **values: Any): return self._repository.create(**values)
    def compare(self, revision_id: str): return self._repository.compare(revision_id)
    def restore(self, revision_id: str, **values: Any): return self._repository.restore(revision_id, **values)
    def delete(self, revision_id: str): return self._repository.delete(revision_id)
    def prune(self, **values: Any): return self._repository.prune(**values)


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
        self._catalogs: dict[str, InterpretationCatalogRepository] = {}
        self._presets: dict[tuple[str, str], InterpretationIntervalFilterPresetRepository] = {}
        self._revision_scopes: dict[tuple[str, str], InterpretationRevisionRepository] = {}
        self._types: InterpretationIntervalTypeRepository | None = None
        self._managers: dict[tuple[int, str, str], InterpretationIntervalManager] = {}
        self._properties: dict[tuple[int, str, str], InterpretationIntervalPropertiesService] = {}
        self._batch: dict[tuple[int, str, str], InterpretationIntervalBatchService] = {}
        self._preset_use_cases: dict[tuple[str, str], _FilterPresetUseCases] = {}
        self._revision_use_cases: dict[tuple[str, str], _RevisionUseCases] = {}

    def _catalog(self, *, well_id: str) -> InterpretationCatalogRepository:
        clean_well = safe_well_id(well_id)
        if clean_well not in self._catalogs:
            self._catalogs[clean_well] = InterpretationCatalogRepository(
                    root=self.root,
                    project_id=self.project_id,
                    well_id=clean_well,
                )
        return self._catalogs[clean_well]

    def _interval_types(self) -> InterpretationIntervalTypeRepository:
        if self._types is None:
            self._types = InterpretationIntervalTypeRepository(root=self.root, project_id=self.project_id)
        return self._types

    def _filter_presets(self, *, well_id: str, interpretation_id: str) -> InterpretationIntervalFilterPresetRepository:
        key = (safe_well_id(well_id), _safe_interpretation_id(interpretation_id))
        if key not in self._presets:
            self._presets[key] = InterpretationIntervalFilterPresetRepository(
                    root=self.root,
                    project_id=self.project_id,
                    well_id=key[0],
                    interpretation_id=key[1],
                )
        return self._presets[key]

    def _revision_repository(self, *, well_id: str, interpretation_id: str) -> InterpretationRevisionRepository:
        key = (safe_well_id(well_id), _safe_interpretation_id(interpretation_id))
        if key not in self._revision_scopes:
            self._revision_scopes[key] = InterpretationRevisionRepository(
                    root=self.root,
                    project_id=self.project_id,
                    well_id=key[0],
                    interpretation_id=key[1],
                )
        return self._revision_scopes[key]

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


    def filter_preset_use_cases(self, *, well_id: str, interpretation_id: str) -> _FilterPresetUseCases:
        key = (safe_well_id(well_id), _safe_interpretation_id(interpretation_id))
        if key not in self._preset_use_cases:
            self._preset_use_cases[key] = _FilterPresetUseCases(
                self._filter_presets(well_id=key[0], interpretation_id=key[1])
            )
        return self._preset_use_cases[key]

    def revision_use_cases(self, *, well_id: str, interpretation_id: str) -> _RevisionUseCases:
        key = (safe_well_id(well_id), _safe_interpretation_id(interpretation_id))
        if key not in self._revision_use_cases:
            self._revision_use_cases[key] = _RevisionUseCases(
                self._revision_repository(well_id=key[0], interpretation_id=key[1])
            )
        return self._revision_use_cases[key]

    # Catalog use cases -------------------------------------------------
    def list_interpretations(self, *, well_id: str):
        return self._catalog(well_id=well_id).list()

    def get_interpretation(self, interpretation_id: str, *, well_id: str):
        return self._catalog(well_id=well_id).get(interpretation_id)

    def create_interpretation(self, *, well_id: str, **values: Any):
        return self._catalog(well_id=well_id).create(**values)

    def update_interpretation(self, interpretation_id: str, *, well_id: str, **values: Any):
        return self._catalog(well_id=well_id).update(interpretation_id, **values)

    def duplicate_interpretation(self, interpretation_id: str, *, well_id: str, **values: Any):
        return self._catalog(well_id=well_id).duplicate(interpretation_id, **values)

    def delete_interpretation(self, interpretation_id: str, *, well_id: str):
        return self._catalog(well_id=well_id).delete(interpretation_id)

    def list_deleted_interpretations(self, *, well_id: str):
        return self._catalog(well_id=well_id).list_deleted()

    def restore_interpretation(self, interpretation_id: str, *, well_id: str):
        return self._catalog(well_id=well_id).restore(interpretation_id)

    # Interval type use cases ------------------------------------------
    def list_interval_types(self):
        return self._interval_types().list()

    def upsert_interval_type(self, *args: Any, **kwargs: Any):
        return self._interval_types().upsert(*args, **kwargs)

    def interval_type_usage(self, *args: Any, **kwargs: Any):
        return self._interval_types().usage(*args, **kwargs)

    def preview_interval_type_reassignment(self, *args: Any, **kwargs: Any):
        return self._interval_types().preview_reassignment(*args, **kwargs)

    def reassign_and_delete_interval_type(self, *args: Any, **kwargs: Any):
        return self._interval_types().reassign_and_delete(*args, **kwargs)

    def delete_interval_type(self, *args: Any, **kwargs: Any):
        return self._interval_types().delete(*args, **kwargs)

    def count_interval_type_operations(self, *args: Any, **kwargs: Any):
        return self._interval_types().count_operations(*args, **kwargs)

    def list_interval_type_operations(self, *args: Any, **kwargs: Any):
        return self._interval_types().list_operations(*args, **kwargs)

    def get_interval_type_operation(self, *args: Any, **kwargs: Any):
        return self._interval_types().get_operation(*args, **kwargs)

    def undo_last_interval_type_reassignment(self):
        return self._interval_types().undo_last_reassignment()

    def reset_interval_type_defaults(self):
        return self._interval_types().reset_defaults()

    # Filter preset use cases ------------------------------------------
    def list_filter_presets(self, *, well_id: str, interpretation_id: str):
        return self._filter_presets(well_id=well_id, interpretation_id=interpretation_id).list()

    def get_filter_preset(self, preset_id: str, *, well_id: str, interpretation_id: str):
        return self._filter_presets(well_id=well_id, interpretation_id=interpretation_id).get(preset_id)

    def save_filter_preset(self, *, well_id: str, interpretation_id: str, **values: Any):
        return self._filter_presets(well_id=well_id, interpretation_id=interpretation_id).save(**values)

    def delete_filter_preset(self, preset_id: str, *, well_id: str, interpretation_id: str):
        return self._filter_presets(well_id=well_id, interpretation_id=interpretation_id).delete(preset_id)

    def replace_filter_presets(self, presets: Any, *, well_id: str, interpretation_id: str):
        return self._filter_presets(well_id=well_id, interpretation_id=interpretation_id).replace_all(presets)

    # Revision use cases -----------------------------------------------
    def list_revisions(self, *, well_id: str, interpretation_id: str):
        return self._revision_repository(well_id=well_id, interpretation_id=interpretation_id).list()

    def create_revision(self, *, well_id: str, interpretation_id: str, **values: Any):
        return self._revision_repository(well_id=well_id, interpretation_id=interpretation_id).create(**values)

    def compare_revision(self, revision_id: str, *, well_id: str, interpretation_id: str):
        return self._revision_repository(well_id=well_id, interpretation_id=interpretation_id).compare(revision_id)

    def restore_revision(self, revision_id: str, *, well_id: str, interpretation_id: str, **values: Any):
        return self._revision_repository(well_id=well_id, interpretation_id=interpretation_id).restore(revision_id, **values)

    def delete_revision(self, revision_id: str, *, well_id: str, interpretation_id: str):
        return self._revision_repository(well_id=well_id, interpretation_id=interpretation_id).delete(revision_id)

    def prune_revisions(self, *, well_id: str, interpretation_id: str, **values: Any):
        return self._revision_repository(well_id=well_id, interpretation_id=interpretation_id).prune(**values)


    def list_intervals(
        self,
        *,
        state: MutableMapping[str, Any],
        well_id: str,
        interpretation_id: str,
    ):
        """Return manual intervals without exposing the coordination manager to UI code."""
        return self.interval_manager(
            state=state, well_id=well_id, interpretation_id=interpretation_id
        ).list_intervals()

    def load_display_settings(
        self,
        *,
        well_id: str,
        interpretation_id: str,
    ) -> InterpretationIntervalDisplaySettings:
        return load_interpretation_interval_display_settings(
            root=self.root,
            project_id=self.project_id,
            well_id=safe_well_id(well_id),
            interpretation_id=_safe_interpretation_id(interpretation_id),
        )

    def save_display_settings(
        self,
        *,
        well_id: str,
        interpretation_id: str,
        visible: object,
        opacity: object,
    ) -> InterpretationIntervalDisplaySettings:
        normalized = normalize_interval_display_settings(
            visible=visible, opacity=opacity
        )
        save_interpretation_interval_display_settings(
            normalized,
            root=self.root,
            project_id=self.project_id,
            well_id=safe_well_id(well_id),
            interpretation_id=_safe_interpretation_id(interpretation_id),
        )
        return normalized

    def health_snapshot(self) -> dict[str, Any]:
        return {
            "service": type(self).__name__,
            "project_id": self.project_id,
            "root": str(self.root.resolve()),
            "catalog_scopes": len(self._catalogs),
            "preset_scopes": len(self._presets),
            "revision_scopes": len(self._revision_scopes),
            "interval_types_initialized": self._types is not None,
            "manager_scopes": len(self._managers),
            "properties_scopes": len(self._properties),
            "batch_scopes": len(self._batch),
            "preset_use_case_scopes": len(self._preset_use_cases),
            "revision_use_case_scopes": len(self._revision_use_cases),
        }
