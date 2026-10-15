"""Unit tests for Human-in-the-Loop review checkpoint."""

from src.hitl.checkpoint import HITLReviewGate
from src.models.advisory import HITLDecision, HITLReviewStatus
from src.models.analysis import (
    AnalysisReport,
    AnomalySeverity,
    AnomalyType,
    AssetAllocationSummary,
    DetectedAnomaly,
    FinancialHealthMetrics,
)


def build_mock_report(has_critical: bool = True) -> AnalysisReport:
    sev = AnomalySeverity.CRITICAL if has_critical else AnomalySeverity.LOW
    return AnalysisReport(
        client_id="client_test",
        timestamp="2026-10-15T12:00:00Z",
        metrics=FinancialHealthMetrics(
            total_liquid_net_worth=1000000.0,
            total_cash=50000.0,
            cash_percentage=5.0,
            monthly_burn_rate=8000.0,
            emergency_fund_months=6.2,
            monthly_savings_rate_pct=25.0,
            overall_health_score=85,
        ),
        allocation=AssetAllocationSummary(
            actual_allocation_pct={"US_EQUITY": 60.0},
            target_allocation_pct={"US_EQUITY": 60.0},
            drift_pct={"US_EQUITY": 0.0},
            max_drift_asset_class="NONE",
            max_drift_value_pct=0.0,
        ),
        anomalies=[
            DetectedAnomaly(
                anomaly_id="TEST-01",
                anomaly_type=AnomalyType.HIGH_VALUE_WIRE_TRANSFER if has_critical else AnomalyType.CASH_DRAG,
                severity=sev,
                title="Test Anomaly",
                description="Test description",
                recommended_action="Test action",
            )
        ],
        risk_summary="Test risk summary",
        requires_human_review=has_critical,
    )


def test_hitl_requires_review_evaluation():
    gate = HITLReviewGate()
    assert gate.evaluate_requires_review(build_mock_report(has_critical=True)) is True
    assert gate.evaluate_requires_review(build_mock_report(has_critical=False)) is False


def test_hitl_auto_approve_mode():
    gate = HITLReviewGate(auto_approve=True, reviewer_name="AutoTester")
    report = build_mock_report(has_critical=True)
    decision = gate.request_review(report, [])
    assert decision.status == HITLReviewStatus.APPROVED
    assert "AutoTester" in decision.reviewer_name


def test_hitl_custom_callback_override():
    gate = HITLReviewGate()
    report = build_mock_report(has_critical=True)

    def mock_override_callback(r, acts):
        return HITLDecision(
            status=HITLReviewStatus.MODIFIED,
            reviewer_name="Senior Advisor Jane",
            modified_actions=[],
            timestamp="2026-10-16 10:00:00",
            override_reason="Modified rebalancing timeline from 30 days to 90 days.",
        )

    decision = gate.request_review(report, [], review_callback=mock_override_callback)
    assert decision.status == HITLReviewStatus.MODIFIED
    assert decision.reviewer_name == "Senior Advisor Jane"
    assert "90 days" in decision.override_reason
