from services.project_manager_service import ProjectManagerService


def test_project_manager_service_accepts_include_archived_keyword(tmp_path):
    service = ProjectManagerService(tmp_path)

    records = service.list_projects(include_archived=True)

    assert records
    assert records[0].id == "default"
