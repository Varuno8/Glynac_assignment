"""Convert current anomaly evidence into deterministic action proposals."""

from pydantic import BaseModel

from src.models.advisory import ActionPriority, AdvisoryActionItem
from src.models.analysis import AnalysisReport, AnomalyType
from src.tools.base import BaseTool


class RecommendationArgs(BaseModel):
    analysis_report: AnalysisReport


class RecommendationTool(BaseTool):
    name = "advisory_action_builder"
    description = "Builds evidence-linked actions with application-calculated amounts."
    args_schema = RecommendationArgs

    def _execute(self, analysis_report):
        report = AnalysisReport.model_validate(analysis_report)
        mapping = {
            AnomalyType.CASH_DRAG: (
                "CASH_OPTIMIZATION",
                "Review excess cash placement",
                "excess_cash_dollars",
            ),
            AnomalyType.CONCENTRATION_RISK: (
                "RISK_MITIGATION",
                "Review single-stock diversification",
                "concentration_excess",
            ),
            AnomalyType.ASSET_ALLOCATION_DRIFT: (
                "PORTFOLIO_REBALANCING",
                "Coordinate portfolio rebalancing",
                "rebalance_amount",
            ),
            AnomalyType.EMERGENCY_RESERVE_DEFICIT: (
                "LIQUIDITY_MANAGEMENT",
                "Fund the emergency reserve shortfall",
                "reserve_shortfall",
            ),
            AnomalyType.HIGH_BURN_RATE: ("CASHFLOW_REVIEW", "Review monthly income and spending", None),
            AnomalyType.HIGH_VALUE_WIRE_TRANSFER: ("SECURITY_FRAUD_ALERT", "Verify outbound wire", None),
            AnomalyType.UNUSUAL_TRANSACTION_SPIKE: ("TRANSACTION_REVIEW", "Verify unusual transaction", None),
        }
        actions = []
        for anomaly in report.anomalies:
            category, title, amount_key = mapping[anomaly.anomaly_type]
            amount = float(anomaly.evidence[amount_key]) if amount_key else None
            impact = "Addresses the documented risk signal; outcome depends on advisor review."
            if anomaly.anomaly_type == AnomalyType.CASH_DRAG:
                estimate = anomaly.evidence.get("estimated_annual_opportunity_loss_usd")
                if estimate is not None:
                    impact = f"Illustrative annual gross yield difference: ${estimate:,.2f}, using simulated rates; excludes fees and taxes."
            actions.append(
                AdvisoryActionItem(
                    action_id=f"ACT-{anomaly.anomaly_id}",
                    priority=ActionPriority.IMMEDIATE
                    if anomaly.severity == "CRITICAL"
                    else ActionPriority.HIGH
                    if anomaly.severity == "HIGH"
                    else ActionPriority.MEDIUM,
                    category=category,
                    title=title,
                    rationale=anomaly.description,
                    impact=impact,
                    estimated_dollar_amount=amount,
                    source_anomaly_ids=[anomaly.anomaly_id],
                    action_steps=[
                        anomaly.recommended_action,
                        "Confirm feasibility and document the advisor's decision before implementation.",
                    ],
                )
            )
        if report.warnings:
            actions.append(
                AdvisoryActionItem(
                    action_id="ACT-DATA-REVIEW",
                    priority=ActionPriority.HIGH,
                    category="DATA_REVIEW",
                    title="Resolve missing or inconsistent data",
                    rationale="; ".join(report.warnings),
                    impact="Improves the basis for a subsequent assessment.",
                    action_steps=["Verify source records and rerun the assessment after corrections."],
                )
            )
        if not actions:
            actions.append(
                AdvisoryActionItem(
                    action_id="ACT-MONITOR",
                    priority=ActionPriority.LOW,
                    category="PORTFOLIO_MONITORING",
                    title="Schedule periodic portfolio review",
                    rationale="No configured rules were triggered in the supplied snapshot.",
                    impact="Maintains oversight as circumstances change.",
                    action_steps=["Confirm current goals and schedule the next review."],
                )
            )
        order = {
            ActionPriority.IMMEDIATE: 0,
            ActionPriority.HIGH: 1,
            ActionPriority.MEDIUM: 2,
            ActionPriority.LOW: 3,
        }
        return [a.model_dump(mode="json") for a in sorted(actions, key=lambda a: order[a.priority])]
