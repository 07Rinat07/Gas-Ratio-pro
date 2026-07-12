import pandas as pd

from core.hydrocarbon_intervals import HydrocarbonInterval
from core.reservoir_passport import build_reservoir_passport
from reports.hydrocarbon_report import build_reservoir_passport_tables


def _frame():
    return pd.DataFrame({
        "depth": [1000.0, 1000.5, 1001.0],
        "c1": [10.0, 12.0, 11.0], "c2": [2.0, 2.2, 2.1], "c3": [1.0, 1.1, 1.2],
        "ic4": [0.4, 0.5, 0.45], "nc4": [0.5, 0.6, 0.55],
        "ic5": [0.2, 0.25, 0.22], "nc5": [0.1, 0.12, 0.11],
        "wh": [1.2, 1.3, 1.25], "bh": [0.5, 0.6, 0.55], "ch": [1.1, 1.2, 1.15],
        "c1_c2": [5.0, 5.45, 5.24], "c1_c3": [10.0, 10.9, 9.17],
        "c1_c4": [11.1, 10.9, 11.0], "c1_c5": [33.3, 32.4, 33.3],
        "c2_sumc": [0.5, 0.5, 0.5], "c3_sumc": [0.3, 0.3, 0.3], "nc4_sumc": [0.2, 0.2, 0.2],
    })


def _interval():
    return HydrocarbonInterval(
        top=1000.0, base=1001.0, sample_count=3, fluid_type="oil", confidence="high",
        interpretation="Вероятный нефтяной интервал", confidence_score=84,
        data_confidence_score=90, geological_confidence_score=75, decision_level="medium",
        average_ch=1.15,
    )


def test_passport_contains_interval_statistics_and_methods():
    passport = build_reservoir_passport(_frame(), _interval(), interval_id="HC-001")
    assert passport.interval_id == "HC-001"
    assert passport.thickness == 1.0
    assert dict(passport.gas_composition)["c1"] == 11.0
    assert {item.method for item in passport.methods} == {"Pixler", "Ternary", "Haworth"}
    assert passport.data_completeness_percent == 100.0
    assert passport.readiness_label


def test_passport_tables_are_ready_for_pdf_docx_model():
    summary, methods = build_reservoir_passport_tables(_frame(), (_interval(),))
    assert summary is not None and "Reservoir Passport 2.0" in summary.title
    assert methods is not None and methods.rows
