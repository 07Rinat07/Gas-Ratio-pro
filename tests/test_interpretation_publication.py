from pathlib import Path

import pytest

from projects.interpretation_interval_manager import InterpretationIntervalManager
from projects.interpretation_publication import InterpretationPublicationService
from projects.interpretation_revisions import InterpretationRevisionRepository


def _service(tmp_path: Path) -> InterpretationPublicationService:
    return InterpretationPublicationService(root=tmp_path, project_id="p", well_id="w", interpretation_id="default")


def _manager(tmp_path: Path) -> InterpretationIntervalManager:
    return InterpretationIntervalManager({}, root=tmp_path, project_id="p", well_id="w", interpretation_id="default")


def test_full_publication_workflow_and_history(tmp_path: Path) -> None:
    manager = _manager(tmp_path)
    manager.create(label="A", top=100, base=110)
    revisions = InterpretationRevisionRepository(root=tmp_path, project_id="p", well_id="w", interpretation_id="default")
    revision = revisions.create(name="Release 1", note="validated")
    service = _service(tmp_path)
    assert service.state().status == "draft"
    service.submit_for_review(comment="ready")
    service.approve(comment="approved")
    published = service.publish(revision_id=revision.id, comment="release")
    assert published.status == "published"
    assert published.published_revision_id == revision.id
    assert [event.action for event in published.events] == ["submit_for_review", "approve", "publish"]
    service.unpublish(comment="correction")
    reopened = service.reopen(comment="edit")
    assert reopened.status == "draft"


def test_publish_requires_revision_matching_current_state(tmp_path: Path) -> None:
    manager = _manager(tmp_path)
    manager.create(label="A", top=100, base=110)
    revisions = InterpretationRevisionRepository(root=tmp_path, project_id="p", well_id="w", interpretation_id="default")
    revision = revisions.create(name="Old")
    manager.create(label="B", top=120, base=130)
    service = _service(tmp_path)
    service.submit_for_review()
    service.approve()
    with pytest.raises(ValueError, match="не соответствует"):
        service.publish(revision_id=revision.id)


def test_approved_and_published_interpretations_are_read_only(tmp_path: Path) -> None:
    manager = _manager(tmp_path)
    interval = manager.create(label="A", top=100, base=110)
    service = _service(tmp_path)
    service.submit_for_review()
    service.approve()
    with pytest.raises(ValueError, match="только для чтения"):
        manager.update(interval.id, label="B", top=100, base=110)
    with pytest.raises(ValueError):
        manager.delete(interval.id)
    service.reopen()
    assert manager.update(interval.id, label="B", top=100, base=110).label == "B"


def test_invalid_transitions_are_rejected(tmp_path: Path) -> None:
    service = _service(tmp_path)
    with pytest.raises(ValueError, match="недоступна"):
        service.approve()
    service.submit_for_review()
    with pytest.raises(ValueError):
        service.publish(revision_id="missing")


def test_duplicate_does_not_copy_publication_lock(tmp_path: Path) -> None:
    from projects.interpretation_catalog import InterpretationCatalogRepository

    catalog = InterpretationCatalogRepository(root=tmp_path, project_id="p", well_id="w")
    catalog.list()
    manager = _manager(tmp_path)
    manager.create(label="A", top=100, base=110)
    service = _service(tmp_path)
    service.submit_for_review()
    service.approve()
    duplicate = catalog.duplicate("default", name="Copy", target_id="copy")
    copy_service = InterpretationPublicationService(
        root=tmp_path, project_id="p", well_id="w", interpretation_id=duplicate.id
    )
    assert copy_service.state().status == "draft"
