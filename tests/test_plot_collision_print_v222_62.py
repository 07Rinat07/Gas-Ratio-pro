from reports.presentation_model import _track_chunks
from reports.well_log_plot import WellLogPlotConfig


def test_print_tracks_are_split_into_readable_groups():
    chunks = _track_chunks(("c1", "c2", "c3", "wh", "bh", "ch", "c1_c2", "c1_c3", "inverse_oil_indicator"), 5)
    assert chunks == (("c1", "c2", "c3", "wh", "bh"), ("ch", "c1_c2", "c1_c3", "inverse_oil_indicator"))
    assert all(len(chunk) <= 5 for chunk in chunks)


def test_print_legend_is_hidden_by_default():
    assert WellLogPlotConfig().show_curve_legend is False
