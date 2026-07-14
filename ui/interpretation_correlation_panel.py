from __future__ import annotations

"""Streamlit UI for project-level multi-well interpretation correlation."""

from pathlib import Path
from typing import Any, MutableMapping

from projects.interpretation_correlation import (
    CorrelationEndpoint,
    CorrelationWorkspaceRepository,
    CorrelationWorkspaceService,
    discover_published_interpretations,
    export_correlation_csv,
    export_correlation_json,
)
from projects.interpretation_correlation_chart import (
    CorrelationChartSettings,
    build_correlation_figure,
    build_correlation_payload,
    export_correlation_svg,
)
from projects.repository import DEFAULT_PROJECTS_ROOT


def _source_key(item: Any) -> str:
    return f"{item.well_id}|{item.interpretation_id}|{item.revision_id}"


def render_interpretation_correlation_panel(
    st: Any,
    *,
    state: MutableMapping[str, Any],
    project_id: str,
    root: Path | str = DEFAULT_PROJECTS_ROOT,
) -> None:
    sources = discover_published_interpretations(root=root, project_id=project_id)
    repository = CorrelationWorkspaceRepository(root=root, project_id=project_id)
    workspaces = repository.list()

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
                created = repository.create(name=name, description=description)
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
        workspace = repository.get(workspace_id)
        service = CorrelationWorkspaceService(root=root, project_id=project_id, workspace_id=workspace.id)

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
                    service.add_tie(
                        left=CorrelationEndpoint(left_source.well_id, left_source.interpretation_id, left_source.revision_id,
                                                 left_interval.id, float(left_depth), left_interval.label),
                        right=CorrelationEndpoint(right_source.well_id, right_source.interpretation_id, right_source.revision_id,
                                                  right_interval.id, float(right_depth), right_interval.label),
                        name=tie_name, note=tie_note, expected_state_token=workspace.state_token,
                    )
                except (ValueError, KeyError, OSError) as exc:
                    st.error(str(exc))
                else:
                    st.success("Корреляционная связь добавлена.")
                    st.rerun()

        workspace = repository.get(workspace.id)

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
                    "Левый интервал": tie.left.label,
                    "Правая скважина": tie.right.well_id,
                    "Глубина справа": tie.right.depth,
                    "Правый интервал": tie.right.label,
                    "Комментарий": tie.note,
                }
                for tie in workspace.ties
            ], width="stretch", hide_index=True)
            tie_ids = [tie.id for tie in workspace.ties]
            selected_tie = st.selectbox(
                "Связь для удаления", options=tie_ids,
                format_func=lambda value: next(tie.name for tie in workspace.ties if tie.id == value),
                key=f"correlation_delete_tie_{workspace.id}",
            )
            confirm_delete = st.checkbox("Подтверждаю удаление связи", key=f"correlation_confirm_delete_{workspace.id}")
            if st.button("Удалить выбранную связь", disabled=not confirm_delete, key=f"correlation_delete_{workspace.id}"):
                try:
                    service.delete_tie(selected_tie, expected_state_token=workspace.state_token)
                except (ValueError, KeyError, OSError) as exc:
                    st.error(str(exc))
                else:
                    st.success("Корреляционная связь удалена.")
                    st.rerun()
        else:
            st.info("В проекте ещё нет корреляционных связей.")

        export_left, export_right = st.columns(2)
        export_left.download_button(
            "Скачать JSON", export_correlation_json(workspace),
            file_name=f"correlation_{workspace.id}.json", mime="application/json", width="stretch",
        )
        export_right.download_button(
            "Скачать CSV", export_correlation_csv(workspace),
            file_name=f"correlation_{workspace.id}.csv", mime="text/csv", width="stretch",
        )
