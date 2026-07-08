from ui.manager_framework import build_manager_toolbar, build_records_table


def test_build_manager_toolbar_contains_standard_dataset_actions() -> None:
    toolbar = build_manager_toolbar("dataset-mud-log", "Dataset Manager · Mud Log")

    assert toolbar.has_action("delete_selected")
    assert toolbar.has_action("clear_section")
    assert toolbar.has_action("clear_all")
    assert toolbar.has_action("export")


def test_build_records_table_orders_columns() -> None:
    table = build_records_table(
        "dataset",
        [{"id": "one", "name": "Dataset 1", "rows": 10}],
        [("name", "Dataset"), ("rows", "Строк")],
    )

    assert table.row_ids() == ("one",)
    assert list(table.to_dataframe().columns) == ["Dataset", "Строк"]
