import pandas as pd

from las_editor.advanced_saturation_models import run_advanced_saturation_models
from las_editor.petrophysical_crossplot_workspace import run_petrophysical_crossplot_workspace
from las_editor.petrophysical_report_package import (
    PETROPHYSICAL_REPORT_PACKAGE_SCHEMA,
    build_petrophysical_report_manifest,
    build_petrophysical_report_package,
    render_petrophysical_report_markdown,
    report_issue_table_rows,
    report_section_table_rows,
    validate_report_package,
)
from las_editor.petrophysical_workspace import run_petrophysical_workspace
from las_editor.reservoir_property_calculator import run_reservoir_property_calculator


def sample_df():
    return pd.DataFrame(
        {
            "DEPT": [1000.0, 1000.5, 1001.0, 1001.5],
            "GR": [45.0, 55.0, 80.0, 110.0],
            "RT": [30.0, 20.0, 8.0, 2.0],
            "RHOB": [2.25, 2.30, 2.45, 2.60],
            "NPHI": [0.22, 0.20, 0.15, 0.08],
            "PHIE": [0.20, 0.18, 0.12, 0.05],
            "SW_ARCHIE": [0.30, 0.40, 0.70, 0.90],
            "NG": [1.0, 0.8, 0.5, 0.0],
            "PAY": [1, 1, 0, 0],
        }
    )


def test_build_package_from_all_major_petrophysical_outputs():
    data = sample_df()
    petro = run_petrophysical_workspace(data, source_references=("docs/sources/gladkov-3d-modeling.pdf",))
    saturation = run_advanced_saturation_models(petro.data)
    crossplots = run_petrophysical_crossplot_workspace(petro.data)
    intervals = petro
    volumes = run_reservoir_property_calculator(petro.data, intervals=[{"name": "A", "top": 1000.0, "base": 1001.5}])

    package = build_petrophysical_report_package(
        well_name="WELL-01",
        petrophysical_result=petro,
        saturation_result=saturation,
        crossplot_result=crossplots,
        interval_result=intervals,
        reservoir_property_result=volumes,
        source_references=("docs/sources/lab-4-property-cubes.pdf",),
    )

    assert package.schema == PETROPHYSICAL_REPORT_PACKAGE_SCHEMA
    assert package.well_name == "WELL-01"
    assert len(package.sections) == 5
    assert any(section.section_id == "reservoir_volumes" for section in package.sections)
    assert "docs/sources/lab-4-property-cubes.pdf" in package.source_references
    assert report_section_table_rows(package.sections)


def test_manifest_report_and_issue_rows_are_rendered():
    package = build_petrophysical_report_package(well_name="WELL-MISSING")
    manifest = build_petrophysical_report_manifest(package)
    report = render_petrophysical_report_markdown(package)

    assert manifest["schema"].endswith("/v1")
    assert manifest["section_count"] == 5
    assert "Petrophysical Report Package" in report
    assert "missing" in report
    assert report_issue_table_rows(package.issues)
    assert validate_report_package(package.sections)
