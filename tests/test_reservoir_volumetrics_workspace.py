from projects.reservoir_volumetrics_workspace import (
    VolumetricCell,
    build_reservoir_volumetrics_manifest,
    build_zone_volumetrics_table,
    cell_passes_cutoffs,
    compute_cell_volumes,
    create_reservoir_volumetrics_job,
    list_reservoir_volumetrics_jobs,
    render_reservoir_volumetrics_markdown,
    summarize_uncertainty,
    summarize_volumetrics_by_zone,
)


def _cells():
    return [
        VolumetricCell(cell_id="c1", zone="A", bulk_volume=100.0, porosity=0.2, water_saturation=0.3, oil_saturation=0.7, gas_saturation=0.0),
        VolumetricCell(cell_id="c2", zone="A", bulk_volume=50.0, porosity=0.1, water_saturation=0.7, oil_saturation=0.3, gas_saturation=0.0, pay_flag=False),
        VolumetricCell(cell_id="c3", zone="B", bulk_volume=80.0, porosity=0.25, water_saturation=0.2, oil_saturation=0.0, gas_saturation=0.8),
    ]


def test_compute_cell_volumes_foundation():
    values = compute_cell_volumes(_cells()[0])
    assert values["brv"] == 100.0
    assert values["nrv"] == 100.0
    assert values["pv"] == 20.0
    assert values["hcpv"] == 14.0
    assert values["ooip_stb"] > 0


def test_cell_cutoffs_can_require_pay_flag():
    assert cell_passes_cutoffs(_cells()[0], {"require_pay_flag": True}) is True
    assert cell_passes_cutoffs(_cells()[1], {"require_pay_flag": True}) is False


def test_summarize_volumetrics_by_zone():
    summaries = summarize_volumetrics_by_zone(_cells(), cutoffs={"min_porosity": 0.15})
    assert [item.zone for item in summaries] == ["A", "B"]
    zone_a = summaries[0]
    assert zone_a.brv == 150.0
    assert zone_a.nrv == 100.0
    assert zone_a.net_gross == round(100.0 / 150.0, 6)


def test_build_table_manifest_and_markdown():
    summaries = summarize_volumetrics_by_zone(_cells())
    table = build_zone_volumetrics_table(summaries)
    manifest = build_reservoir_volumetrics_manifest(summaries, project_id="demo", job_count=1)
    md = render_reservoir_volumetrics_markdown(summaries, manifest=manifest)
    assert len(table) == 2
    assert manifest.total_brv == 230.0
    assert "OOIP" in md
    assert "OGIP" in md


def test_uncertainty_summary_groups_cases():
    cells = [
        VolumetricCell(cell_id="l", zone="A", bulk_volume=100, porosity=0.15, water_saturation=0.4, case="low"),
        VolumetricCell(cell_id="b", zone="A", bulk_volume=100, porosity=0.2, water_saturation=0.3, case="base"),
        VolumetricCell(cell_id="h", zone="A", bulk_volume=100, porosity=0.25, water_saturation=0.2, case="high"),
    ]
    summaries = []
    for case in ("low", "base", "high"):
        summaries.extend(summarize_volumetrics_by_zone(cells, case=case))
    uncertainty = summarize_uncertainty(summaries)
    assert set(uncertainty) == {"base", "high", "low"}
    assert uncertainty["high"]["hcpv"] > uncertainty["low"]["hcpv"]


def test_job_registry(tmp_path):
    job = create_reservoir_volumetrics_job(tmp_path, "Project_A", job_id="vol-1", name="Base volumetrics")
    jobs = list_reservoir_volumetrics_jobs(tmp_path, "Project_A")
    assert job.job_id == "vol-1"
    assert len(jobs) == 1
