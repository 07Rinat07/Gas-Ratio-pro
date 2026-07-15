from __future__ import annotations

"""Streamlit UI for project-level multi-well interpretation correlation."""

from dataclasses import asdict
from pathlib import Path
from typing import Any, MutableMapping

from projects.interpretation_correlation import (
    CorrelationEndpoint,
    CorrelationTie,
    export_correlation_csv,
    export_correlation_json,
)
from projects.interpretation_correlation_commands import CorrelationHistoryConflict
from projects.interpretation_correlation_suggestions import (
    CorrelationSuggestionSettings,
    build_correlation_suggestions,
    compare_suggestion_scenarios,
    suggestion_preview_from_dict,
    validate_suggestion_preview,
)
from projects.interpretation_correlation_quality import (
    analyze_correlation_quality,
    build_correlation_quality_issue_rows,
    export_correlation_quality_csv,
    export_correlation_quality_json,
)
from projects.interpretation_correlation_chart import (
    CorrelationChartSettings,
    build_correlation_figure,
    build_correlation_payload,
    export_correlation_svg,
)
from projects.repository import DEFAULT_PROJECTS_ROOT
from core.repository_io import RepositoryIOMetrics
from core.runtime_service_registry import runtime_service_registry
from core.application_service_container import application_service_container


def _source_key(item: Any) -> str:
    return f"{item.well_id}|{item.interpretation_id}|{item.revision_id}"


