from core.expert_interpretation import MethodResult, build_cross_method_analysis


def test_cross_method_majority_and_contributions():
    analysis = build_cross_method_analysis(
        (
            MethodResult("Pixler", "oil", 90, 90),
            MethodResult("Haworth", "oil", 80, 80),
            MethodResult("Ternary", "gas", 60, 60),
        ),
        data_completeness_percent=85,
        interval_confidence_percent=84,
    )
    assert analysis.final_classification == "oil"
    assert analysis.agreement_percent > 60
    assert analysis.majority_methods == ("Pixler", "Haworth")
    assert analysis.dissenting_methods == ("Ternary",)
    assert round(sum(item.contribution_percent for item in analysis.contributions), 1) == 100.0
    assert "Ternary" in analysis.expert_conclusion


def test_cross_method_qc_for_low_completeness():
    analysis = build_cross_method_analysis(
        (MethodResult("Pixler", "oil", 70, 70),),
        data_completeness_percent=40,
        interval_confidence_percent=55,
    )
    codes = {item.code for item in analysis.quality_issues}
    assert "LOW_COMPLETENESS" in codes
    assert "TOO_FEW_METHODS" in codes
