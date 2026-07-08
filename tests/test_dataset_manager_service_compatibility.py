from __future__ import annotations

from pathlib import Path

from services.dataset_manager_service import DatasetManagerService
from projects.datasets import save_project_mud_log_dataset
from projects.las_files import save_project_las_file


def test_dataset_manager_contract_exposes_all_ui_sections(tmp_path: Path) -> None:
    service = DatasetManagerService(tmp_path)

    assert service.supported_sections() == ("las", "csv", "excel", "core", "mud_log", "production")
    assert set(service.section_specs) == set(service.supported_sections())


def test_dataset_manager_list_dataset_cards_is_ui_ready_for_mud_log(tmp_path: Path) -> None:
    save_project_mud_log_dataset(
        b"DEPTH,C1\n100,1\n",
        root=tmp_path,
        project_id="demo",
        file_name="mud.csv",
        name="Mud UI Card",
    )

    cards = DatasetManagerService(tmp_path).list_dataset_cards("demo", "mud_log")

    assert len(cards) == 1
    assert cards[0].kind == "Mud Log"
    assert cards[0].name == "Mud UI Card"


def test_dataset_manager_list_dataset_cards_supports_las(tmp_path: Path) -> None:
    save_project_las_file(
        b"~Version\nVERS. 2.0\n~Well\nSTRT.M 100\nSTOP.M 101\nSTEP.M 1\nNULL. -999.25\n~Curve\nDEPT.M : Depth\nGR.API : Gamma Ray\n~Ascii\n100 50\n101 51\n",
        root=tmp_path,
        project_id="demo",
        file_name="well.las",
        well_name="Well Contract",
    )

    cards = DatasetManagerService(tmp_path).list_dataset_cards("demo", "las")

    assert len(cards) == 1
    assert cards[0].kind == "LAS"


def test_dataset_manager_streamlit_ui_uses_service_layer_for_dataset_cards() -> None:
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")
    manager_block = source.split("def _render_project_dataset_manager", 1)[1].split("def _render_project_manager_tools", 1)[0]

    assert "service = _dataset_manager_service()" in manager_block
    assert "service.list_dataset_cards" in manager_block
    assert "list_project_mud_log_datasets(" not in manager_block
    assert "list_project_las_datasets(" not in manager_block
