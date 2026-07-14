from __future__ import annotations

"""Streamlit panel for manual interpretation interval management.

The panel is intentionally thin: persistence, validation, overlap checks and
Undo/Redo remain in the project-layer services.  Only JSON-compatible values
are stored in Streamlit session state.
"""

from pathlib import Path
from typing import Any, MutableMapping

from projects.interpretation_interval_exports import (
    export_interpretation_intervals_csv,
    export_interpretation_intervals_json,
    export_interpretation_intervals_xlsx,
)
from projects.interpretation_interval_imports import (
    apply_interpretation_interval_import,
    parse_interpretation_interval_import,
)
from projects.interpretation_interval_manager import (
    InterpretationIntervalManager,
    InterpretationIntervalOverlapError,
)
from projects.interpretation_interval_properties import InterpretationIntervalPropertiesService
from projects.interpretation_interval_types import InterpretationIntervalTypeRepository
from projects.repository import DEFAULT_PROJECTS_ROOT


DEFAULT_MANUAL_WELL_ID = "active-well"


def resolve_interpretation_well_id(state: MutableMapping[str, Any]) -> str:
    """Resolve a stable storage scope for the active interpretation workspace."""

    direct = str(state.get("active_well_id", "") or "").strip()
    if direct:
        return direct
    contract = state.get("workbench_active_calculation", {})
    if isinstance(contract, dict):
        contract_well_id = str(contract.get("well_id", "") or "").strip()
        if contract_well_id:
            return contract_well_id
    return DEFAULT_MANUAL_WELL_ID


