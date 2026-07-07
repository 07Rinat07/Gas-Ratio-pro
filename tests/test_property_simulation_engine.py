from pathlib import Path

from projects.interpolation_engine import build_regular_grid
from projects.property_simulation_engine import (
    SimulationJobSpec,
    build_property_simulation_manifest,
    build_simulated_cells_table,
    build_simulation_job_table,
    list_simulation_jobs,
    render_property_simulation_markdown,
    run_property_simulation,
    save_simulation_job,
    seed_property_simulation_engine,
    sequential_gaussian_simulation_foundation,
    sequential_indicator_simulation_foundation,
    summarize_simulation_result,
)


def _numeric_samples():
    return [
        {"x": 0, "y": 0, "value": 0.12},
        {"x": 10, "y": 0, "value": 0.18},
        {"x": 0, "y": 10, "value": 0.22},
        {"x": 10, "y": 10, "value": 0.28},
    ]


def _facies_samples():
    return [
        {"x": 0, "y": 0, "value": "Sand"},
        {"x": 10, "y": 0, "value": "Sand"},
        {"x": 0, "y": 10, "value": "Shale"},
        {"x": 10, "y": 10, "value": "Shale"},
    ]


def test_sequential_gaussian_simulation_is_reproducible():
    grid = build_regular_grid(x_min=0, x_max=10, y_min=0, y_max=10, nx=3, ny=3)
    first = sequential_gaussian_simulation_foundation(_numeric_samples(), grid, realization_count=2, seed=123, min_value=0, max_value=0.5)
    second = sequential_gaussian_simulation_foundation(_numeric_samples(), grid, realization_count=2, seed=123, min_value=0, max_value=0.5)
    assert [cell.value for cell in first] == [cell.value for cell in second]
    assert len(first) == 18
    assert {cell.realization for cell in first} == {1, 2}
    assert all(0 <= cell.value <= 0.5 for cell in first if isinstance(cell.value, float))


def test_sequential_indicator_simulation_returns_categories():
    grid = build_regular_grid(x_min=0, x_max=10, y_min=0, y_max=10, nx=2, ny=2)
    cells = sequential_indicator_simulation_foundation(_facies_samples(), grid, categories=["Sand", "Shale"], realization_count=2, seed=10)
    assert len(cells) == 8
    assert {cell.value for cell in cells} <= {"Sand", "Shale"}
    assert all(cell.method == "sequential_indicator_foundation" for cell in cells)


def test_run_property_simulation_dispatches_methods():
    grid = build_regular_grid(x_min=0, x_max=5, y_min=0, y_max=5, nx=2, ny=2)
    gaussian = run_property_simulation(_numeric_samples(), grid, method="sequential_gaussian_foundation", parameters={"seed": 5})
    indicator = run_property_simulation(_facies_samples(), grid, method="sequential_indicator_foundation", parameters={"categories": ["Sand", "Shale"], "seed": 5})
    assert len(gaussian) == 4
    assert len(indicator) == 4


def test_simulation_result_summary_and_table():
    grid = build_regular_grid(x_min=0, x_max=10, y_min=0, y_max=10, nx=2, ny=2)
    cells = sequential_gaussian_simulation_foundation(_numeric_samples(), grid, seed=1)
    summary = summarize_simulation_result(cells)
    table = build_simulated_cells_table(cells)
    assert summary["cell_count"] == 4
    assert summary["numeric_count"] == 4
    assert summary["mean"] is not None
    assert table[0]["method"] == "sequential_gaussian_foundation"


def test_save_list_seed_manifest_and_markdown(tmp_path: Path):
    root = tmp_path / "projects"
    project_id = "sim-demo"
    saved = save_simulation_job(
        root,
        project_id,
        SimulationJobSpec(name="POR simulation", property_name="POR", method="sequential_gaussian_foundation", realization_count=3, seed=11),
    )
    assert saved["name"] == "POR simulation"
    jobs = list_simulation_jobs(root, project_id)
    assert len(jobs) == 1
    assert build_simulation_job_table(jobs)[0]["realizations"] == 3
    manifest = build_property_simulation_manifest(root, project_id)
    assert manifest.job_count == 1
    assert manifest.realization_count == 3
    markdown = render_property_simulation_markdown(root, project_id)
    assert "Property Simulation Engine Report" in markdown
    assert "POR simulation" in markdown
    seed_property_simulation_engine(root, project_id, overwrite=True, author="Rinat")
    assert len(list_simulation_jobs(root, project_id)) == 2


def test_invalid_method_raises():
    grid = build_regular_grid(x_min=0, x_max=1, y_min=0, y_max=1, nx=1, ny=1)
    try:
        run_property_simulation(_numeric_samples(), grid, method="bad")
    except ValueError as exc:
        assert "не поддерживается" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
