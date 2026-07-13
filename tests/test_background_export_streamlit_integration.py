from pathlib import Path


APP = Path("app/streamlit_app.py").read_text(encoding="utf-8")


def _professional_export_body() -> str:
    start = APP.index("def _render_professional_export_panel(")
    end = APP.index("def _render_interpretation_graphs_tab(", start)
    return APP[start:end]


def test_professional_export_panel_uses_background_manager() -> None:
    body = _professional_export_body()
    assert "BackgroundExportManager(" in body
    assert "background_manager.submit(" in body
    assert "background_manager.cancel(" in body
    assert "background_manager.pop_result(" in body
    assert "background_manager.dismiss(" in body


def test_background_worker_has_progress_and_cancellation_checkpoints() -> None:
    body = _professional_export_body()
    assert "on_progress=report" in body
    assert "check_cancelled=check_cancelled" in body
    assert "def _background_work(report, check_cancelled):" in body


def test_worker_does_not_call_streamlit_rendering_api() -> None:
    body = _professional_export_body()
    worker_start = body.index("def _background_work(report, check_cancelled):")
    worker_end = body.index("project_jobs = background_manager.list", worker_start)
    worker = body[worker_start:worker_end]
    assert "st.progress(" not in worker
    assert "st.empty(" not in worker
    assert "st.download_button(" not in worker


def test_terminal_background_job_can_be_retried_with_current_wizard_state() -> None:
    body = _professional_export_body()
    assert '"Повторить экспорт"' in body
    assert "status_view.retryable" in body
    assert "export_state[repeat_autorun_key] = True" in body
    assert 'artifact_available=background_manager.result_available(relevant_job.id)' in body
