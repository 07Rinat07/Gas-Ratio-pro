from reports.export_progress import (
    EXPORT_PROGRESS_STAGES,
    export_progress_stage,
    format_export_progress_message,
    staged_progress_reporter,
)


def test_four_stage_contract_is_complete_and_contiguous() -> None:
    assert tuple(stage.prefix for stage in EXPORT_PROGRESS_STAGES) == (
        "Шаг 1 из 4 — Проверка параметров",
        "Шаг 2 из 4 — Подготовка данных",
        "Шаг 3 из 4 — Формирование документа",
        "Шаг 4 из 4 — Финализация файла",
    )
    assert EXPORT_PROGRESS_STAGES[0].minimum == 0
    assert EXPORT_PROGRESS_STAGES[-1].maximum == 100
    for current, following in zip(EXPORT_PROGRESS_STAGES, EXPORT_PROGRESS_STAGES[1:]):
        assert current.maximum + 1 == following.minimum


def test_progress_values_are_clamped_and_mapped_to_stages() -> None:
    assert export_progress_stage(-10).number == 1
    assert export_progress_stage(9).number == 1
    assert export_progress_stage(10).number == 2
    assert export_progress_stage(39).number == 2
    assert export_progress_stage(40).number == 3
    assert export_progress_stage(89).number == 3
    assert export_progress_stage(90).number == 4
    assert export_progress_stage(120).number == 4


def test_message_preserves_renderer_detail() -> None:
    assert format_export_progress_message(45, "Построение страниц") == (
        "Шаг 3 из 4 — Формирование документа: Построение страниц"
    )


def test_reporter_decorator_forwards_normalized_progress_and_stage() -> None:
    events: list[tuple[int, str]] = []
    reporter = staged_progress_reporter(lambda progress, message: events.append((progress, message)))

    reporter(105, "Готово")

    assert events == [(100, "Шаг 4 из 4 — Финализация файла: Готово")]