def render_interpretation_correlation_panel(
    st: Any,
    *,
    state: MutableMapping[str, Any],
    project_id: str,
    root: Path | str = DEFAULT_PROJECTS_ROOT,
) -> None:
    registry = runtime_service_registry(state)
    io_metrics = registry.ensure(
        "repository_io_metrics", RepositoryIOMetrics, expected_type=RepositoryIOMetrics
    )
    application = application_service_container(state).correlation(
        root=root, project_id=project_id, io_metrics=io_metrics
    )
    sources = application.list_published_inputs()
    workspaces = application.list_workspaces()

    with st.expander("Корреляция опубликованных интерпретаций", expanded=False):
        st.caption("Корреляционные связи используют только опубликованные ревизии и не изменяют исходные интервалы.")
        if len({item.well_id for item in sources}) < 2:
            st.info("Для корреляции опубликуйте интерпретации как минимум двух разных скважин.")
            return

        with st.form(f"correlation_create_{project_id}", clear_on_submit=True):
            name = st.text_input("Название корреляционного проекта")
            description = st.text_area("Описание")
            create_clicked = st.form_submit_button("Создать корреляционный проект", width="stretch")
        if create_clicked:
            try:
                created = application.create_workspace(name=name, description=description)
            except (ValueError, OSError) as exc:
                st.error(str(exc))
            else:
                state[f"correlation_workspace_{project_id}"] = created.id
                st.success("Корреляционный проект создан.")
                st.rerun()

        if not workspaces:
            st.info("Корреляционные проекты ещё не созданы.")
            return

        workspace_ids = [item.id for item in workspaces]
        selector_key = f"correlation_workspace_{project_id}"
        if state.get(selector_key) not in workspace_ids:
            state[selector_key] = workspace_ids[0]
        workspace_id = st.selectbox(
            "Активный корреляционный проект",
            options=workspace_ids,
            format_func=lambda value: next((item.name for item in workspaces if item.id == value), value),
            key=selector_key,
        )
        workspace = application.get_workspace(workspace_id)
        service = application.workspace_service(workspace.id)
        commands = application.command_service(state, workspace.id)
        history = commands.history_status()
        undo_col, redo_col, history_col = st.columns([1, 1, 2])
        if undo_col.button(
            "Отменить", disabled=not history["can_undo"],
            key=f"correlation_undo_{workspace.id}", width="stretch",
        ):
            try:
                commands.undo()
            except (CorrelationHistoryConflict, ValueError, KeyError, OSError) as exc:
                st.error(str(exc))
            else:
                st.rerun()
        if redo_col.button(
            "Повторить", disabled=not history["can_redo"],
            key=f"correlation_redo_{workspace.id}", width="stretch",
        ):
            try:
                commands.redo()
            except (CorrelationHistoryConflict, ValueError, KeyError, OSError) as exc:
                st.error(str(exc))
            else:
                st.rerun()
        history_col.caption(
            f"История: {history['undo_count']} отмен · {history['redo_count']} повторов"
        )

        source_map = {_source_key(item): item for item in sources}
        source_options = list(source_map)
        left_col, right_col = st.columns(2)
        left_key = left_col.selectbox(
            "Левая скважина / ревизия",
            options=source_options,
            format_func=lambda value: f"{source_map[value].well_id} · {source_map[value].interpretation_id} · {source_map[value].revision_name}",
            key=f"correlation_left_source_{workspace.id}",
        )
        right_candidates = [key for key in source_options if source_map[key].well_id != source_map[left_key].well_id]
        right_key = right_col.selectbox(
            "Правая скважина / ревизия",
            options=right_candidates,
            format_func=lambda value: f"{source_map[value].well_id} · {source_map[value].interpretation_id} · {source_map[value].revision_name}",
            key=f"correlation_right_source_{workspace.id}",
        )
        left_source, right_source = source_map[left_key], source_map[right_key]
        if not left_source.intervals or not right_source.intervals:
            st.warning("Одна из опубликованных ревизий не содержит ручных интервалов.")
        else:
            with st.form(f"correlation_tie_{workspace.id}", clear_on_submit=True):
                interval_left, interval_right = st.columns(2)
                left_id = interval_left.selectbox(
                    "Левый интервал",
                    options=[item.id for item in left_source.intervals],
                    format_func=lambda value: next(
                        f"{item.label} · {item.top:g}–{item.base:g} м" for item in left_source.intervals if item.id == value
                    ),
                )
                right_id = interval_right.selectbox(
                    "Правый интервал",
                    options=[item.id for item in right_source.intervals],
                    format_func=lambda value: next(
                        f"{item.label} · {item.top:g}–{item.base:g} м" for item in right_source.intervals if item.id == value
                    ),
                )
                left_interval = next(item for item in left_source.intervals if item.id == left_id)
                right_interval = next(item for item in right_source.intervals if item.id == right_id)
                depth_left, depth_right = st.columns(2)
                left_depth = depth_left.number_input(
                    "Опорная глубина слева, м", min_value=float(left_interval.top), max_value=float(left_interval.base),
                    value=float(left_interval.middle_depth), format="%.3f",
                )
                right_depth = depth_right.number_input(
                    "Опорная глубина справа, м", min_value=float(right_interval.top), max_value=float(right_interval.base),
                    value=float(right_interval.middle_depth), format="%.3f",
                )
                tie_name = st.text_input("Название связи")
                tie_note = st.text_area("Комментарий к связи")
                add_clicked = st.form_submit_button("Добавить корреляционную связь", width="stretch")
            if add_clicked:
                try:
                    commands.add_tie(
                        left=CorrelationEndpoint(left_source.well_id, left_source.interpretation_id, left_source.revision_id,
                                                 left_interval.id, float(left_depth), left_interval.label),
                        right=CorrelationEndpoint(right_source.well_id, right_source.interpretation_id, right_source.revision_id,
                                                  right_interval.id, float(right_depth), right_interval.label),
                        name=tie_name, note=tie_note,
                    )
                except (ValueError, KeyError, OSError) as exc:
                    st.error(str(exc))
                else:
                    st.success("Корреляционная связь добавлена.")
                    st.rerun()

        workspace = application.get_workspace(workspace.id)

        with st.expander("Автоматические предложения связей", expanded=False):
            st.caption("Настраиваемая детерминированная модель по типу, подписи и близости глубин. Сначала preview, затем подтверждение.")
            profiles = application.list_suggestion_profiles()
            selected_profile_id = st.selectbox(
                "Профиль калибровки",
                options=[""] + [str(item["id"]) for item in profiles],
                format_func=lambda value: "Текущие настройки" if not value else next(
                    str(item["name"]) for item in profiles if item["id"] == value
                ),
                key=f"correlation_suggestion_profile_{workspace.id}",
            )
            profile_settings = next(
                (item.get("settings", {}) for item in profiles if item.get("id") == selected_profile_id), {}
            )
            calibration_cols = st.columns(2)
            max_delta = calibration_cols[0].number_input(
                "Максимальная разница глубин, м", min_value=1.0, max_value=1000.0,
                value=float(profile_settings.get("max_depth_delta", 50.0)), step=5.0,
                key=f"correlation_suggestion_delta_{workspace.id}_{selected_profile_id}",
            )
            min_confidence = calibration_cols[1].slider(
                "Минимальная уверенность", 0.0, 1.0,
                float(profile_settings.get("minimum_confidence", 0.55)), 0.05,
                key=f"correlation_suggestion_confidence_{workspace.id}_{selected_profile_id}",
            )
            weight_cols = st.columns(4)
            base_weight = weight_cols[0].number_input(
                "Базовый вес", min_value=0.0, max_value=10.0,
                value=float(profile_settings.get("base_weight", 0.25)), step=0.05,
                key=f"correlation_weight_base_{workspace.id}_{selected_profile_id}",
            )
            type_weight = weight_cols[1].number_input(
                "Вес типа", min_value=0.0, max_value=10.0,
                value=float(profile_settings.get("type_weight", 0.40)), step=0.05,
                key=f"correlation_weight_type_{workspace.id}_{selected_profile_id}",
            )
            label_weight = weight_cols[2].number_input(
                "Вес подписи", min_value=0.0, max_value=10.0,
                value=float(profile_settings.get("label_weight", 0.25)), step=0.05,
                key=f"correlation_weight_label_{workspace.id}_{selected_profile_id}",
            )
            depth_weight = weight_cols[3].number_input(
                "Вес глубины", min_value=0.0, max_value=10.0,
                value=float(profile_settings.get("depth_weight", 0.10)), step=0.05,
                key=f"correlation_weight_depth_{workspace.id}_{selected_profile_id}",
            )
            settings = CorrelationSuggestionSettings(
                max_depth_delta=float(max_delta), minimum_confidence=float(min_confidence),
                base_weight=float(base_weight), type_weight=float(type_weight),
                label_weight=float(label_weight), depth_weight=float(depth_weight),
            )
            profile_cols = st.columns([3, 1, 1])
            profile_name = profile_cols[0].text_input(
                "Название нового профиля", key=f"correlation_profile_name_{workspace.id}"
            )
            if profile_cols[1].button("Сохранить", key=f"correlation_save_profile_{workspace.id}"):
                try:
                    application.save_suggestion_profile(name=profile_name, settings=settings)
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.success("Профиль калибровки сохранён.")
                    st.rerun()
            if profile_cols[2].button(
                "Удалить", disabled=not selected_profile_id,
                key=f"correlation_delete_profile_{workspace.id}",
            ):
                application.delete_suggestion_profile(selected_profile_id)
                st.rerun()

            if st.checkbox("Сравнить с базовым сценарием", key=f"correlation_compare_scenarios_{workspace.id}"):
                try:
                    comparison = compare_suggestion_scenarios(
                        workspace, sources,
                        (("Базовый", CorrelationSuggestionSettings()), ("Текущий", settings)),
                    )
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.dataframe([
                        {
                            "Сценарий": item.name,
                            "Кандидатов": item.suggestion_count,
                            "Высокая уверенность": item.high_confidence_count,
                            "Средняя уверенность": item.average_confidence,
                            "Средняя Δ глубины": item.average_depth_delta,
                        }
                        for item in comparison
                    ], width="stretch", hide_index=True)

            preview_key = f"correlation_suggestion_preview_{workspace.id}"
            if st.button("Построить предложения", key=f"correlation_build_suggestions_{workspace.id}", width="stretch"):
                try:
                    preview = build_correlation_suggestions(workspace, sources, settings=settings)
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    state[preview_key] = asdict(preview)

            preview_payload = state.get(preview_key)
            if isinstance(preview_payload, dict):
                try:
                    preview = suggestion_preview_from_dict(preview_payload)
                except (ValueError, KeyError, TypeError):
                    state.pop(preview_key, None)
                else:
                    rows = [
                        {
                            "ID": item.id, "Левая скважина": item.left.well_id,
                            "Левый интервал": item.left.label, "Глубина слева": item.left.depth,
                            "Правая скважина": item.right.well_id, "Правый интервал": item.right.label,
                            "Глубина справа": item.right.depth, "Уверенность": item.confidence,
                            "Причина": item.reason,
                        }
                        for item in preview.suggestions
                    ]
                    if rows:
                        st.dataframe(rows, width="stretch", hide_index=True)
                        selected_suggestions = st.multiselect(
                            "Предложения для добавления", options=[item.id for item in preview.suggestions],
                            default=[item.id for item in preview.suggestions if item.confidence >= 0.75],
                            format_func=lambda value: next(
                                f"{item.left.well_id}: {item.left.label} ↔ {item.right.well_id}: {item.right.label} ({item.confidence:.0%})"
                                for item in preview.suggestions if item.id == value
                            ), key=f"correlation_selected_suggestions_{workspace.id}",
                        )
                        confirm_suggestions = st.checkbox(
                            "Подтверждаю добавление выбранных предложений",
                            key=f"correlation_confirm_suggestions_{workspace.id}",
                        )
                        if st.button(
                            "Добавить выбранные связи",
                            disabled=not (confirm_suggestions and selected_suggestions),
                            key=f"correlation_apply_suggestions_{workspace.id}", width="stretch",
                        ):
                            try:
                                current_workspace = application.get_workspace(workspace.id)
                                current_sources = application.list_published_inputs()
                                validate_suggestion_preview(preview, current_workspace, current_sources)
                                selected_ids = set(selected_suggestions)
                                chosen = [item for item in preview.suggestions if item.id in selected_ids]
                                ties = tuple(
                                    CorrelationTie(
                                        id="", left=item.left, right=item.right,
                                        name=f"{item.left.label} ↔ {item.right.label}",
                                        note=f"Автопредложение: {item.reason}; уверенность {item.confidence:.0%}",
                                    ) for item in chosen
                                )
                                before_ids = {item.id for item in current_workspace.ties}
                                updated_workspace = commands.add_ties(ties)
                                added_ids = [item.id for item in updated_workspace.ties if item.id not in before_ids]
                                application.record_suggestion_acceptance(
                                    workspace_id=workspace.id, preview=preview,
                                    accepted_ids=selected_suggestions, added_tie_ids=added_ids,
                                )
                            except (ValueError, KeyError, OSError) as exc:
                                st.error(str(exc))
                            else:
                                state.pop(preview_key, None)
                                st.success(f"Добавлено связей: {len(ties)}.")
                                st.rerun()
                    else:
                        st.info("Подходящие новые связи не найдены.")

            accepted_rows = application.list_suggestion_acceptances(workspace_id=workspace.id)
            if accepted_rows:
                with st.expander("Журнал подтверждённых автокорреляций", expanded=False):
                    st.dataframe(list(reversed(accepted_rows[-20:])), width="stretch", hide_index=True)

        workspace = application.get_workspace(workspace.id)

        if len(workspace.wells) >= 2:
            st.markdown("#### Корреляционный планшет")
            try:
                default_payload, _ = build_correlation_payload(workspace, sources)
            except ValueError as exc:
                st.info(str(exc))
            else:
                controls = st.columns(4)
                depth_min = controls[0].number_input(
                    "Верх планшета, м", value=float(default_payload.depth_min), format="%.2f",
                    key=f"correlation_chart_min_{workspace.id}",
                )
                depth_max = controls[1].number_input(
                    "Низ планшета, м", value=float(default_payload.depth_max), format="%.2f",
                    key=f"correlation_chart_max_{workspace.id}",
                )
                opacity = controls[2].slider(
                    "Прозрачность", min_value=0.04, max_value=0.85, value=0.28, step=0.01,
                    key=f"correlation_chart_opacity_{workspace.id}",
                )
                tie_width = controls[3].slider(
                    "Толщина связей", min_value=0.5, max_value=8.0, value=2.0, step=0.5,
                    key=f"correlation_chart_width_{workspace.id}",
                )
                label_controls = st.columns(2)
                show_interval_labels = label_controls[0].checkbox(
                    "Подписи интервалов", value=True, key=f"correlation_interval_labels_{workspace.id}"
                )
                show_tie_labels = label_controls[1].checkbox(
                    "Подписи связей", value=True, key=f"correlation_tie_labels_{workspace.id}"
                )
                chart_settings = CorrelationChartSettings(
                    depth_min=float(depth_min), depth_max=float(depth_max),
                    interval_opacity=float(opacity), tie_width=float(tie_width),
                    show_interval_labels=show_interval_labels, show_tie_labels=show_tie_labels,
                )
                try:
                    chart = build_correlation_figure(workspace, sources, settings=chart_settings)
                    svg_bytes = export_correlation_svg(workspace, sources, settings=chart_settings)
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.plotly_chart(chart, width="stretch", key=f"correlation_chart_{workspace.id}")
                    st.download_button(
                        "Скачать планшет SVG", svg_bytes,
                        file_name=f"correlation_{workspace.id}.svg", mime="image/svg+xml",
                        key=f"correlation_svg_{workspace.id}", width="stretch",
                    )

        if workspace.ties:
            st.dataframe([
                {
                    "Связь": tie.name,
                    "Левая скважина": tie.left.well_id,
                    "Глубина слева": tie.left.depth,
                    "Правая скважина": tie.right.well_id,
                    "Глубина справа": tie.right.depth,
                    "Цвет": tie.color,
                    "Толщина": tie.width,
                    "Линия": tie.dash,
                    "Видима": tie.visible,
                    "Комментарий": tie.note,
                }
                for tie in workspace.ties
            ], width="stretch", hide_index=True)
            tie_ids = [tie.id for tie in workspace.ties]
            selected_tie_id = st.selectbox(
                "Выбранная корреляционная связь", options=tie_ids,
                format_func=lambda value: next(tie.name for tie in workspace.ties if tie.id == value),
                key=f"correlation_selected_tie_{workspace.id}",
            )
            selected_tie = next(item for item in workspace.ties if item.id == selected_tie_id)
            with st.form(f"correlation_edit_tie_{workspace.id}_{selected_tie.id}"):
                edit_name = st.text_input("Название", value=selected_tie.name)
                edit_note = st.text_area("Комментарий", value=selected_tie.note)
                depth_cols = st.columns(2)
                edit_left_depth = depth_cols[0].number_input(
                    "Опорная глубина слева, м", value=float(selected_tie.left.depth), format="%.3f"
                )
                edit_right_depth = depth_cols[1].number_input(
                    "Опорная глубина справа, м", value=float(selected_tie.right.depth), format="%.3f"
                )
                style_cols = st.columns(4)
                edit_color = style_cols[0].color_picker("Цвет", value=selected_tie.color)
                edit_width = style_cols[1].slider("Толщина", 0.5, 8.0, float(selected_tie.width), 0.5)
                dash_options = ["solid", "dot", "dash", "longdash", "dashdot", "longdashdot"]
                edit_dash = style_cols[2].selectbox(
                    "Тип линии", dash_options, index=dash_options.index(selected_tie.dash)
                )
                edit_visible = style_cols[3].checkbox("Видима", value=selected_tie.visible)
                save_tie = st.form_submit_button("Сохранить связь", width="stretch")
            if save_tie:
                try:
                    commands.update_tie(
                        selected_tie.id, left_depth=float(edit_left_depth), right_depth=float(edit_right_depth),
                        name=edit_name, note=edit_note, color=edit_color, width=float(edit_width),
                        dash=edit_dash, visible=bool(edit_visible),
                    )
                except (ValueError, KeyError, OSError) as exc:
                    st.error(str(exc))
                else:
                    st.success("Корреляционная связь обновлена.")
                    st.rerun()

            selected_for_delete = st.multiselect(
                "Связи для удаления", options=tie_ids,
                format_func=lambda value: next(tie.name for tie in workspace.ties if tie.id == value),
                key=f"correlation_delete_ties_{workspace.id}",
            )
            confirm_delete = st.checkbox(
                "Подтверждаю групповое удаление связей", key=f"correlation_confirm_delete_{workspace.id}"
            )
            if st.button(
                "Удалить выбранные связи", disabled=not (confirm_delete and selected_for_delete),
                key=f"correlation_delete_{workspace.id}", width="stretch",
            ):
                try:
                    commands.delete_ties(tuple(selected_for_delete))
                except (ValueError, KeyError, OSError) as exc:
                    st.error(str(exc))
                else:
                    st.success("Выбранные связи удалены.")
                    st.rerun()
        else:
            st.info("В проекте ещё нет корреляционных связей.")

        quality = analyze_correlation_quality(workspace, sources)
        with st.expander("Контроль качества корреляции", expanded=False):
            metric_cols = st.columns(5)
            metric_cols[0].metric("Оценка", f"{quality.score}/100")
            metric_cols[1].metric("Связи", quality.total_ties)
            metric_cols[2].metric("Скважины", f"{quality.connected_wells}/{quality.total_wells}")
            metric_cols[3].metric("Ошибки", quality.error_count)
            metric_cols[4].metric("Предупреждения", quality.warning_count)
            status_labels = {"good": "Хорошее", "attention": "Требует внимания", "critical": "Критическое"}
            st.caption(
                f"Состояние: {status_labels.get(quality.status, quality.status)} · "
                f"дубли: {quality.duplicate_groups} · пересечения: {quality.crossing_pairs} · "
                f"недоступные опоры: {quality.unavailable_endpoints}"
            )
            issue_rows = build_correlation_quality_issue_rows(quality)
            if issue_rows:
                severity_filter = st.multiselect(
                    "Уровень проблем", options=["error", "warning", "info"],
                    default=["error", "warning", "info"],
                    key=f"correlation_quality_severity_{workspace.id}",
                )
                filtered_rows = [row for row in issue_rows if row["severity"] in severity_filter]
                if filtered_rows:
                    st.dataframe(filtered_rows, width="stretch", hide_index=True)
                else:
                    st.caption("Для выбранных уровней проблем нет.")
            else:
                st.success("Проблемы качества корреляции не обнаружены.")
            quality_export_cols = st.columns(2)
            quality_export_cols[0].download_button(
                "Скачать отчёт JSON", export_correlation_quality_json(workspace, quality),
                file_name=f"correlation_quality_{workspace.id}.json", mime="application/json",
                key=f"correlation_quality_json_{workspace.id}", width="stretch",
            )
            quality_export_cols[1].download_button(
                "Скачать отчёт CSV", export_correlation_quality_csv(workspace, quality),
                file_name=f"correlation_quality_{workspace.id}.csv", mime="text/csv",
                key=f"correlation_quality_csv_{workspace.id}", width="stretch",
            )

        operations = commands.journal.list()
        with st.expander("Журнал изменений корреляции", expanded=False):
            if operations:
                st.dataframe([
                    {
                        "Дата": item.get("timestamp", ""),
                        "Операция": item.get("action", ""),
                        "Связей до": item.get("tie_count_before", 0),
                        "Связей после": item.get("tie_count_after", 0),
                        "Добавлено": len(item.get("added_tie_ids", [])),
                        "Удалено": len(item.get("removed_tie_ids", [])),
                    }
                    for item in reversed(operations)
                ], width="stretch", hide_index=True)
            else:
                st.caption("Журнал изменений пока пуст.")

        export_left, export_right = st.columns(2)
        export_left.download_button(
            "Скачать JSON", export_correlation_json(workspace),
            file_name=f"correlation_{workspace.id}.json", mime="application/json", width="stretch",
        )
        export_right.download_button(
            "Скачать CSV", export_correlation_csv(workspace),
            file_name=f"correlation_{workspace.id}.csv", mime="text/csv", width="stretch",
        )
