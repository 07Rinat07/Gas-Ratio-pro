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


def test_petrophysical_professional_vsh_methods_and_porosity() -> None:
    from projects.interpretation_workspace import (
        calculate_combined_density_neutron_porosity,
        calculate_density_porosity,
        calculate_sonic_porosity,
        calculate_vsh_from_gr,
    )

    frame = pd.DataFrame({"GR": [30, 90, 150], "RHOB": [2.1, 2.3, 2.65], "NPHI": [0.25, 20, 0.05], "DT": [80, 100, 55.5]})

    linear = calculate_vsh_from_gr(frame, "GR", gr_min=30, gr_max=150, method="linear")
    larionov = calculate_vsh_from_gr(frame, "GR", gr_min=30, gr_max=150, method="larionov_tertiary")
    steiber = calculate_vsh_from_gr(frame, "GR", gr_min=30, gr_max=150, method="steiber")

    assert linear.round(2).tolist() == [0.0, 0.5, 1.0]
    assert larionov.iloc[1] < linear.iloc[1]
    assert steiber.iloc[2] == 1.0
    assert calculate_density_porosity(frame, "RHOB").round(3).tolist()[0] == 0.333
    assert calculate_sonic_porosity(frame, "DT").between(0, 1).all()
    assert calculate_combined_density_neutron_porosity(frame, "RHOB", "NPHI").between(0, 1).all()


def test_petrophysical_professional_saturation_permeability_and_net_pay() -> None:
    from projects.interpretation_workspace import (
        InterpretationCutoffs,
        PetrophysicalParameters,
        build_interpretation_workspace,
        calculate_net_pay_summary,
        calculate_permeability,
        calculate_water_saturation,
    )

    frame = pd.DataFrame(
        {
            "DEPT": [1000.0, 1000.5, 1001.0],
            "GR": [35, 70, 145],
            "PHIT": [0.24, 0.18, 0.08],
            "RT": [40, 12, 2],
        }
    )
    params = PetrophysicalParameters(rw=0.06, rsh=2.5)
    interpreted = build_interpretation_workspace(
        frame,
        gr_min=30,
        gr_max=150,
        parameters=params,
        vsh_method="clavier",
        saturation_method="simandoux",
        permeability_method="timur",
        cutoffs=InterpretationCutoffs(vsh_max=0.5, phie_min=0.08, sw_max=0.75),
    )

    assert {"VSH", "PHIE", "SW", "PERM", "net_pay_flag", "lithology_hint"}.issubset(interpreted.columns)
    assert interpreted["SW"].dropna().between(0, 1).all()
    assert interpreted["PERM"].dropna().ge(0).all()

    indonesia = calculate_water_saturation(interpreted, method="indonesia", parameters=params)
    coates = calculate_permeability(interpreted.assign(SW=indonesia), method="coates", parameters=params)
    assert indonesia.dropna().between(0, 1).all()
    assert coates.dropna().ge(0).all()

    summary = calculate_net_pay_summary(interpreted, depth_curve="DEPT")
    assert summary.rows == 3
    assert summary.gross_thickness == 1.5
    assert summary.net_pay_thickness >= 0
