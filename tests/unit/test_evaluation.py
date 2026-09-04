from retrieval.evaluation import EvaluationMetrics, render_report


def test_report_contains_measured_dense_hybrid_and_exact_reference():
    dense = EvaluationMetrics(total=10, correct=6, reciprocal_rank_sum=5.0, exact_total=4, exact_correct=2)
    hybrid = EvaluationMetrics(total=10, correct=8, reciprocal_rank_sum=7.0, exact_total=4, exact_correct=4)

    report = render_report(dense, hybrid)

    assert "Dense" in report
    assert "Hybride" in report
    assert "reference_exacte" in report
    assert "20.0" in report