def render_interpretation_interval_panel(
    st: Any,
    *,
    state: MutableMapping[str, Any],
    project_id: str,
    root: Path | str = DEFAULT_PROJECTS_ROOT,
) -> None:
    """Render CRUD and property editing for manually managed intervals."""

    well_id = resolve_interpretation_well_id(state)
    manager = InterpretationIntervalManager(
        state,
        root=root,
        project_id=project_id,
        well_id=well_id,
    )
    properties_service = InterpretationIntervalPropertiesService(manager)
    type_repository = InterpretationIntervalTypeRepository(root=root, project_id=project_id)
    interval_types = type_repository.list()
    intervals = manager.list_intervals()

    with st.expander("Ручные интервалы интерпретации", expanded=False):
        st.caption(f"Область хранения: проект `{project_id}` · скважина `{well_id}`")

        action_left, action_mid, action_right = st.columns((1, 1, 3))
        if action_left.button(
            "↶ Отменить",
            key=f"manual_interval_undo_{project_id}_{well_id}",
            disabled=not manager.can_undo,
            width="stretch",
        ):
            manager.undo()
            st.rerun()
        if action_mid.button(
            "↷ Повторить",
            key=f"manual_interval_redo_{project_id}_{well_id}",
            disabled=not manager.can_redo,
            width="stretch",
        ):
            manager.redo()
            st.rerun()
        action_right.caption(f"Интервалов: {len(intervals)}")

        with st.expander("Справочник типов интервалов", expanded=False):
            st.caption("Типы хранятся на уровне проекта и доступны всем его скважинам.")
            if interval_types:
                st.dataframe(
                    [
                        {
                            "ID": item.id,
                            "Название": item.name,
                            "Цвет": item.color,
                            "Описание": item.description,
                        }
                        for item in interval_types
                    ],
                    width="stretch",
                    hide_index=True,
                )
            with st.form(f"manual_interval_type_upsert_{project_id}", clear_on_submit=True):
                type_id_input = st.text_input("ID типа", placeholder="например: tight_gas")
                type_name_input = st.text_input("Название типа")
                type_color_input = st.color_picker("Цвет типа", value="#4C78A8")
                type_description_input = st.text_area("Описание типа")
                type_save_clicked = st.form_submit_button("Добавить или обновить тип", width="stretch")
            if type_save_clicked:
                try:
                    type_repository.upsert(
                        type_id=type_id_input,
                        name=type_name_input,
                        color=type_color_input,
                        description=type_description_input,
                    )
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.success("Тип интервала сохранён.")
                    st.rerun()
            if interval_types:
                type_delete_id = st.selectbox(
                    "Тип для удаления",
                    options=[item.id for item in interval_types],
                    format_func=lambda value: next(
                        (f"{item.name} ({item.id})" for item in interval_types if item.id == value),
                        value,
                    ),
                    key=f"manual_interval_type_delete_select_{project_id}",
                )
                type_usage = type_repository.usage(type_delete_id)
                if type_usage.in_use:
                    st.warning(
                        f"Тип используется: {type_usage.interval_count} интервалов · "
                        f"{type_usage.well_count} скважин · "
                        f"{type_usage.interpretation_count} интерпретаций."
                    )
                    replacement_ids = [item.id for item in interval_types if item.id != type_delete_id]
                    if replacement_ids:
                        replacement_type_id = st.selectbox(
                            "Переназначить интервалы на тип",
                            options=replacement_ids,
                            format_func=lambda value: next(
                                (f"{item.name} ({item.id})" for item in interval_types if item.id == value),
                                value,
                            ),
                            key=f"manual_interval_type_reassign_target_{project_id}",
                        )
                        apply_replacement_color = st.checkbox(
                            "Применить цвет целевого типа",
                            value=True,
                            key=f"manual_interval_type_reassign_color_{project_id}",
                        )
                        try:
                            reassignment_preview = type_repository.preview_reassignment(
                                type_delete_id,
                                replacement_type_id,
                                apply_target_color=apply_replacement_color,
                            )
                        except (KeyError, ValueError) as exc:
                            st.error(str(exc))
                            reassignment_preview = None
                        if reassignment_preview is not None:
                            st.caption(
                                f"Будет изменено: {reassignment_preview.interval_count} интервалов · "
                                f"{reassignment_preview.well_count} скважин · "
                                f"{reassignment_preview.interpretation_count} интерпретаций."
                            )
                            with st.expander("Предварительный просмотр переназначения", expanded=False):
                                st.dataframe(
                                    [
                                        {
                                            "Скважина": item.well_id,
                                            "Интерпретация": item.interpretation_id,
                                            "Интервал": item.label,
                                            "Верх": item.top,
                                            "Низ": item.base,
                                            "Мощность": item.thickness,
                                            "Текущий цвет": item.color,
                                        }
                                        for item in reassignment_preview.items
                                    ],
                                    width="stretch",
                                    hide_index=True,
                                )
                        reassignment_confirmed = st.checkbox(
                            "Подтверждаю переназначение и удаление исходного типа",
                            value=False,
                            key=f"manual_interval_type_reassign_confirm_{project_id}_{type_delete_id}_{replacement_type_id}",
                        )
                        if st.button(
                            "Переназначить интервалы и удалить тип",
                            key=f"manual_interval_type_reassign_delete_{project_id}",
                            disabled=not reassignment_confirmed or reassignment_preview is None,
                            width="stretch",
                        ):
                            try:
                                reassigned = type_repository.reassign_and_delete(
                                    type_delete_id,
                                    replacement_type_id,
                                    apply_target_color=apply_replacement_color,
                                    expected_confirmation_token=reassignment_preview.confirmation_token,
                                )
                            except (KeyError, ValueError) as exc:
                                st.error(str(exc))
                            else:
                                st.success(
                                    f"Переназначено интервалов: {reassigned.interval_count}. "
                                    "Исходный тип удалён."
                                )
                                st.rerun()
                if st.button(
                    "Удалить тип из справочника",
                    key=f"manual_interval_type_delete_{project_id}",
                    disabled=type_usage.in_use,
                    width="stretch",
                ):
                    try:
                        deleted = type_repository.delete(type_delete_id)
                    except ValueError as exc:
                        st.error(str(exc))
                    else:
                        if deleted:
                            st.success("Неиспользуемый тип удалён из справочника.")
                            st.rerun()
            with st.expander("Журнал пакетных операций", expanded=False):
                type_operations = type_repository.list_operations(limit=25)
                if not type_operations:
                    st.caption("Пакетные операции с типами ещё не выполнялись.")
                else:
                    st.dataframe(
                        [
                            {
                                "Дата": item.created_at,
                                "Операция": "Переназначение и удаление",
                                "Исходный тип": item.source_type_id,
                                "Целевой тип": item.target_type_id,
                                "Интервалы": item.interval_count,
                                "Скважины": item.well_count,
                                "Интерпретации": item.interpretation_count,
                                "Цвет изменён": "Да" if item.target_color_applied else "Нет",
                            }
                            for item in type_operations
                        ],
                        width="stretch",
                        hide_index=True,
                    )

            if st.button(
                "Восстановить типы по умолчанию",
                key=f"manual_interval_type_reset_{project_id}",
                width="stretch",
            ):
                type_repository.reset_defaults()
                st.success("Справочник типов восстановлен.")
                st.rerun()

        if intervals:
            export_json = export_interpretation_intervals_json(
                intervals,
                project_id=project_id,
                well_id=well_id,
                interpretation_id=manager.interpretation_id,
            )
            export_csv = export_interpretation_intervals_csv(intervals)
            export_xlsx = export_interpretation_intervals_xlsx(
                intervals,
                project_id=project_id,
                well_id=well_id,
                interpretation_id=manager.interpretation_id,
            )
            export_left, export_mid, export_right = st.columns(3)
            export_left.download_button(
                "JSON",
                data=export_json,
                file_name=f"interpretation_intervals_{project_id}_{well_id}.json",
                mime="application/json",
                key=f"manual_interval_export_json_{project_id}_{well_id}",
                width="stretch",
            )
            export_mid.download_button(
                "CSV",
                data=export_csv,
                file_name=f"interpretation_intervals_{project_id}_{well_id}.csv",
                mime="text/csv",
                key=f"manual_interval_export_csv_{project_id}_{well_id}",
                width="stretch",
            )
            export_right.download_button(
                "Excel",
                data=export_xlsx,
                file_name=f"interpretation_intervals_{project_id}_{well_id}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"manual_interval_export_xlsx_{project_id}_{well_id}",
                width="stretch",
            )

        st.markdown("**Импорт интервалов**")
        import_file = st.file_uploader(
            "JSON, CSV или Excel",
            type=["json", "csv", "xlsx"],
            key=f"manual_interval_import_file_{project_id}_{well_id}",
        )
        import_mode = st.selectbox(
            "Режим импорта",
            options=("upsert", "append", "replace"),
            format_func=lambda value: {
                "upsert": "Добавить и обновить по UUID",
                "append": "Только добавить новые",
                "replace": "Полностью заменить текущие",
            }[value],
            key=f"manual_interval_import_mode_{project_id}_{well_id}",
        )
        if st.button(
            "Импортировать интервалы",
            key=f"manual_interval_import_apply_{project_id}_{well_id}",
            disabled=import_file is None,
            width="stretch",
        ):
            try:
                payload = parse_interpretation_interval_import(
                    import_file.getvalue(),
                    import_file.name,
                )
                result = apply_interpretation_interval_import(
                    manager,
                    payload,
                    mode=import_mode,
                )
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.success(
                    f"Импортировано: {result.imported_count}; "
                    f"добавлено: {result.created_count}; "
                    f"обновлено: {result.updated_count}."
                )
                st.rerun()

        with st.form(f"manual_interval_create_{project_id}_{well_id}", clear_on_submit=True):
            st.markdown("**Новый интервал**")
            create_top_col, create_base_col = st.columns(2)
            top = create_top_col.number_input("Верх, м", step=0.1, format="%.3f")
            base = create_base_col.number_input("Низ, м", step=0.1, format="%.3f")
            label = st.text_input("Подпись", value="Интервал")
            type_col, color_col = st.columns(2)
            type_ids = [item.id for item in interval_types] or ["undefined"]
            interval_type = type_col.selectbox(
                "Тип",
                options=type_ids,
                format_func=lambda value: next(
                    (f"{item.name} ({item.id})" for item in interval_types if item.id == value),
                    value,
                ),
            )
            default_type_color = next(
                (item.color for item in interval_types if item.id == interval_type),
                "#4C78A8",
            )
            color = color_col.color_picker("Цвет", value=default_type_color)
            comment = st.text_area("Комментарий")
            reject_overlaps = st.checkbox("Запрещать пересечения", value=False)
            create_clicked = st.form_submit_button("Добавить интервал", width="stretch")

        if create_clicked:
            try:
                manager.create(
                    label=label,
                    top=top,
                    base=base,
                    interval_type=interval_type,
                    color=color,
                    comment=comment,
                    source="manual-ui",
                    reject_overlaps=reject_overlaps,
                )
            except (ValueError, InterpretationIntervalOverlapError) as exc:
                st.error(str(exc))
            else:
                st.success("Интервал добавлен.")
                st.rerun()

        if not intervals:
            st.info("Ручные интервалы ещё не созданы.")
            return

        option_ids = [item.id for item in intervals]
        option_labels = {
            item.id: f"{item.label} · {item.top:g}–{item.base:g} м · {item.interval_type}"
            for item in intervals
        }
        selected_id = st.selectbox(
            "Выбранный интервал",
            options=option_ids,
            format_func=lambda value: option_labels.get(value, value),
            key=f"manual_interval_selected_{project_id}_{well_id}",
        )
        selected = properties_service.get(selected_id)

        with st.form(f"manual_interval_properties_{project_id}_{well_id}_{selected_id}"):
            st.markdown("**Свойства интервала**")
            label_value = st.text_input("Подпись интервала", value=selected.label)
            bounds_left, bounds_right = st.columns(2)
            top_value = bounds_left.number_input(
                "Верх интервала, м", value=float(selected.top), step=0.1, format="%.3f"
            )
            base_value = bounds_right.number_input(
                "Низ интервала, м", value=float(selected.base), step=0.1, format="%.3f"
            )
            metrics_left, metrics_right = st.columns(2)
            metrics_left.metric("Мощность, м", f"{selected.thickness:g}")
            metrics_right.metric("Средняя глубина, м", f"{selected.middle_depth:g}")
            edit_type_ids = [item.id for item in interval_types]
            if selected.interval_type not in edit_type_ids:
                edit_type_ids.append(selected.interval_type)
            type_value = st.selectbox(
                "Тип интервала",
                options=edit_type_ids,
                index=edit_type_ids.index(selected.interval_type),
                format_func=lambda value: next(
                    (f"{item.name} ({item.id})" for item in interval_types if item.id == value),
                    f"{value} (вне справочника)",
                ),
            )
            color_value = st.color_picker("Цвет интервала", value=selected.color)
            comment_value = st.text_area("Комментарий интервала", value=selected.comment)
            reject_update_overlaps = st.checkbox(
                "Запрещать пересечения при сохранении",
                value=False,
                key=f"manual_interval_reject_overlap_{selected_id}",
            )
            save_col, delete_col = st.columns(2)
            save_clicked = save_col.form_submit_button("Сохранить", width="stretch")
            delete_clicked = delete_col.form_submit_button("Удалить", width="stretch")

        if save_clicked:
            try:
                properties_service.apply(
                    selected_id,
                    {
                        "label": label_value,
                        "top": top_value,
                        "base": base_value,
                        "interval_type": type_value,
                        "color": color_value,
                        "comment": comment_value,
                    },
                    reject_overlaps=reject_update_overlaps,
                )
            except (ValueError, InterpretationIntervalOverlapError) as exc:
                st.error(str(exc))
            else:
                st.success("Свойства интервала сохранены.")
                st.rerun()

        if delete_clicked:
            manager.delete(selected_id)
            state.pop(f"manual_interval_selected_{project_id}_{well_id}", None)
            st.success("Интервал удалён.")
            st.rerun()
