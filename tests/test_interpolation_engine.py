from projects.interpolation_engine import (
    GridNode,
    InterpolationJobSpec,
    build_interpolated_cells_table,
    build_interpolation_job_table,
    build_regular_grid,
    interpolate_idw,
    interpolate_nearest,
    interpolate_simple_kriging_foundation,
    list_interpolation_jobs,
    render_interpolation_markdown,
    run_interpolation,
    save_interpolation_job,
    seed_interpolation_engine,
    summarize_interpolation_result,
)


def test_regular_grid_and_nearest_interpolation():
    samples = [(0, 0, 10), (10, 0, 20)]
    grid = build_regular_grid(x_min=0, x_max=10, y_min=0, y_max=0, nx=3, ny=1)
    cells = interpolate_nearest(samples, grid)
    assert len(cells) == 3
    assert cells[0].value == 10
    assert cells[-1].value == 20
    assert cells[0].method == "nearest"


def test_idw_interpolation_midpoint():
    samples = [(0, 0, 10), (10, 0, 20)]
    cells = interpolate_idw(samples, [GridNode(5, 0)], power=2, max_neighbors=2)
    assert len(cells) == 1
    assert cells[0].value == 15
    assert cells[0].neighbor_count == 2


def test_idw_exact_sample_has_exact_value():
    samples = [(0, 0, 10), (10, 0, 20)]
    cells = run_interpolation(samples, [GridNode(0, 0)], method="idw")
    assert cells[0].value == 10
    assert cells[0].confidence == 1.0


def test_simple_kriging_foundation_returns_cells():
    samples = [(0, 0, 10), (10, 0, 20), (0, 10, 30)]
    cells = interpolate_simple_kriging_foundation(samples, [GridNode(5, 5)], max_neighbors=3)
    assert len(cells) == 1
    assert cells[0].method == "simple_kriging_foundation"
    assert cells[0].value is not None


def test_result_summary_and_table():
    cells = interpolate_idw([(0, 0, 10), (10, 0, 20)], [GridNode(5, 0), GridNode(0, 0)])
    table = build_interpolated_cells_table(cells)
    summary = summarize_interpolation_result(cells)
    assert table[0]["method"] == "idw"
    assert summary["cell_count"] == 2
    assert summary["estimated_count"] == 2


def test_jobs_persistence_and_markdown(tmp_path):
    seed_interpolation_engine(tmp_path, "Demo", author="tester", overwrite=True)
    save_interpolation_job(
        tmp_path,
        "Demo",
        InterpolationJobSpec(name="SW kriging", property_name="SW", method="simple_kriging_foundation"),
    )
    jobs = list_interpolation_jobs(tmp_path, "Demo")
    table = build_interpolation_job_table(jobs)
    report = render_interpolation_markdown(tmp_path, "Demo")
    assert any(row["name"] == "SW kriging" for row in table)
    assert "Interpolation Engine Report" in report
    assert "SW kriging" in report


def test_unknown_method_rejected():
    try:
        run_interpolation([(0, 0, 1)], [GridNode(0, 0)], method="bad")
    except ValueError as exc:
        assert "не поддерживается" in str(exc)
    else:
        raise AssertionError("Unknown method must be rejected")
