from __future__ import annotations

"""Streamlit panel for manual interpretation interval management.

The panel is intentionally thin: persistence, validation, overlap checks and
Undo/Redo remain in the project-layer services.  Only JSON-compatible values
are stored in Streamlit session state.
"""

from pathlib import Path
from typing import Any, MutableMapping

from projects.interpretation_interval_manager import (
    InterpretationIntervalManager,
    InterpretationIntervalOverlapError,
)
from projects.interpretation_interval_properties import InterpretationIntervalPropertiesService
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

        with st.form(f"manual_interval_create_{project_id}_{well_id}", clear_on_submit=True):
            st.markdown("**Новый интервал**")
            create_top_col, create_base_col = st.columns(2)
            top = create_top_col.number_input("Верх, м", step=0.1, format="%.3f")
            base = create_base_col.number_input("Низ, м", step=0.1, format="%.3f")
            label = st.text_input("Подпись", value="Интервал")
            type_col, color_col = st.columns(2)
            interval_type = type_col.text_input("Тип", value="undefined")
            color = color_col.color_picker("Цвет", value="#4C78A8")
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
            type_value = st.text_input("Тип интервала", value=selected.interval_type)
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
