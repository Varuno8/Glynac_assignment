"""Deterministic, evidence-producing analysis with explicit missing-data behavior."""

import math
from typing import Any

from pydantic import Field

from src.config import DEFAULT_THRESHOLDS, AnalysisThresholds
from src.models.analysis import AnomalySeverity as Severity
from src.models.analysis import AnomalyType as Kind
from src.models.analysis import AssetAllocationSummary, DetectedAnomaly, FinancialHealthMetrics
from src.models.common import ValidatedModel
from src.models.crm import TargetAllocation
from src.models.financial import AccountType, ClientFinancialData, TransactionType
from src.tools.base import BaseTool

# Fixture classification, not a complete security master or sector-risk model.
BROAD_FUNDS = {
    "VTI",
    "VOO",
    "SPY",
    "IVV",
    "QQQ",
    "QQQM",
    "BND",
    "AGG",
    "VXUS",
    "IXUS",
    "FXAIX",
    "FXNAX",
    "VCIT",
    "VUG",
}


class AnomalyDetectionArgs(ValidatedModel):
    financial_data: dict[str, Any]
    target_allocation: dict[str, float] | None = None
    thresholds: dict[str, Any] | None = None
    market_benchmarks: dict[str, Any] = Field(default_factory=dict)


class AnomalyDetectionTool(BaseTool):
    name = "anomaly_detection_engine"
    description = "Analyzes portfolio, cashflow and transactions with traceable evidence."
    args_schema = AnomalyDetectionArgs

    def __init__(self, default_thresholds=None):
        self.thresholds = default_thresholds or DEFAULT_THRESHOLDS

    def _execute(self, financial_data, target_allocation=None, thresholds=None, market_benchmarks=None):
        fin = ClientFinancialData.model_validate(financial_data)
        cfg = AnalysisThresholds(**thresholds) if thresholds is not None else self.thresholds
        targets = TargetAllocation(**target_allocation).model_dump() if target_allocation is not None else {}
        benchmark = market_benchmarks or {}
        val = fin.valuation()
        total = val.total
        actual = {k: v / total * 100 if total else 0.0 for k, v in val.asset_values.items()}
        warnings = list(val.warnings)
        allocation_known = not val.asset_values["UNCLASSIFIED"]
        if not targets:
            warnings.append("Agreed target allocation unavailable; target-dependent advice withheld")
        if total == 0:
            warnings.append("Portfolio has zero value; allocation percentages are not meaningful")
        drift = (
            {k: actual.get(k, 0.0) - target for k, target in targets.items()}
            if total and allocation_known
            else {}
        )
        max_key = max(drift, key=lambda k: abs(drift[k])) if drift else "NONE"
        max_drift = drift.get(max_key, 0.0)
        anomalies = []

        def add(identifier, kind, severity, title, observation, evidence, action):
            anomalies.append(
                DetectedAnomaly(
                    anomaly_id=identifier,
                    anomaly_type=kind,
                    severity=severity,
                    title=title,
                    description=observation,
                    evidence=evidence,
                    recommended_action=action,
                )
            )

        if abs(max_drift) > cfg.equity_drift_tolerance_pct:
            turnover = sum(max(0, d) * total / 100 for d in drift.values())
            add(
                "ANOM-DRIFT",
                Kind.ASSET_ALLOCATION_DRIFT,
                Severity.HIGH if abs(max_drift) > 25 else Severity.MEDIUM,
                f"Portfolio drift in {max_key}",
                f"Allocation differs from target by {max_drift:+.1f} percentage points.",
                {
                    "asset_class": max_key,
                    "actual_pct": actual[max_key],
                    "target_pct": targets[max_key],
                    "drift_pct": max_drift,
                    "rebalance_amount": round(turnover, 2),
                },
                "Review a coordinated rebalance against the agreed allocation, liquidity needs and taxes.",
            )

        expenses = fin.monthly_cashflow.average_monthly_expenses
        income = fin.monthly_cashflow.average_monthly_net_income
        reserve_target = expenses * cfg.min_emergency_fund_months
        cash_pct = actual["CASH"]
        excess = max(0, val.available_cash - max(reserve_target, total * targets.get("CASH", 0) / 100))
        if (
            targets
            and allocation_known
            and excess > 0
            and cash_pct - targets["CASH"] >= cfg.cash_drag_excess_pct
        ):
            evidence = {
                "actual_cash_pct": cash_pct,
                "target_cash_pct": targets["CASH"],
                "excess_cash_dollars": round(excess, 2),
                "retained_reserve_dollars": round(val.available_cash - excess, 2),
            }
            cash_accounts = [
                a
                for a in fin.accounts
                if a.type in (AccountType.CHECKING, AccountType.SAVINGS) and a.balance > 0
            ]
            bank_cash = sum(a.balance for a in cash_accounts)
            rate = benchmark.get("high_yield_savings_avg_apy")
            if (
                bank_cash
                and abs(bank_cash - val.available_cash) < 0.01
                and all(a.interest_rate_apy is not None for a in cash_accounts)
                and isinstance(rate, (int, float))
                and math.isfinite(rate)
                and 0 <= rate <= 100
            ):
                current_apy = sum(a.balance * a.interest_rate_apy for a in cash_accounts) / bank_cash
                evidence["estimated_annual_opportunity_loss_usd"] = round(
                    excess * max(0, rate / 100 - current_apy), 2
                )
            add(
                "ANOM-CASH-DRAG",
                Kind.CASH_DRAG,
                Severity.MEDIUM,
                "Excess cash above allocation and reserve needs",
                f"Cash allocation is {cash_pct:.1f}%; estimated available excess is ${excess:,.2f}.",
                evidence,
                "Review excess cash placement while retaining the calculated operating reserve.",
            )

        eligible = {t: v for t, v in val.equity_positions.items() if t not in BROAD_FUNDS}
        top = max(eligible, key=eligible.get) if eligible else None
        for ticker, amount in eligible.items():
            pct = amount / total * 100 if total else 0
            if pct > cfg.max_single_position_pct:
                add(
                    f"ANOM-CONC-{ticker}",
                    Kind.CONCENTRATION_RISK,
                    Severity.HIGH if pct > 30 else Severity.MEDIUM,
                    f"Single-stock concentration: {ticker}",
                    f"{ticker} represents {pct:.1f}% of portfolio value.",
                    {
                        "ticker": ticker,
                        "market_value": amount,
                        "portfolio_pct": pct,
                        "prudence_threshold_pct": cfg.max_single_position_pct,
                        "concentration_excess": round(
                            max(0, amount - total * cfg.max_single_position_pct / 100), 2
                        ),
                    },
                    "Review diversification subject to taxes, restrictions and client objectives.",
                )

        runway = val.available_cash / expenses if expenses else None
        savings = (income - expenses) / income * 100 if income else None
        if runway is not None and runway < cfg.min_emergency_fund_months:
            add(
                "ANOM-LIQUIDITY-DEFICIT",
                Kind.EMERGENCY_RESERVE_DEFICIT,
                Severity.CRITICAL if runway < 1 else Severity.HIGH,
                "Emergency reserve shortfall",
                f"Available cash covers {runway:.1f} months of reported expenses.",
                {
                    "current_cash_reserves": val.available_cash,
                    "monthly_expenses": expenses,
                    "months_runway": runway,
                    "target_min_months": cfg.min_emergency_fund_months,
                    "reserve_shortfall": round(max(0, reserve_target - val.available_cash), 2),
                },
                "Build available emergency cash to the configured reserve target.",
            )
        if (savings is not None and savings < 5) or (income == 0 and expenses > 0):
            add(
                "ANOM-HIGH-BURN",
                Kind.HIGH_BURN_RATE,
                Severity.MEDIUM,
                "Cashflow pressure",
                "Reported income leaves little or no monthly surplus.",
                {
                    "monthly_income": income,
                    "monthly_expenses": expenses,
                    "monthly_surplus": income - expenses,
                },
                "Review recurring expenses and identify an achievable monthly savings amount.",
            )

        debits = [tx for tx in fin.recent_transactions if tx.type == TransactionType.DEBIT]
        mean = sum(tx.amount for tx in debits) / len(debits) if debits else 0
        std = math.sqrt(sum((tx.amount - mean) ** 2 for tx in debits) / len(debits)) if debits else 0
        for tx in fin.recent_transactions:
            is_debit = tx.type == TransactionType.DEBIT
            z = (tx.amount - mean) / std if is_debit and len(debits) >= 3 and std else 0
            wire = is_debit and tx.category.upper() == "WIRE_TRANSFER"
            large = is_debit and expenses > 0 and tx.amount >= expenses * 2
            if tx.flagged_by_bank or wire or large:
                add(
                    f"ANOM-TX-{tx.tx_id}",
                    Kind.HIGH_VALUE_WIRE_TRANSFER if wire else Kind.UNUSUAL_TRANSACTION_SPIKE,
                    Severity.CRITICAL if tx.flagged_by_bank else Severity.HIGH,
                    "Transaction requires verification",
                    f"{tx.category}: ${tx.amount:,.2f} on {tx.date}.",
                    {
                        "tx_id": tx.tx_id,
                        "amount": tx.amount,
                        "date": tx.date,
                        "flagged_by_bank": tx.flagged_by_bank,
                        "category": tx.category,
                    },
                    "Confirm transaction purpose and authenticity with the client.",
                )
            elif len(debits) >= 3 and std > 0 and z > cfg.zscore_spike_threshold and tx.amount > 2000:
                add(
                    f"ANOM-TX-{tx.tx_id}",
                    Kind.UNUSUAL_TRANSACTION_SPIKE,
                    Severity.MEDIUM,
                    "Unusual spending amount",
                    f"Transaction is {z:.2f} standard deviations above this sample's mean.",
                    {"tx_id": tx.tx_id, "amount": tx.amount, "z_score": z, "sample_count": len(debits)},
                    "Review whether this is an expected one-off expense.",
                )

        score = max(
            0,
            100
            - sum(
                {Severity.CRITICAL: 30, Severity.HIGH: 15, Severity.MEDIUM: 8, Severity.LOW: 3}[a.severity]
                for a in anomalies
            ),
        )
        metrics = FinancialHealthMetrics(
            total_liquid_net_worth=round(total, 2),
            total_cash=round(val.available_cash, 2),
            cash_percentage=round(cash_pct, 2),
            monthly_burn_rate=expenses,
            emergency_fund_months=round(runway, 2) if runway is not None else None,
            monthly_savings_rate_pct=round(savings, 2) if savings is not None else None,
            top_concentrated_position=top,
            top_concentration_pct=round(eligible[top] / total * 100, 2) if top and total else None,
            overall_health_score=score,
        )
        return dict(
            metrics=metrics.model_dump(),
            allocation=AssetAllocationSummary(
                actual_allocation_pct=actual,
                target_allocation_pct=targets,
                drift_pct=drift,
                max_drift_asset_class=max_key,
                max_drift_value_pct=max_drift,
            ).model_dump(),
            anomalies=[a.model_dump() for a in anomalies],
            risk_summary=f"Illustrative health score {score}/100; {len(anomalies)} risk signals.",
            requires_human_review=bool(warnings)
            or any(a.severity in (Severity.HIGH, Severity.CRITICAL) for a in anomalies),
            warnings=warnings,
            benchmark_source=benchmark.get("source", "unavailable"),
            benchmark_as_of=benchmark.get("last_updated"),
        )
