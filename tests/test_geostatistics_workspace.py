from pathlib import Path

import pytest

from projects.geostatistics_workspace import (
    SearchEllipsoidSpec,
    VariogramModelSpec,
    build_experimental_variogram_table,
    build_geostatistics_manifest,
    build_search_ellipsoid_table,
    build_variogram_model_table,
    calculate_experimental_variogram,
    evaluate_variogram_model,
    fit_variogram_model,
    list_geostatistics_jobs,
    list_search_ellipsoids,
    list_variogram_models,
    render_geostatistics_markdown,
    save_geostatistics_job,
    save_search_ellipsoid,
    save_variogram_model,
    seed_geostatistics_workspace,
)


def demo_samples():
    return [
        {"x": 0, "y": 0, "value": 0.10},
        {"x": 100, "y": 0, "value": 0.15},
        {"x": 200, "y": 0, "value": 0.22},
        {"x": 300, "y": 0, "value": 0.30},
    ]


def test_experimental_variogram_builds_lag_bins():
    bins = calculate_experimental_variogram(demo_samples(), lag_size=100, max_lag=300)
    assert bins
    assert bins[0].pair_count >= 1
    assert bins[0].gamma >= 0
    assert build_experimental_variogram_table(bins)[0]["lag_index"] == 1


def test_variogram_models_are_monotonic_for_common_models():
    model = VariogramModelSpec(name="POR", model_type="spherical", nugget=0.01, sill=0.09, range_major=300)
    assert evaluate_variogram_model(0, model) <= evaluate_variogram_model(100, model)
    assert evaluate_variogram_model(1000, model) == pytest.approx(0.09)
    exp_model = VariogramModelSpec(name="PERM", model_type="exponential", nugget=0, sill=1, range_major=100)
    assert 0 < evaluate_variogram_model(100, exp_model) < 1


def test_fit_variogram_model_returns_valid_spec():
    bins = calculate_experimental_variogram(demo_samples(), lag_size=100, max_lag=300)
    fitted = fit_variogram_model(bins, name="Fitted POR", model_type="gaussian", property_name="POR")
    assert fitted.name == "Fitted POR"
    assert fitted.model_type == "gaussian"
    assert fitted.range_major > 0
    assert fitted.fit_score is not None


def test_save_and_list_models_ellipsoids_jobs(tmp_path: Path):
    model = save_variogram_model(tmp_path, "demo", {"name": "POR model", "model_type": "spherical", "sill": 1, "range_major": 500})
    ellipsoid = save_search_ellipsoid(tmp_path, "demo", SearchEllipsoidSpec(name="Default", radius_major=1000, radius_minor=500, radius_vertical=25))
    job = save_geostatistics_job(tmp_path, "demo", {"name": "POR job", "property_name": "POR", "model_name": model.name, "search_ellipsoid": ellipsoid.name})
    assert list_variogram_models(tmp_path, "demo")[0].name == "POR model"
    assert list_search_ellipsoids(tmp_path, "demo")[0].name == "Default"
    assert list_geostatistics_jobs(tmp_path, "demo")[0].name == "POR job"
    assert job.created_at


def test_duplicate_policy(tmp_path: Path):
    save_variogram_model(tmp_path, "demo", {"name": "POR model", "sill": 1, "range_major": 500})
    with pytest.raises(ValueError):
        save_variogram_model(tmp_path, "demo", {"name": "POR model", "sill": 1, "range_major": 500}, replace=False)


def test_seed_manifest_tables_and_markdown(tmp_path: Path):
    seed_geostatistics_workspace(tmp_path, "demo", author="Rinat", overwrite=True)
    manifest = build_geostatistics_manifest(tmp_path, "demo")
    assert manifest.model_count >= 2
    assert manifest.ellipsoid_count >= 1
    assert manifest.warnings == ()
    assert build_variogram_model_table(list_variogram_models(tmp_path, "demo"))[0]["name"]
    assert build_search_ellipsoid_table(list_search_ellipsoids(tmp_path, "demo"))[0]["name"]
    report = render_geostatistics_markdown(tmp_path, "demo")
    assert "Geostatistics Workspace Report" in report
    assert "Variogram Models" in report


def test_invalid_model_type_rejected():
    with pytest.raises(ValueError):
        evaluate_variogram_model(10, {"name": "Bad", "model_type": "bad", "sill": 1, "range_major": 10})


def test_search_ellipsoid_neighbor_validation(tmp_path: Path):
    with pytest.raises(ValueError):
        save_search_ellipsoid(tmp_path, "demo", {"name": "bad", "radius_major": 1, "radius_minor": 1, "radius_vertical": 1, "min_neighbors": 5, "max_neighbors": 1})
