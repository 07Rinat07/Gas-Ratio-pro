from reports.document_model import DocumentMetadata, EngineeringDocument
from reports.report_i18n import tr


def test_renderer_labels_exist_for_all_report_locales():
    keys = (
        "report.toc", "report.plot", "report.depth_range", "report.active_depth_range",
        "report.zone_note", "report.legend.sign", "report.legend.label",
        "report.legend.meaning", "report.curve_statistics", "report.curve",
        "report.minimum", "report.maximum", "report.mean", "report.sum",
        "report.interval_id", "report.depth_m", "report.thickness_m",
        "report.fluid", "report.confidence",
    )
    for locale in ("ru", "kk", "en"):
        for key in keys:
            value = tr(locale, key, top="1000", base="1100")
            assert value and value != key


def test_document_metadata_carries_report_locale():
    document = EngineeringDocument(
        metadata=DocumentMetadata(title="Report", locale="kk"),
        sections=(),
    )
    assert document.metadata.locale == "kk"
