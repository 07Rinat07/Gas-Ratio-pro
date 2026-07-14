from __future__ import annotations

"""Streamlit panel for manual interpretation interval management.

The panel is intentionally thin: persistence, validation, overlap checks and
Undo/Redo remain in the project-layer services.  Only JSON-compatible values
are stored in Streamlit session state.
"""

from pathlib import Path
from typing import Any, MutableMapping

from projects.interpretation_catalog import InterpretationCatalogRepository
from projects.interpretation_interval_analysis import (
    InterpretationIntervalFilter,
    filter_interpretation_intervals,
    summarize_interpretation_intervals,
)
from projects.interpretation_interval_batch import InterpretationIntervalBatchService
from projects.interpretation_interval_exports import (
    export_interpretation_intervals_csv,
    export_interpretation_intervals_json,
    export_interpretation_intervals_xlsx,
)
from projects.interpretation_interval_imports import (
    apply_interpretation_interval_import,
    parse_interpretation_interval_import,
)
from projects.interpretation_interval_filter_presets import (
    InterpretationIntervalFilterPresetRepository,
    export_filter_presets_json,
    import_filter_presets_json,
)
from projects.interpretation_interval_comparison import (
    InterpretationIntervalTransferService,
    compare_interpretation_intervals,
)
from projects.interpretation_interval_manager import (
    InterpretationIntervalManager,
    InterpretationIntervalOverlapError,
)
from projects.interpretation_interval_merge import InterpretationIntervalMergeService
from projects.interpretation_interval_properties import InterpretationIntervalPropertiesService
from projects.interpretation_revisions import InterpretationRevisionRepository
from projects.interpretation_publication import InterpretationPublicationService
from projects.interpretation_publication_exports import (
    export_publication_audit_csv,
    export_publication_audit_json,
    export_publication_audit_xlsx,
)
from projects.interpretation_access import InterpretationActor, ROLE_LABELS_RU, ROLES
from projects.interpretation_interval_type_operation_exports import (
    export_type_operations_csv,
    export_type_operations_json,
    export_type_operations_xlsx,
)
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
    catalog_repository = InterpretationCatalogRepository(
        root=root,
        project_id=project_id,
        well_id=well_id,
    )
    catalog_items = catalog_repository.list()
    interpretation_ids = [item.id for item in catalog_items]
    selector_key = f"manual_interval_interpretation_selector_{project_id}_{well_id}"
    if str(state.get(selector_key, "")) not in interpretation_ids:
        state[selector_key] = interpretation_ids[0]
    selected_interpretation_id = st.selectbox(
        "Активная интерпретация",
        options=interpretation_ids,
        format_func=lambda value: next(
            (f"{item.name} ({item.id})" for item in catalog_items if item.id == value),
            value,
        ),
        key=selector_key,
    )
    manager = InterpretationIntervalManager(
        state,
        root=root,
        project_id=project_id,
        well_id=well_id,
        interpretation_id=selected_interpretation_id,
    )
    properties_service = InterpretationIntervalPropertiesService(manager)
    type_repository = InterpretationIntervalTypeRepository(root=root, project_id=project_id)
    interval_types = type_repository.list()
    preset_repository = InterpretationIntervalFilterPresetRepository(
        root=root,
        project_id=project_id,
        well_id=well_id,
        interpretation_id=manager.interpretation_id,
    )
    filter_presets = preset_repository.list()
    intervals = manager.list_intervals()
    filtered_intervals = intervals

    with st.expander("Ручные интервалы интерпретации", expanded=False):
        active_catalog_item = catalog_repository.get(manager.interpretation_id)
        st.caption(
            f"Область хранения: проект `{project_id}` · скважина `{well_id}` · "
            f"интерпретация `{manager.interpretation_id}`"
        )
        if active_catalog_item.description:
            st.caption(active_catalog_item.description)

        with st.expander("Управление интерпретациями", expanded=False):
            st.dataframe(
                [
                    {
                        "ID": item.id,
                        "Название": item.name,
                        "Описание": item.description,
                        "Создана": item.created_at,
                        "Обновлена": item.updated_at,
                        "Источник копии": item.duplicated_from,
                    }
                    for item in catalog_items
                ],
                width="stretch",
                hide_index=True,
            )

            with st.form(f"interpretation_create_{project_id}_{well_id}", clear_on_submit=True):
                create_name = st.text_input("Название новой интерпретации")
                create_description = st.text_area("Описание новой интерпретации")
                create_submitted = st.form_submit_button("Создать интерпретацию", width="stretch")
            if create_submitted:
                try:
                    created_interpretation = catalog_repository.create(
                        name=create_name,
                        description=create_description,
                    )
                except (KeyError, ValueError, PermissionError, OSError) as exc:
                    st.error(str(exc))
                else:
                    state[selector_key] = created_interpretation.id
                    st.success("Интерпретация создана.")
                    st.rerun()

            with st.form(f"interpretation_update_{project_id}_{well_id}_{manager.interpretation_id}"):
                update_name = st.text_input(
                    "Название активной интерпретации",
                    value=active_catalog_item.name,
                )
                update_description = st.text_area(
                    "Описание активной интерпретации",
                    value=active_catalog_item.description,
                )
                update_submitted = st.form_submit_button("Сохранить метаданные", width="stretch")
            if update_submitted:
                try:
                    catalog_repository.update(
                        manager.interpretation_id,
                        name=update_name,
                        description=update_description,
                    )
                except (KeyError, ValueError, OSError) as exc:
                    st.error(str(exc))
                else:
                    st.success("Метаданные интерпретации обновлены.")
                    st.rerun()

            with st.form(f"interpretation_duplicate_{project_id}_{well_id}_{manager.interpretation_id}", clear_on_submit=True):
                duplicate_name = st.text_input(
                    "Название копии",
                    value=f"{active_catalog_item.name} — копия",
                )
                duplicate_description = st.text_area(
                    "Описание копии",
                    value=active_catalog_item.description,
                )
                duplicate_submitted = st.form_submit_button("Дублировать интерпретацию", width="stretch")
            if duplicate_submitted:
                try:
                    duplicated_interpretation = catalog_repository.duplicate(
                        manager.interpretation_id,
                        name=duplicate_name,
                        description=duplicate_description,
                    )
                except (KeyError, ValueError, OSError) as exc:
                    st.error(str(exc))
                else:
                    state[selector_key] = duplicated_interpretation.id
                    st.success("Интерпретация продублирована вместе с её настройками и интервалами.")
                    st.rerun()

            delete_confirmed = st.checkbox(
                "Подтверждаю удаление активной интерпретации",
                value=False,
                key=f"interpretation_delete_confirm_{project_id}_{well_id}_{manager.interpretation_id}",
            )
            if st.button(
                "Удалить активную интерпретацию",
                key=f"interpretation_delete_{project_id}_{well_id}_{manager.interpretation_id}",
                disabled=len(catalog_items) <= 1 or not delete_confirmed,
                width="stretch",
            ):
                try:
                    catalog_repository.delete(manager.interpretation_id)
                except (KeyError, ValueError, OSError) as exc:
                    st.error(str(exc))
                else:
                    remaining = catalog_repository.list()
                    state[selector_key] = remaining[0].id
                    st.success("Интерпретация перемещена в корзину.")
                    st.rerun()

            deleted_interpretations = catalog_repository.list_deleted()
            if deleted_interpretations:
                restore_id = st.selectbox(
                    "Удалённая интерпретация",
                    options=[item.trash_id for item in deleted_interpretations],
                    format_func=lambda value: next(
                        (
                            f"{item.name} ({item.interpretation_id}) · {item.deleted_at}"
                            for item in deleted_interpretations
                            if item.trash_id == value
                        ),
                        value,
                    ),
                    key=f"interpretation_restore_select_{project_id}_{well_id}",
                )
                if st.button(
                    "Восстановить из корзины",
                    key=f"interpretation_restore_{project_id}_{well_id}",
                    width="stretch",
                ):
                    try:
                        restored_interpretation = catalog_repository.restore(restore_id)
                    except (KeyError, ValueError, OSError) as exc:
                        st.error(str(exc))
                    else:
                        state[selector_key] = restored_interpretation.id
                        st.success("Интерпретация восстановлена.")
                        st.rerun()


        actor_name_key = f"interpretation_actor_name_{project_id}_{well_id}"
        actor_role_key = f"interpretation_actor_role_{project_id}_{well_id}"
        actor_name = str(state.get(actor_name_key, "Локальный пользователь") or "Локальный пользователь")
        actor_role = str(state.get(actor_role_key, "administrator") or "administrator")
        if actor_role not in ROLES:
            actor_role = "administrator"
        publication_service = InterpretationPublicationService(
            root=root,
            project_id=project_id,
            well_id=well_id,
            interpretation_id=manager.interpretation_id,
            actor=InterpretationActor(id="local-user", name=actor_name, role=actor_role),
        )
        publication_state = publication_service.state()
        status_labels = {
            "draft": "Черновик",
            "in_review": "На согласовании",
            "approved": "Утверждена",
            "published": "Опубликована",
        }
        with st.expander("Согласование и публикация", expanded=publication_state.status != "draft"):
            actor_left, actor_right = st.columns(2)
            actor_name = actor_left.text_input(
                "Пользователь",
                value=actor_name,
                key=f"{actor_name_key}_input",
            )
            actor_role = actor_right.selectbox(
                "Роль",
                options=list(ROLES),
                index=list(ROLES).index(actor_role),
                format_func=lambda value: ROLE_LABELS_RU.get(value, value),
                key=f"{actor_role_key}_input",
            )
            state[actor_name_key] = actor_name
            state[actor_role_key] = actor_role
            publication_service = InterpretationPublicationService(
                root=root,
                project_id=project_id,
                well_id=well_id,
                interpretation_id=manager.interpretation_id,
                actor=InterpretationActor(id="local-user", name=actor_name, role=actor_role),
            )
            st.metric("Статус", status_labels.get(publication_state.status, publication_state.status))
            st.caption(f"Активная роль: {ROLE_LABELS_RU.get(actor_role, actor_role)}")
            if publication_state.is_locked:
                st.warning("Интерпретация заблокирована для изменения интервалов.")
            workflow_comment = st.text_area(
                "Комментарий к операции",
                key=f"interpretation_publication_comment_{project_id}_{well_id}_{manager.interpretation_id}",
            )
            try:
                if publication_state.status == "draft":
                    if st.button("Отправить на согласование", key=f"interpretation_submit_{project_id}_{well_id}_{manager.interpretation_id}", width="stretch"):
                        publication_service.submit_for_review(comment=workflow_comment)
                        st.success("Интерпретация отправлена на согласование.")
                        st.rerun()
                elif publication_state.status == "in_review":
                    review_left, review_right = st.columns(2)
                    if review_left.button("Вернуть в черновик", key=f"interpretation_return_{project_id}_{well_id}_{manager.interpretation_id}", width="stretch"):
                        publication_service.return_to_draft(comment=workflow_comment)
                        st.rerun()
                    if review_right.button("Утвердить", key=f"interpretation_approve_{project_id}_{well_id}_{manager.interpretation_id}", width="stretch"):
                        publication_service.approve(comment=workflow_comment)
                        st.rerun()
                elif publication_state.status == "approved":
                    approval_revisions = InterpretationRevisionRepository(
                        root=root, project_id=project_id, well_id=well_id, interpretation_id=manager.interpretation_id
                    ).list()
                    if approval_revisions:
                        publish_revision_id = st.selectbox(
                            "Ревизия для публикации",
                            options=[item.id for item in approval_revisions],
                            format_func=lambda value: next((f"{item.name} · {item.created_at}" for item in approval_revisions if item.id == value), value),
                            key=f"interpretation_publish_revision_{project_id}_{well_id}_{manager.interpretation_id}",
                        )
                        publish_left, publish_right = st.columns(2)
                        if publish_left.button("Открыть для редактирования", key=f"interpretation_reopen_{project_id}_{well_id}_{manager.interpretation_id}", width="stretch"):
                            publication_service.reopen(comment=workflow_comment)
                            st.rerun()
                        if publish_right.button("Опубликовать", key=f"interpretation_publish_{project_id}_{well_id}_{manager.interpretation_id}", width="stretch"):
                            publication_service.publish(revision_id=publish_revision_id, comment=workflow_comment)
                            st.rerun()
                    else:
                        st.info("Перед публикацией создайте ревизию текущего состояния.")
                        if st.button("Открыть для редактирования", key=f"interpretation_reopen_no_revision_{project_id}_{well_id}_{manager.interpretation_id}", width="stretch"):
                            publication_service.reopen(comment=workflow_comment)
                            st.rerun()
                elif publication_state.status == "published":
                    st.caption(f"Опубликованная ревизия: `{publication_state.published_revision_id}`")
                    if st.button("Снять с публикации", key=f"interpretation_unpublish_{project_id}_{well_id}_{manager.interpretation_id}", width="stretch"):
                        publication_service.unpublish(comment=workflow_comment)
                        st.rerun()
            except (KeyError, ValueError, OSError) as exc:
                st.error(str(exc))

            if publication_state.events:
                st.dataframe(
                    [
                        {
                            "Дата": event.created_at,
                            "Операция": event.action,
                            "Статус": f"{status_labels.get(event.from_status, event.from_status)} → {status_labels.get(event.to_status, event.to_status)}",
                            "Пользователь": event.actor_name or "—",
                            "Роль": ROLE_LABELS_RU.get(event.actor_role, event.actor_role or "—"),
                            "Комментарий": event.comment,
                            "Ревизия": event.revision_id,
                        }
                        for event in reversed(publication_state.events)
                    ],
                    width="stretch",
                    hide_index=True,
                )
                audit_json = export_publication_audit_json(
                    publication_state.events,
                    project_id=project_id,
                    well_id=well_id,
                    interpretation_id=manager.interpretation_id,
                )
                audit_csv = export_publication_audit_csv(publication_state.events)
                audit_xlsx = export_publication_audit_xlsx(
                    publication_state.events,
                    project_id=project_id,
                    well_id=well_id,
                    interpretation_id=manager.interpretation_id,
                )
                audit_json_col, audit_csv_col, audit_xlsx_col = st.columns(3)
                audit_json_col.download_button(
                    "Аудит JSON", data=audit_json,
                    file_name=f"{manager.interpretation_id}_publication_audit.json",
                    mime="application/json", width="stretch",
                )
                audit_csv_col.download_button(
                    "Аудит CSV", data=audit_csv,
                    file_name=f"{manager.interpretation_id}_publication_audit.csv",
                    mime="text/csv", width="stretch",
                )
                audit_xlsx_col.download_button(
                    "Аудит Excel", data=audit_xlsx,
                    file_name=f"{manager.interpretation_id}_publication_audit.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch",
                )

        revision_repository = InterpretationRevisionRepository(
            root=root,
            project_id=project_id,
            well_id=well_id,
            interpretation_id=manager.interpretation_id,
        )
        with st.expander("Ревизии активной интерпретации", expanded=False):
            revisions = revision_repository.list()
            st.caption(
                "Ревизия сохраняет интервалы и JSON-настройки активной интерпретации. "
                "Восстановление защищено от устаревшего предварительного просмотра."
            )
            with st.form(
                f"interpretation_revision_create_{project_id}_{well_id}_{manager.interpretation_id}",
                clear_on_submit=True,
            ):
                revision_name = st.text_input("Название ревизии", placeholder="Например: До корректировки пластов")
                revision_note = st.text_area("Комментарий к ревизии")
                revision_create_submitted = st.form_submit_button("Создать ревизию", width="stretch")
            if revision_create_submitted:
                try:
                    created_revision = revision_repository.create(name=revision_name, note=revision_note)
                except (ValueError, OSError) as exc:
                    st.error(str(exc))
                else:
                    st.success(
                        f"Ревизия создана: {created_revision.interval_count} интервалов, "
                        f"{created_revision.file_count} файлов."
                    )
                    st.rerun()

            if revisions:
                st.dataframe(
                    [
                        {
                            "ID": item.id,
                            "Название": item.name,
                            "Комментарий": item.note,
                            "Создана": item.created_at,
                            "Интервалы": item.interval_count,
                            "Файлы": item.file_count,
                        }
                        for item in revisions
                    ],
                    width="stretch",
                    hide_index=True,
                )
                selected_revision_id = st.selectbox(
                    "Выбранная ревизия",
                    options=[item.id for item in revisions],
                    format_func=lambda value: next(
                        (f"{item.name} · {item.created_at}" for item in revisions if item.id == value),
                        value,
                    ),
                    key=f"interpretation_revision_select_{project_id}_{well_id}_{manager.interpretation_id}",
                )
                try:
                    revision_diff = revision_repository.compare(selected_revision_id)
                except (KeyError, ValueError, OSError) as exc:
                    st.error(str(exc))
                    revision_diff = None
                if revision_diff is not None:
                    revision_metrics = st.columns(4)
                    revision_metrics[0].metric("Добавлено после ревизии", len(revision_diff.added))
                    revision_metrics[1].metric("Удалено после ревизии", len(revision_diff.removed))
                    revision_metrics[2].metric("Изменено", len(revision_diff.changed))
                    revision_metrics[3].metric("Без изменений", revision_diff.unchanged_count)
                    changed_rows = [
                        {
                            "UUID": before.id,
                            "Было": f"{before.label}: {before.top:g}–{before.base:g}",
                            "Стало": f"{after.label}: {after.top:g}–{after.base:g}",
                        }
                        for before, after in revision_diff.changed
                    ]
                    changed_rows.extend(
                        {"UUID": item.id, "Было": "—", "Стало": f"{item.label}: {item.top:g}–{item.base:g}"}
                        for item in revision_diff.added
                    )
                    changed_rows.extend(
                        {"UUID": item.id, "Было": f"{item.label}: {item.top:g}–{item.base:g}", "Стало": "—"}
                        for item in revision_diff.removed
                    )
                    if changed_rows:
                        st.dataframe(changed_rows, width="stretch", hide_index=True)
                    revision_restore_confirmed = st.checkbox(
                        "Подтверждаю восстановление выбранной ревизии",
                        value=False,
                        key=f"interpretation_revision_restore_confirm_{project_id}_{well_id}_{manager.interpretation_id}",
                    )
                    if st.button(
                        "Восстановить выбранную ревизию",
                        disabled=not revision_restore_confirmed,
                        key=f"interpretation_revision_restore_{project_id}_{well_id}_{manager.interpretation_id}",
                        width="stretch",
                    ):
                        try:
                            revision_repository.restore(
                                selected_revision_id,
                                expected_current_state_token=revision_diff.current_state_token,
                            )
                        except (KeyError, ValueError, OSError) as exc:
                            st.error(str(exc))
                        else:
                            st.success("Активная интерпретация восстановлена из ревизии.")
                            st.rerun()

                revision_delete_confirmed = st.checkbox(
                    "Подтверждаю удаление выбранной ревизии",
                    value=False,
                    key=f"interpretation_revision_delete_confirm_{project_id}_{well_id}_{manager.interpretation_id}",
                )
                if st.button(
                    "Удалить выбранную ревизию",
                    disabled=not revision_delete_confirmed,
                    key=f"interpretation_revision_delete_{project_id}_{well_id}_{manager.interpretation_id}",
                    width="stretch",
                ):
                    try:
                        deleted = revision_repository.delete(selected_revision_id)
                    except (ValueError, OSError) as exc:
                        st.error(str(exc))
                    else:
                        if deleted:
                            st.success("Ревизия удалена.")
                            st.rerun()

                keep_latest = st.number_input(
                    "Оставить последних ревизий",
                    min_value=1,
                    max_value=max(1, len(revisions)),
                    value=min(10, len(revisions)),
                    step=1,
                    key=f"interpretation_revision_keep_{project_id}_{well_id}_{manager.interpretation_id}",
                )
                if st.button(
                    "Очистить старые ревизии",
                    disabled=len(revisions) <= int(keep_latest),
                    key=f"interpretation_revision_prune_{project_id}_{well_id}_{manager.interpretation_id}",
                    width="stretch",
                ):
                    try:
                        removed_revision_ids = revision_repository.prune(keep_latest=int(keep_latest))
                    except (ValueError, OSError) as exc:
                        st.error(str(exc))
                    else:
                        st.success(f"Удалено старых ревизий: {len(removed_revision_ids)}.")
                        st.rerun()
            else:
                st.info("Для активной интерпретации ещё нет сохранённых ревизий.")

        if len(catalog_items) > 1:
            with st.expander("Сравнение и перенос интервалов", expanded=False):
                reference_ids = [item.id for item in catalog_items if item.id != manager.interpretation_id]
                reference_id = st.selectbox(
                    "Сравнить с интерпретацией",
                    options=reference_ids,
                    format_func=lambda value: next(
                        (f"{item.name} ({item.id})" for item in catalog_items if item.id == value),
                        value,
                    ),
                    key=f"interpretation_compare_reference_{project_id}_{well_id}_{manager.interpretation_id}",
                )
                comparison = compare_interpretation_intervals(
                    root=root,
                    project_id=project_id,
                    well_id=well_id,
                    source_interpretation_id=reference_id,
                    target_interpretation_id=manager.interpretation_id,
                )
                summary_columns = st.columns(4)
                summary_columns[0].metric("Новые", comparison.added_count)
                summary_columns[1].metric("Удалённые", comparison.removed_count)
                summary_columns[2].metric("Изменённые", comparison.modified_count)
                summary_columns[3].metric("Без изменений", comparison.unchanged_count)
                changed_differences = [item for item in comparison.differences if item.status != "unchanged"]
                if changed_differences:
                    st.dataframe(
                        [
                            {
                                "UUID": item.interval_id,
                                "Статус": item.status,
                                "Источник": item.source.label if item.source else "—",
                                "Цель": item.target.label if item.target else "—",
                                "Поля": ", ".join(item.changed_fields) or "—",
                                "Верх источника": item.source.top if item.source else None,
                                "Низ источника": item.source.base if item.source else None,
                            }
                            for item in changed_differences
                        ],
                        width="stretch",
                        hide_index=True,
                    )
                else:
                    st.info("Различий между интерпретациями нет.")

                transferable = [item for item in comparison.differences if item.source is not None and item.status != "unchanged"]
                if transferable:
                    selected_transfer_ids = st.multiselect(
                        "Интервалы из сравниваемой версии для переноса в активную",
                        options=[item.interval_id for item in transferable],
                        format_func=lambda value: next(
                            (
                                f"{item.source.label} · {item.source.top:g}–{item.source.base:g} м · {item.status}"
                                for item in transferable
                                if item.interval_id == value and item.source is not None
                            ),
                            value,
                        ),
                        key=f"interpretation_compare_transfer_ids_{project_id}_{well_id}_{manager.interpretation_id}_{reference_id}",
                    )
                    conflict_policy_label = st.selectbox(
                        "Конфликт одинакового UUID",
                        options=("Заменить целевой", "Пропустить", "Создать копию"),
                        key=f"interpretation_compare_conflict_{project_id}_{well_id}_{manager.interpretation_id}_{reference_id}",
                    )
                    conflict_policy = {
                        "Заменить целевой": "overwrite",
                        "Пропустить": "skip",
                        "Создать копию": "copy",
                    }[conflict_policy_label]
                    reject_transfer_overlaps = st.checkbox(
                        "Запретить пересечения после переноса",
                        value=False,
                        key=f"interpretation_compare_reject_overlaps_{project_id}_{well_id}_{manager.interpretation_id}_{reference_id}",
                    )
                    transfer_preview = None
                    if selected_transfer_ids:
                        transfer_service = InterpretationIntervalTransferService(
                            state,
                            root=root,
                            project_id=project_id,
                            well_id=well_id,
                            source_interpretation_id=reference_id,
                            target_interpretation_id=manager.interpretation_id,
                        )
                        try:
                            transfer_preview = transfer_service.preview(
                                selected_transfer_ids, conflict_policy=conflict_policy
                            )
                        except (KeyError, ValueError) as exc:
                            st.error(str(exc))
                        else:
                            st.caption(
                                f"Добавить: {transfer_preview.add_count} · "
                                f"заменить: {transfer_preview.overwrite_count} · "
                                f"пропустить: {transfer_preview.skip_count} · "
                                f"копировать: {transfer_preview.copy_count}"
                            )
                    transfer_confirmed = st.checkbox(
                        "Подтверждаю перенос выбранных интервалов",
                        value=False,
                        key=f"interpretation_compare_confirm_{project_id}_{well_id}_{manager.interpretation_id}_{reference_id}",
                    )
                    if st.button(
                        "Перенести в активную интерпретацию",
                        disabled=transfer_preview is None or not transfer_confirmed,
                        key=f"interpretation_compare_apply_{project_id}_{well_id}_{manager.interpretation_id}_{reference_id}",
                        width="stretch",
                    ):
                        try:
                            result = transfer_service.apply(
                                transfer_preview,
                                expected_confirmation_token=transfer_preview.confirmation_token,
                                reject_overlaps=reject_transfer_overlaps,
                            )
                        except (KeyError, ValueError) as exc:
                            st.error(str(exc))
                        else:
                            st.success(
                                f"Перенос завершён: добавлено {result.added_count}, "
                                f"заменено {result.overwritten_count}, "
                                f"пропущено {result.skipped_count}, копий {result.copied_count}."
                            )
                            st.rerun()

        if len(catalog_items) >= 3:
            with st.expander("Трёхстороннее объединение интерпретаций", expanded=False):
                merge_candidates = [item.id for item in catalog_items if item.id != manager.interpretation_id]
                merge_base_id = st.selectbox(
                    "Базовая интерпретация",
                    options=merge_candidates,
                    format_func=lambda value: next(
                        (f"{item.name} ({item.id})" for item in catalog_items if item.id == value), value
                    ),
                    key=f"interpretation_merge_base_{project_id}_{well_id}_{manager.interpretation_id}",
                )
                source_candidates = [item for item in merge_candidates if item != merge_base_id]
                merge_source_id = st.selectbox(
                    "Исходная интерпретация",
                    options=source_candidates,
                    format_func=lambda value: next(
                        (f"{item.name} ({item.id})" for item in catalog_items if item.id == value), value
                    ),
                    key=f"interpretation_merge_source_{project_id}_{well_id}_{manager.interpretation_id}",
                )
                merge_service = InterpretationIntervalMergeService(
                    state,
                    root=root,
                    project_id=project_id,
                    well_id=well_id,
                    base_interpretation_id=merge_base_id,
                    source_interpretation_id=merge_source_id,
                    target_interpretation_id=manager.interpretation_id,
                )
                try:
                    merge_preview = merge_service.preview()
                except (KeyError, ValueError) as exc:
                    st.error(str(exc))
                    merge_preview = None
                if merge_preview is not None:
                    merge_metrics = st.columns(4)
                    merge_metrics[0].metric("Автоматически", merge_preview.automatic_count)
                    merge_metrics[1].metric("Конфликты", merge_preview.conflict_count)
                    merge_metrics[2].metric("Без изменений", merge_preview.unchanged_count)
                    merge_metrics[3].metric("Удаления", merge_preview.delete_count)
                    if merge_preview.conflicts:
                        st.dataframe(
                            [
                                {
                                    "UUID": item.interval_id,
                                    "База": item.base.label if item.base else "—",
                                    "Источник": item.source.label if item.source else "—",
                                    "Цель": item.target.label if item.target else "—",
                                    "Поля": ", ".join(item.changed_fields),
                                }
                                for item in merge_preview.conflicts
                            ],
                            width="stretch",
                            hide_index=True,
                        )
                    merge_policy_label = st.selectbox(
                        "Разрешение конфликтов",
                        options=("Сохранить целевую версию", "Принять исходную версию", "Пропустить конфликт"),
                        key=f"interpretation_merge_policy_{project_id}_{well_id}_{manager.interpretation_id}",
                    )
                    merge_policy = {
                        "Сохранить целевую версию": "target",
                        "Принять исходную версию": "source",
                        "Пропустить конфликт": "skip",
                    }[merge_policy_label]
                    merge_reject_overlaps = st.checkbox(
                        "Запретить пересечения после объединения",
                        value=False,
                        key=f"interpretation_merge_overlap_{project_id}_{well_id}_{manager.interpretation_id}",
                    )
                    merge_confirmed = st.checkbox(
                        "Подтверждаю объединение в активную интерпретацию",
                        value=False,
                        key=f"interpretation_merge_confirm_{project_id}_{well_id}_{manager.interpretation_id}",
                    )
                    if st.button(
                        "Объединить интерпретации",
                        disabled=not merge_confirmed,
                        key=f"interpretation_merge_apply_{project_id}_{well_id}_{manager.interpretation_id}",
                        width="stretch",
                    ):
                        try:
                            merge_result = merge_service.apply(
                                merge_preview,
                                expected_confirmation_token=merge_preview.confirmation_token,
                                conflict_policy=merge_policy,
                                reject_overlaps=merge_reject_overlaps,
                            )
                        except (KeyError, ValueError) as exc:
                            st.error(str(exc))
                        else:
                            st.success(
                                f"Объединение завершено: автоматически {merge_result.automatic_count}, "
                                f"разрешено конфликтов {merge_result.resolved_conflict_count}, "
                                f"пропущено {merge_result.skipped_conflict_count}."
                            )
                            st.rerun()

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
                journal_filter_left, journal_filter_right = st.columns((1, 2))
                journal_status_label = journal_filter_left.selectbox(
                    "Статус",
                    options=("Все", "Выполненные", "Отменённые"),
                    key=f"manual_interval_type_journal_status_{project_id}",
                )
                journal_query = journal_filter_right.text_input(
                    "Поиск по типам",
                    placeholder="ID исходного или целевого типа",
                    key=f"manual_interval_type_journal_query_{project_id}",
                )
                status_map = {
                    "Все": "all",
                    "Выполненные": "completed",
                    "Отменённые": "undone",
                }
                journal_status = status_map[journal_status_label]
                journal_total = type_repository.count_operations(
                    status=journal_status,
                    query=journal_query,
                )
                pagination_left, pagination_right = st.columns((1, 1))
                journal_page_size = int(
                    pagination_left.selectbox(
                        "Строк на странице",
                        options=(10, 25, 50),
                        index=1,
                        key=f"manual_interval_type_journal_page_size_{project_id}",
                    )
                )
                journal_page_count = max(1, (journal_total + journal_page_size - 1) // journal_page_size)
                journal_page = int(
                    pagination_right.number_input(
                        "Страница",
                        min_value=1,
                        max_value=journal_page_count,
                        value=1,
                        step=1,
                        key=f"manual_interval_type_journal_page_{project_id}",
                    )
                )
                type_operations = type_repository.list_operations(
                    limit=journal_page_size,
                    offset=(journal_page - 1) * journal_page_size,
                    status=journal_status,
                    query=journal_query,
                )
                st.caption(
                    f"Найдено операций: {journal_total}. "
                    f"Страница {journal_page} из {journal_page_count}."
                )
                if not type_operations:
                    st.caption("Операции, соответствующие фильтру, не найдены.")
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
                                "Статус": "Отменена" if item.undone_at else "Выполнена",
                            }
                            for item in type_operations
                        ],
                        width="stretch",
                        hide_index=True,
                    )
                    operation_labels = {
                        item.id: (
                            f"{item.created_at} · {item.source_type_id} → "
                            f"{item.target_type_id} · {item.id}"
                        )
                        for item in type_operations
                    }
                    selected_operation_id = st.selectbox(
                        "Детальная карточка операции",
                        options=tuple(operation_labels),
                        format_func=lambda value: operation_labels[value],
                        key=f"manual_interval_type_journal_detail_{project_id}",
                    )
                    selected_operation = type_repository.get_operation(selected_operation_id)
                    if selected_operation is not None:
                        with st.container(border=True):
                            st.code(selected_operation.id, language=None)
                            detail_left, detail_right = st.columns(2)
                            detail_left.markdown(
                                f"**Типы:** `{selected_operation.source_type_id}` → "
                                f"`{selected_operation.target_type_id}`\n\n"
                                f"**Создана:** {selected_operation.created_at}\n\n"
                                f"**Статус:** "
                                f"{'Отменена' if selected_operation.undone_at else 'Выполнена'}"
                            )
                            detail_right.markdown(
                                f"**Интервалы:** {selected_operation.interval_count}\n\n"
                                f"**Скважины:** {selected_operation.well_count}\n\n"
                                f"**Интерпретации:** {selected_operation.interpretation_count}\n\n"
                                f"**Цвет целевого типа:** "
                                f"{'применён' if selected_operation.target_color_applied else 'сохранены текущие цвета'}"
                            )
                            if selected_operation.undone_at:
                                st.caption(f"Отменена: {selected_operation.undone_at}")

                    journal_json = export_type_operations_json(
                        type_operations, project_id=project_id
                    )
                    journal_csv = export_type_operations_csv(type_operations)
                    journal_xlsx = export_type_operations_xlsx(
                        type_operations, project_id=project_id
                    )
                    journal_left, journal_mid, journal_right = st.columns(3)
                    journal_left.download_button(
                        "Журнал JSON",
                        data=journal_json,
                        file_name=f"interval_type_operations_{project_id}.json",
                        mime="application/json",
                        key=f"manual_interval_type_journal_json_{project_id}",
                        width="stretch",
                    )
                    journal_mid.download_button(
                        "Журнал CSV",
                        data=journal_csv,
                        file_name=f"interval_type_operations_{project_id}.csv",
                        mime="text/csv",
                        key=f"manual_interval_type_journal_csv_{project_id}",
                        width="stretch",
                    )
                    journal_right.download_button(
                        "Журнал Excel",
                        data=journal_xlsx,
                        file_name=f"interval_type_operations_{project_id}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"manual_interval_type_journal_xlsx_{project_id}",
                        width="stretch",
                    )

                    latest_operation = type_repository.list_operations(limit=1)[0]
                    undo_confirmed = st.checkbox(
                        "Подтверждаю отмену последнего проектного переназначения",
                        value=False,
                        key=f"manual_interval_type_operation_undo_confirm_{project_id}",
                        disabled=not latest_operation.undo_available or bool(latest_operation.undone_at),
                    )
                    if st.button(
                        "Отменить последнее переназначение",
                        key=f"manual_interval_type_operation_undo_{project_id}",
                        disabled=(
                            not latest_operation.undo_available
                            or bool(latest_operation.undone_at)
                            or not undo_confirmed
                        ),
                        width="stretch",
                    ):
                        try:
                            restored = type_repository.undo_last_reassignment()
                        except ValueError as exc:
                            st.error(str(exc))
                        else:
                            st.success(
                                f"Переназначение {restored.source_type_id} → "
                                f"{restored.target_type_id} отменено."
                            )
                            st.rerun()

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

            with st.expander("Поиск, фильтры и аналитика", expanded=False):
                filter_keys = {
                    "query": f"manual_interval_filter_query_{project_id}_{well_id}",
                    "types": f"manual_interval_filter_types_{project_id}_{well_id}",
                    "sources": f"manual_interval_filter_sources_{project_id}_{well_id}",
                    "depth_enabled": f"manual_interval_filter_depth_enabled_{project_id}_{well_id}",
                    "depth_top": f"manual_interval_filter_depth_top_{project_id}_{well_id}",
                    "depth_base": f"manual_interval_filter_depth_base_{project_id}_{well_id}",
                    "thickness_enabled": f"manual_interval_filter_thickness_enabled_{project_id}_{well_id}",
                    "min_thickness": f"manual_interval_filter_min_thickness_{project_id}_{well_id}",
                    "max_thickness": f"manual_interval_filter_max_thickness_{project_id}_{well_id}",
                }
                with st.expander("Сохранённые представления", expanded=False):
                    if filter_presets:
                        preset_ids = [item.id for item in filter_presets]
                        preset_labels = {item.id: item.name for item in filter_presets}
                        selected_preset_id = st.selectbox(
                            "Представление",
                            options=preset_ids,
                            format_func=lambda value: preset_labels.get(value, value),
                            key=f"manual_interval_filter_preset_selected_{project_id}_{well_id}",
                        )
                        preset_load, preset_delete = st.columns(2)
                        if preset_load.button(
                            "Применить",
                            key=f"manual_interval_filter_preset_apply_{project_id}_{well_id}",
                            width="stretch",
                        ):
                            selected_preset = preset_repository.get(selected_preset_id)
                            criteria = selected_preset.criteria
                            st.session_state[filter_keys["query"]] = criteria.query
                            st.session_state[filter_keys["types"]] = list(criteria.interval_types)
                            st.session_state[filter_keys["sources"]] = list(criteria.sources)
                            st.session_state[filter_keys["depth_enabled"]] = (
                                criteria.depth_top is not None or criteria.depth_base is not None
                            )
                            if criteria.depth_top is not None:
                                st.session_state[filter_keys["depth_top"]] = criteria.depth_top
                            if criteria.depth_base is not None:
                                st.session_state[filter_keys["depth_base"]] = criteria.depth_base
                            st.session_state[filter_keys["thickness_enabled"]] = (
                                criteria.min_thickness is not None or criteria.max_thickness is not None
                            )
                            if criteria.min_thickness is not None:
                                st.session_state[filter_keys["min_thickness"]] = criteria.min_thickness
                            if criteria.max_thickness is not None:
                                st.session_state[filter_keys["max_thickness"]] = criteria.max_thickness
                            st.success(f"Применено представление: {selected_preset.name}.")
                            st.rerun()
                        if preset_delete.button(
                            "Удалить",
                            key=f"manual_interval_filter_preset_delete_{project_id}_{well_id}",
                            width="stretch",
                        ):
                            preset_repository.delete(selected_preset_id)
                            st.success("Представление удалено.")
                            st.rerun()
                    else:
                        st.caption("Сохранённых представлений пока нет.")

                    preset_import = st.file_uploader(
                        "Импорт представлений JSON",
                        type=["json"],
                        key=f"manual_interval_filter_preset_import_{project_id}_{well_id}",
                    )
                    preset_exchange_left, preset_exchange_right = st.columns(2)
                    if filter_presets:
                        preset_exchange_left.download_button(
                            "Экспорт JSON",
                            data=export_filter_presets_json(
                                filter_presets,
                                project_id=project_id,
                                well_id=well_id,
                                interpretation_id=manager.interpretation_id,
                            ),
                            file_name=f"interpretation_filter_presets_{project_id}_{well_id}.json",
                            mime="application/json",
                            key=f"manual_interval_filter_preset_export_{project_id}_{well_id}",
                            width="stretch",
                        )
                    if preset_exchange_right.button(
                        "Импортировать",
                        key=f"manual_interval_filter_preset_import_apply_{project_id}_{well_id}",
                        disabled=preset_import is None,
                        width="stretch",
                    ):
                        try:
                            imported_presets = import_filter_presets_json(preset_import.getvalue())
                            preset_repository.replace_all(imported_presets)
                        except ValueError as exc:
                            st.error(str(exc))
                        else:
                            st.success(f"Импортировано представлений: {len(imported_presets)}.")
                            st.rerun()

                filter_query = st.text_input(
                    "Поиск",
                    placeholder="Подпись, UUID, тип, комментарий или источник",
                    key=filter_keys["query"],
                )
                available_types = sorted({item.interval_type for item in intervals})
                available_sources = sorted({item.source for item in intervals})
                filter_left, filter_right = st.columns(2)
                filter_types = filter_left.multiselect(
                    "Типы",
                    options=available_types,
                    key=filter_keys["types"],
                )
                filter_sources = filter_right.multiselect(
                    "Источники",
                    options=available_sources,
                    key=filter_keys["sources"],
                )
                depth_left, depth_right = st.columns(2)
                use_depth_filter = depth_left.checkbox(
                    "Ограничить диапазон глубин",
                    value=False,
                    key=filter_keys["depth_enabled"],
                )
                use_thickness_filter = depth_right.checkbox(
                    "Ограничить мощность",
                    value=False,
                    key=filter_keys["thickness_enabled"],
                )
                min_project_depth = min(item.top for item in intervals)
                max_project_depth = max(item.base for item in intervals)
                range_left, range_right = st.columns(2)
                filter_depth_top = range_left.number_input(
                    "Верх диапазона, м",
                    value=float(min_project_depth),
                    step=0.1,
                    disabled=not use_depth_filter,
                    key=filter_keys["depth_top"],
                )
                filter_depth_base = range_right.number_input(
                    "Низ диапазона, м",
                    value=float(max_project_depth),
                    step=0.1,
                    disabled=not use_depth_filter,
                    key=filter_keys["depth_base"],
                )
                thickness_left, thickness_right = st.columns(2)
                filter_min_thickness = thickness_left.number_input(
                    "Минимальная мощность, м",
                    min_value=0.0,
                    value=0.0,
                    step=0.1,
                    disabled=not use_thickness_filter,
                    key=filter_keys["min_thickness"],
                )
                filter_max_thickness = thickness_right.number_input(
                    "Максимальная мощность, м",
                    min_value=0.0,
                    value=float(max(item.thickness for item in intervals)),
                    step=0.1,
                    disabled=not use_thickness_filter,
                    key=filter_keys["max_thickness"],
                )
                try:
                    filtered_intervals = filter_interpretation_intervals(
                        intervals,
                        InterpretationIntervalFilter(
                            query=filter_query,
                            interval_types=tuple(filter_types),
                            sources=tuple(filter_sources),
                            depth_top=filter_depth_top if use_depth_filter else None,
                            depth_base=filter_depth_base if use_depth_filter else None,
                            min_thickness=filter_min_thickness if use_thickness_filter else None,
                            max_thickness=filter_max_thickness if use_thickness_filter else None,
                        ),
                    )
                except ValueError as exc:
                    st.error(str(exc))
                    filtered_intervals = ()

                current_filter_criteria = InterpretationIntervalFilter(
                    query=filter_query,
                    interval_types=tuple(filter_types),
                    sources=tuple(filter_sources),
                    depth_top=filter_depth_top if use_depth_filter else None,
                    depth_base=filter_depth_base if use_depth_filter else None,
                    min_thickness=filter_min_thickness if use_thickness_filter else None,
                    max_thickness=filter_max_thickness if use_thickness_filter else None,
                )
                save_name_col, save_button_col = st.columns((3, 1))
                preset_name = save_name_col.text_input(
                    "Название представления",
                    placeholder="Например: Газовые интервалы 1000–1200 м",
                    key=f"manual_interval_filter_preset_name_{project_id}_{well_id}",
                )
                if save_button_col.button(
                    "Сохранить",
                    key=f"manual_interval_filter_preset_save_{project_id}_{well_id}",
                    width="stretch",
                ):
                    try:
                        preset_repository.save(name=preset_name, criteria=current_filter_criteria)
                    except ValueError as exc:
                        st.error(str(exc))
                    else:
                        st.success("Представление сохранено.")
                        st.rerun()

                summary = summarize_interpretation_intervals(filtered_intervals)
                metric_a, metric_b, metric_c, metric_d = st.columns(4)
                metric_a.metric("Найдено", summary.count)
                metric_b.metric("Суммарная мощность, м", f"{summary.total_thickness:g}")
                metric_c.metric("Покрытая глубина, м", f"{summary.covered_depth:g}")
                metric_d.metric("Типов", summary.type_count)
                if summary.by_type:
                    st.dataframe(
                        [
                            {
                                "Тип": item.interval_type,
                                "Интервалы": item.count,
                                "Суммарная мощность, м": item.total_thickness,
                                "Средняя мощность, м": item.average_thickness,
                                "Диапазон, м": f"{item.min_top:g}–{item.max_base:g}",
                            }
                            for item in summary.by_type
                        ],
                        width="stretch",
                        hide_index=True,
                    )
                if filtered_intervals:
                    filtered_json = export_interpretation_intervals_json(
                        filtered_intervals,
                        project_id=project_id,
                        well_id=well_id,
                        interpretation_id=manager.interpretation_id,
                    )
                    filtered_csv = export_interpretation_intervals_csv(filtered_intervals)
                    filtered_xlsx = export_interpretation_intervals_xlsx(
                        filtered_intervals,
                        project_id=project_id,
                        well_id=well_id,
                        interpretation_id=manager.interpretation_id,
                    )
                    filtered_left, filtered_mid, filtered_right = st.columns(3)
                    filtered_left.download_button(
                        "Выборка JSON",
                        data=filtered_json,
                        file_name=f"interpretation_intervals_filtered_{project_id}_{well_id}.json",
                        mime="application/json",
                        key=f"manual_interval_filtered_json_{project_id}_{well_id}",
                        width="stretch",
                    )
                    filtered_mid.download_button(
                        "Выборка CSV",
                        data=filtered_csv,
                        file_name=f"interpretation_intervals_filtered_{project_id}_{well_id}.csv",
                        mime="text/csv",
                        key=f"manual_interval_filtered_csv_{project_id}_{well_id}",
                        width="stretch",
                    )
                    filtered_right.download_button(
                        "Выборка Excel",
                        data=filtered_xlsx,
                        file_name=f"interpretation_intervals_filtered_{project_id}_{well_id}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"manual_interval_filtered_xlsx_{project_id}_{well_id}",
                        width="stretch",
                    )
                else:
                    st.info("По заданным условиям интервалы не найдены.")

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

        if not filtered_intervals:
            st.info("Измените фильтры, чтобы выбрать и редактировать интервалы.")
            return

        option_ids = [item.id for item in filtered_intervals]
        option_labels = {
            item.id: f"{item.label} · {item.top:g}–{item.base:g} м · {item.interval_type}"
            for item in filtered_intervals
        }
        selected_id = st.selectbox(
            "Выбранный интервал",
            options=option_ids,
            format_func=lambda value: option_labels.get(value, value),
            key=f"manual_interval_selected_{project_id}_{well_id}",
        )
        selected = properties_service.get(selected_id)

        with st.expander("Групповые операции", expanded=False):
            batch_service = InterpretationIntervalBatchService(manager)
            batch_ids = st.multiselect(
                "Выбранные интервалы",
                options=option_ids,
                format_func=lambda value: option_labels.get(value, value),
                key=f"manual_interval_batch_selected_{project_id}_{well_id}",
            )
            batch_type_ids = [item.id for item in interval_types] or ["undefined"]
            batch_type = st.selectbox(
                "Новый тип",
                options=batch_type_ids,
                format_func=lambda value: next(
                    (f"{item.name} ({item.id})" for item in interval_types if item.id == value),
                    value,
                ),
                key=f"manual_interval_batch_type_{project_id}_{well_id}",
            )
            batch_apply_color = st.checkbox(
                "Применить цвет выбранного типа",
                value=True,
                key=f"manual_interval_batch_apply_color_{project_id}_{well_id}",
            )
            batch_color = next(
                (item.color for item in interval_types if item.id == batch_type),
                "#4C78A8",
            )
            batch_left, batch_right = st.columns(2)
            if batch_left.button(
                "Изменить тип",
                key=f"manual_interval_batch_assign_{project_id}_{well_id}",
                disabled=not batch_ids,
                width="stretch",
            ):
                try:
                    preview = batch_service.preview_assign_type(
                        batch_ids,
                        interval_type=batch_type,
                        color=batch_color if batch_apply_color else None,
                    )
                    result = batch_service.confirm_assign_type(
                        preview,
                        interval_type=batch_type,
                        color=batch_color if batch_apply_color else None,
                    )
                except (ValueError, KeyError) as exc:
                    st.error(str(exc))
                else:
                    st.success(f"Изменено интервалов: {result.changed_count}.")
                    st.rerun()
            st.markdown("**Комментарий и источник**")
            metadata_left, metadata_right = st.columns(2)
            batch_comment_enabled = metadata_left.checkbox(
                "Изменить комментарий",
                value=False,
                key=f"manual_interval_batch_comment_enabled_{project_id}_{well_id}",
            )
            batch_source_enabled = metadata_right.checkbox(
                "Изменить источник",
                value=False,
                key=f"manual_interval_batch_source_enabled_{project_id}_{well_id}",
            )
            batch_comment_mode = st.radio(
                "Режим комментария",
                options=("replace", "append"),
                format_func=lambda value: "Заменить" if value == "replace" else "Добавить к существующему",
                horizontal=True,
                disabled=not batch_comment_enabled,
                key=f"manual_interval_batch_comment_mode_{project_id}_{well_id}",
            )
            batch_comment = st.text_area(
                "Комментарий для выбранных интервалов",
                disabled=not batch_comment_enabled,
                key=f"manual_interval_batch_comment_{project_id}_{well_id}",
            )
            batch_source = st.text_input(
                "Источник для выбранных интервалов",
                disabled=not batch_source_enabled,
                key=f"manual_interval_batch_source_{project_id}_{well_id}",
            )
            if st.button(
                "Изменить комментарий и источник",
                key=f"manual_interval_batch_metadata_{project_id}_{well_id}",
                disabled=(
                    not batch_ids
                    or (not batch_comment_enabled and not batch_source_enabled)
                ),
                width="stretch",
            ):
                try:
                    preview = batch_service.preview_edit_metadata(
                        batch_ids,
                        comment=batch_comment if batch_comment_enabled else None,
                        comment_mode=batch_comment_mode,
                        source=batch_source if batch_source_enabled else None,
                    )
                    result = batch_service.confirm_edit_metadata(
                        preview,
                        comment=batch_comment if batch_comment_enabled else None,
                        comment_mode=batch_comment_mode,
                        source=batch_source if batch_source_enabled else None,
                    )
                except (ValueError, KeyError) as exc:
                    st.error(str(exc))
                else:
                    st.success(f"Изменено интервалов: {result.changed_count}.")
                    st.rerun()

            if batch_ids:
                with st.expander("Предварительный просмотр групповых изменений", expanded=False):
                    try:
                        type_preview = batch_service.preview_assign_type(
                            batch_ids,
                            interval_type=batch_type,
                            color=batch_color if batch_apply_color else None,
                        )
                        st.caption(
                            f"Изменение типа: будет изменено {type_preview.changed_count} "
                            f"из {type_preview.selected_count} интервалов."
                        )
                        st.dataframe(
                            [
                                {
                                    "Интервал": item.label,
                                    "Глубины, м": f"{item.top:g}–{item.base:g}",
                                    "Текущий тип": item.current_type,
                                    "Новый тип": item.target_type,
                                    "Текущий цвет": item.current_color,
                                    "Новый цвет": item.target_color,
                                    "Изменится": "Да" if item.will_change else "Нет",
                                }
                                for item in type_preview.items
                            ],
                            width="stretch",
                            hide_index=True,
                        )

                        if batch_comment_enabled or batch_source_enabled:
                            metadata_preview = batch_service.preview_edit_metadata(
                                batch_ids,
                                comment=batch_comment if batch_comment_enabled else None,
                                comment_mode=batch_comment_mode,
                                source=batch_source if batch_source_enabled else None,
                            )
                            st.caption(
                                f"Метаданные: будет изменено {metadata_preview.changed_count} "
                                f"из {metadata_preview.selected_count} интервалов."
                            )
                            st.dataframe(
                                [
                                    {
                                        "Интервал": item.label,
                                        "Текущий источник": item.current_source,
                                        "Новый источник": item.target_source,
                                        "Текущий комментарий": item.current_comment,
                                        "Новый комментарий": item.target_comment,
                                        "Изменится": "Да" if item.will_change else "Нет",
                                    }
                                    for item in metadata_preview.items
                                ],
                                width="stretch",
                                hide_index=True,
                            )

                        delete_preview = batch_service.preview_delete(batch_ids)
                        st.caption(
                            f"Удаление затронет {delete_preview.changed_count} "
                            f"интервалов после отдельного подтверждения."
                        )
                    except (ValueError, KeyError) as exc:
                        st.warning(str(exc))

            batch_journal = batch_service.list_journal(limit=10)
            if batch_journal:
                with st.expander("Журнал групповых операций", expanded=False):
                    st.dataframe(
                        [
                            {
                                "Дата": entry.get("timestamp", ""),
                                "Операция": entry.get("action", ""),
                                "Выбрано": entry.get("selected_count", 0),
                                "Изменено": entry.get("changed_count", 0),
                            }
                            for entry in batch_journal
                        ],
                        width="stretch",
                        hide_index=True,
                    )

            batch_delete_confirm = st.checkbox(
                "Подтверждаю групповое удаление",
                value=False,
                key=f"manual_interval_batch_delete_confirm_{project_id}_{well_id}",
            )
            if batch_right.button(
                "Удалить выбранные",
                key=f"manual_interval_batch_delete_{project_id}_{well_id}",
                disabled=not batch_ids or not batch_delete_confirm,
                width="stretch",
            ):
                try:
                    preview = batch_service.preview_delete(batch_ids)
                    result = batch_service.confirm_delete(preview)
                except (ValueError, KeyError) as exc:
                    st.error(str(exc))
                else:
                    state.pop(f"manual_interval_selected_{project_id}_{well_id}", None)
                    st.success(f"Удалено интервалов: {result.changed_count}.")
                    st.rerun()

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
