from __future__ import annotations

import json

from projects import (
    build_project_file_index,
    build_project_file_index_table,
    load_project_file_index,
    save_project_file_index,
    save_project_las_file,
    save_project_csv_dataset,
    validate_project_file_index,
)

LAS_BYTES = b"~Version\nVERS. 2.0\n~Curve\nDEPT.M : Depth\nGR.API : Gamma\n~ASCII\n1000 45\n"
CSV_BYTES = b"Depth,C1\n1000,1.2\n"


def test_project_file_index_scans_project_files_with_checksums(tmp_path):
    save_project_las_file(
        LAS_BYTES,
        root=tmp_path,
        project_id="demo",
        file_name="Well A.las",
        well_name="Well A",
    )
    save_project_csv_dataset(
        CSV_BYTES,
        root=tmp_path,
        project_id="demo",
        file_name="gas.csv",
        name="Gas dataset",
        well_id="well-a",
    )

    entries = build_project_file_index(tmp_path, "demo")

    assert entries
    paths = {entry.relative_path for entry in entries}
    assert any(path.endswith("source.las") for path in paths)
    assert any(path.endswith("source.csv") for path in paths)
    assert all(len(entry.checksum_sha256) == 64 for entry in entries)
    assert {entry.kind for entry in entries} >= {"LAS", "CSV", "Metadata"}


