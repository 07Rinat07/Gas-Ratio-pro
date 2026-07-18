from pathlib import Path


def test_professional_export_is_explicit_and_format_aware(tmp_path):
    from core.ui_behavior_contracts import PROFESSIONAL_EXPORT_BEHAVIOR
    from reports.export_wizard import ExportWizardCapabilities, ExportWizardState, build_export_wizard_review

    capabilities = ExportWizardCapabilities()
    assert capabilities.report_formats == PROFESSIONAL_EXPORT_BEHAVIOR.report_formats
    for format_id in capabilities.report_formats:
        review = build_export_wizard_review(
            ExportWizardState(
                source_label="Well A.las",
                project_label="North Block",
                export_format=format_id,
                output_dir=tmp_path,
            )
        )
        assert review.ready is True
        assert review.file_name.endswith(f".{format_id if format_id != 'bundle' else 'zip'}")
    assert PROFESSIONAL_EXPORT_BEHAVIOR.primary_action_label
    assert PROFESSIONAL_EXPORT_BEHAVIOR.download_prefix


def test_interpretation_figures_are_reused_when_settings_do_not_change():
    source = Path("app/streamlit_app.py").read_text(encoding="utf-8")
    assert "interpretation_figure_cache" in source
    assert "interpretation_plot_cache_hit" in source
    assert "interpretation_figure_cache_miss" in source
