import pandas as pd

from projects.interpretation_workspace import (
    build_interpretation_workspace,
    calculate_archie_sw,
    calculate_effective_porosity,
    calculate_vsh_from_gr,
    list_interpretation_records,
    save_interpretation_record,
    summarize_interpretation_workspace,
)
from projects.project_manager import create_project


def test_interpretation_workspace_calculates_petrophysical_curves() -> None:
    frame = pd.DataFrame({"GR": [30, 90, 150], "PHIT": [0.25, 0.20, 0.10], "RT": [30, 10, 2]})

    interpreted = build_interpretation_workspace(frame, gr_min=30, gr_max=150)

    assert interpreted["VSH"].round(2).tolist() == [0.0, 0.5, 1.0]
    assert interpreted["PHIE"].round(3).tolist() == [0.25, 0.1, 0.0]
    assert "SW" in interpreted.columns
    assert interpreted["reservoir_flag"].tolist() == [True, False, False]


def test_interpretation_workspace_helpers_are_safe_for_missing_data() -> None:
    frame = pd.DataFrame({"GR": [60, None], "PHIT": [0.2, 0.1]})

    assert calculate_vsh_from_gr(frame, "GR", gr_min=30, gr_max=150).round(2).tolist()[0] == 0.25
    assert calculate_effective_porosity(frame.assign(VSH=[0.25, 0.5]), "PHIT", "VSH").round(3).tolist() == [0.15, 0.05]
    assert calculate_archie_sw(frame, "RT", "PHIE").empty


def test_interpretation_workspace_summary_and_project_records(tmp_path) -> None:
    project = create_project(tmp_path, name="Interpretation Demo")
    interpreted = build_interpretation_workspace(
        pd.DataFrame({"GR": [40, 140], "PHIT": [0.22, 0.08], "RT": [20, 3]}),
        gr_min=30,
        gr_max=150,
    )

    summary = summarize_interpretation_workspace(interpreted)
    assert summary.rows == 2
    assert summary.reservoir_rows == 1

    saved = save_interpretation_record(tmp_path, project.id, "Reservoir pass", interpreted, source_type="las", source_id="las-1", well_id="well-a")
    records = list_interpretation_records(tmp_path, project.id)

    assert records[0].id == saved.id
    assert records[0].net_pay_rows >= 0