def test_project_file_index_can_be_saved_and_loaded(tmp_path):
    save_project_csv_dataset(
        CSV_BYTES,
        root=tmp_path,
        project_id="demo",
        file_name="gas.csv",
        name="Gas dataset",
    )

    saved_entries = save_project_file_index(tmp_path, "demo")
    loaded_entries = load_project_file_index(tmp_path, "demo")

    assert len(saved_entries) == len(loaded_entries)
    assert (tmp_path / "demo" / "project_index.json").exists()
    payload = json.loads((tmp_path / "demo" / "project_index.json").read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert payload["project_id"] == "demo"
    assert payload["entries"]


def test_project_file_index_validation_flags_changed_and_missing_files(tmp_path):
    record = save_project_csv_dataset(
        CSV_BYTES,
        root=tmp_path,
        project_id="demo",
        file_name="gas.csv",
        name="Gas dataset",
    )
    save_project_file_index(tmp_path, "demo")

    source_path = tmp_path / "demo" / "datasets" / "csv" / record.id / "source.csv"
    source_path.write_bytes(b"Depth,C1\n1000,9.9\n")
    manifest_path = tmp_path / "demo" / "datasets" / "csv" / "csv_datasets.json"
    manifest_path.unlink()

    checked_entries = validate_project_file_index(tmp_path, "demo")

    statuses_by_path = {entry.relative_path: entry.status for entry in checked_entries}
    assert statuses_by_path[f"datasets/csv/{record.id}/source.csv"] == "changed"
    assert statuses_by_path["datasets/csv/csv_datasets.json"] == "missing"


def test_project_file_index_table_contains_compact_file_summary(tmp_path):
    save_project_csv_dataset(
        CSV_BYTES,
        root=tmp_path,
        project_id="demo",
        file_name="gas.csv",
        name="Gas dataset",
    )
    entries = save_project_file_index(tmp_path, "demo")

    table = build_project_file_index_table(entries)

    assert list(table.columns) == [
        "Тип",
        "Файл",
        "Путь",
        "Статус",
        "Скважина ID",
        "Dataset",
        "Размер, байт",
        "SHA-256",
        "Изменен",
        "Предупреждения",
    ]
    assert "source.csv" in set(table["Файл"])
    assert "CSV" in set(table["Тип"])

from projects import (
    annotate_project_file_index_duplicates,
    build_project_duplicate_files_table,
    detect_project_duplicate_files,
)


def test_project_file_index_detects_exact_checksum_duplicates(tmp_path):
    project_dir = tmp_path / "demo"
    (project_dir / "datasets" / "csv" / "a").mkdir(parents=True)
    (project_dir / "datasets" / "csv" / "b").mkdir(parents=True)
    duplicate_bytes = b"Depth,C1\n1000,1.2\n"
    (project_dir / "datasets" / "csv" / "a" / "source.csv").write_bytes(duplicate_bytes)
    (project_dir / "datasets" / "csv" / "b" / "source.csv").write_bytes(duplicate_bytes)

    entries = save_project_file_index(tmp_path, "demo")
    groups = detect_project_duplicate_files(entries)

    assert len(groups) == 1
    assert groups[0].reason == "checksum"
    assert groups[0].duplicate_count == 1
    assert {entry.relative_path for entry in groups[0].entries} == {
        "datasets/csv/a/source.csv",
        "datasets/csv/b/source.csv",
    }


def test_project_file_index_detects_name_size_duplicates_after_checksum_groups(tmp_path):
    project_dir = tmp_path / "demo"
    (project_dir / "exports" / "first").mkdir(parents=True)
    (project_dir / "exports" / "second").mkdir(parents=True)
    (project_dir / "exports" / "first" / "report.html").write_bytes(b"AAAA")
    (project_dir / "exports" / "second" / "report.html").write_bytes(b"BBBB")

    entries = save_project_file_index(tmp_path, "demo")
    groups = detect_project_duplicate_files(entries)

    assert len(groups) == 1
    assert groups[0].reason == "name_size"
    assert groups[0].match_key == "report.html::4"


def test_project_duplicate_files_table_contains_recommendations(tmp_path):
    project_dir = tmp_path / "demo"
    (project_dir / "datasets" / "csv" / "a").mkdir(parents=True)
    (project_dir / "datasets" / "csv" / "b").mkdir(parents=True)
    (project_dir / "datasets" / "csv" / "a" / "source.csv").write_bytes(CSV_BYTES)
    (project_dir / "datasets" / "csv" / "b" / "source.csv").write_bytes(CSV_BYTES)

    entries = save_project_file_index(tmp_path, "demo")
    groups = detect_project_duplicate_files(entries)
    table = build_project_duplicate_files_table(groups)

    assert list(table.columns) == [
        "Причина",
        "Совпадений",
        "Лишних файлов",
        "Ключ",
        "Файлы",
        "Типы",
        "Рекомендация",
    ]
    assert table.iloc[0]["Лишних файлов"] == 1
    assert "Оставьте один" in table.iloc[0]["Рекомендация"]


def test_project_file_index_annotation_marks_duplicate_entries(tmp_path):
    project_dir = tmp_path / "demo"
    (project_dir / "datasets" / "csv" / "a").mkdir(parents=True)
    (project_dir / "datasets" / "csv" / "b").mkdir(parents=True)
    (project_dir / "datasets" / "csv" / "a" / "source.csv").write_bytes(CSV_BYTES)
    (project_dir / "datasets" / "csv" / "b" / "source.csv").write_bytes(CSV_BYTES)

    entries = save_project_file_index(tmp_path, "demo")
    annotated = annotate_project_file_index_duplicates(entries)

    duplicate_entries = [entry for entry in annotated if entry.name == "source.csv"]
    assert {entry.status for entry in duplicate_entries} == {"warning"}
    assert all("Возможный дубликат" in "; ".join(entry.warnings) for entry in duplicate_entries)

from projects import (
    build_project_file_version_history_table,
    build_project_file_versions_table,
    load_project_file_versions,
    update_project_file_versions,
)


def test_project_file_versions_create_initial_versions_from_saved_index(tmp_path):
    save_project_csv_dataset(
        CSV_BYTES,
        root=tmp_path,
        project_id="demo",
        file_name="gas.csv",
        name="Gas dataset",
    )
    save_project_file_index(tmp_path, "demo")

    assets = update_project_file_versions(tmp_path, "demo", author="Rinat")
    loaded_assets = load_project_file_versions(tmp_path, "demo")

    assert assets
    assert len(assets) == len(loaded_assets)
    source_assets = [asset for asset in assets if asset.relative_path.endswith("source.csv")]
    assert source_assets
    assert source_assets[0].version_count == 1
    assert source_assets[0].active_version is not None
    assert source_assets[0].active_version.version_number == 1
    assert source_assets[0].active_version.author == "Rinat"
    assert source_assets[0].active_version.change_summary == "Initial version"
    payload = json.loads((tmp_path / "demo" / "project_file_versions.json").read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert payload["project_id"] == "demo"


def test_project_file_versions_append_new_version_when_checksum_changes(tmp_path):
    record = save_project_csv_dataset(
        CSV_BYTES,
        root=tmp_path,
        project_id="demo",
        file_name="gas.csv",
        name="Gas dataset",
    )
    save_project_file_index(tmp_path, "demo")
    update_project_file_versions(tmp_path, "demo")

    source_path = tmp_path / "demo" / "datasets" / "csv" / record.id / "source.csv"
    source_path.write_bytes(b"Depth,C1\n1000,2.4\n")
    save_project_file_index(tmp_path, "demo")
    assets = update_project_file_versions(tmp_path, "demo", author="engineer")

    source_asset = next(asset for asset in assets if asset.relative_path.endswith("source.csv"))
    assert source_asset.version_count == 2
    assert [version.status for version in source_asset.versions] == ["archived", "active"]
    assert source_asset.active_version.version_number == 2
    assert source_asset.active_version.change_summary == "File content changed"
    assert source_asset.active_version.author == "engineer"


def test_project_file_versions_do_not_duplicate_unchanged_checksums(tmp_path):
    save_project_csv_dataset(
        CSV_BYTES,
        root=tmp_path,
        project_id="demo",
        file_name="gas.csv",
        name="Gas dataset",
    )
    save_project_file_index(tmp_path, "demo")

    first_assets = update_project_file_versions(tmp_path, "demo")
    second_assets = update_project_file_versions(tmp_path, "demo")

    first_counts = {asset.relative_path: asset.version_count for asset in first_assets}
    second_counts = {asset.relative_path: asset.version_count for asset in second_assets}
    assert second_counts == first_counts


def test_project_file_versions_tables_contain_active_and_history_summary(tmp_path):
    record = save_project_csv_dataset(
        CSV_BYTES,
        root=tmp_path,
        project_id="demo",
        file_name="gas.csv",
        name="Gas dataset",
    )
    save_project_file_index(tmp_path, "demo")
    update_project_file_versions(tmp_path, "demo")
    (tmp_path / "demo" / "datasets" / "csv" / record.id / "source.csv").write_bytes(b"Depth,C1\n1000,3.6\n")
    save_project_file_index(tmp_path, "demo")
    assets = update_project_file_versions(tmp_path, "demo")

    table = build_project_file_versions_table(assets)
    assert list(table.columns) == [
        "Тип",
        "Файл",
        "Путь",
        "Активная версия",
        "Всего версий",
        "SHA-256",
        "Размер, байт",
        "Автор",
        "Создана версия",
        "Изменение",
    ]
    source_asset = next(asset for asset in assets if asset.relative_path.endswith("source.csv"))
    history = build_project_file_version_history_table(source_asset)
    assert list(history["Версия"]) == [2, 1]
    assert "активная" in set(history["Статус"])
