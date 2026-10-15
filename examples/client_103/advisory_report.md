# Advisory Review Report
Client: Marcus Vance (client_103)
Generated: 2026-10-15T19:29:57.103199+00:00
**Workflow outcome: COMPLETED | Review: APPROVED**

## Executive summary
Assessment for client_103: 5 current risk signals and 5 proposed review actions. First recorded assessment; no historical observations.

## Data quality and provenance
- Market data: simulated fixture (not live market data); as of 2026-10-15
- Narrative provider: mock

## Financial snapshot
- Portfolio assets: $310,200.00
- Available emergency cash: $3,200.00
- Emergency runway: 0.30 months
- Savings rate: 1.8%
- Illustrative health score: 31/100

| Asset class | Actual % | Target % | Drift (percentage points) |
|---|---:|---:|---:|
| US_EQUITY | 98.97 | 80.00 | +18.97 |
| INTL_EQUITY | 0.00 | 10.00 | -10.00 |
| FIXED_INCOME | 0.00 | 0.00 | +0.00 |
| REAL_ESTATE | 0.00 | 0.00 | +0.00 |
| COMMODITIES | 0.00 | 0.00 | +0.00 |
| CRYPTO | 0.00 | 0.00 | +0.00 |
| CASH | 1.03 | 10.00 | -8.97 |

## Current risk signals
### MEDIUM: Portfolio drift in US_EQUITY
Evidence ID: `ANOM-DRIFT`
Allocation differs from target by +19.0 percentage points.
Evidence: asset_class=US_EQUITY; actual_pct=98.97; target_pct=80.00; drift_pct=18.97; rebalance_amount=58,840.00

### HIGH: Single-stock concentration: TSLA
Evidence ID: `ANOM-CONC-TSLA`
TSLA represents 52.4% of portfolio value.
Evidence: ticker=TSLA; market_value=162,500.00; portfolio_pct=52.39; prudence_threshold_pct=15.00; concentration_excess=115,970.00

### MEDIUM: Single-stock concentration: PLTR
Evidence ID: `ANOM-CONC-PLTR`
PLTR represents 23.4% of portfolio value.
Evidence: ticker=PLTR; market_value=72,500.00; portfolio_pct=23.37; prudence_threshold_pct=15.00; concentration_excess=25,970.00

### CRITICAL: Emergency reserve shortfall
Evidence ID: `ANOM-LIQUIDITY-DEFICIT`
Available cash covers 0.3 months of reported expenses.
Evidence: current_cash_reserves=3,200.00; monthly_expenses=10,800.00; months_runway=0.30; target_min_months=3.00; reserve_shortfall=29,200.00

### MEDIUM: Cashflow pressure
Evidence ID: `ANOM-HIGH-BURN`
Reported income leaves little or no monthly surplus.
Evidence: monthly_income=11,000.00; monthly_expenses=10,800.00; monthly_surplus=200.00


## Reviewed proposals
Amounts can overlap across proposals and must not be added together as an execution plan.
### [IMMEDIATE] Fund the emergency reserve shortfall
- Action ID: `ACT-ANOM-LIQUIDITY-DEFICIT`
- Estimated amount: $29,200.00
- Sources: ANOM-LIQUIDITY-DEFICIT
- Rationale: Available cash covers 0.3 months of reported expenses.
- Expected purpose: Addresses the documented risk signal; outcome depends on advisor review.
- Build available emergency cash to the configured reserve target.
- Confirm feasibility and document the advisor's decision before implementation.
### [HIGH] Review single-stock diversification
- Action ID: `ACT-ANOM-CONC-TSLA`
- Estimated amount: $115,970.00
- Sources: ANOM-CONC-TSLA
- Rationale: TSLA represents 52.4% of portfolio value.
- Expected purpose: Addresses the documented risk signal; outcome depends on advisor review.
- Review diversification subject to taxes, restrictions and client objectives.
- Confirm feasibility and document the advisor's decision before implementation.
### [MEDIUM] Coordinate portfolio rebalancing
- Action ID: `ACT-ANOM-DRIFT`
- Estimated amount: $58,840.00
- Sources: ANOM-DRIFT
- Rationale: Allocation differs from target by +19.0 percentage points.
- Expected purpose: Addresses the documented risk signal; outcome depends on advisor review.
- Review a coordinated rebalance against the agreed allocation, liquidity needs and taxes.
- Confirm feasibility and document the advisor's decision before implementation.
### [MEDIUM] Review single-stock diversification
- Action ID: `ACT-ANOM-CONC-PLTR`
- Estimated amount: $25,970.00
- Sources: ANOM-CONC-PLTR
- Rationale: PLTR represents 23.4% of portfolio value.
- Expected purpose: Addresses the documented risk signal; outcome depends on advisor review.
- Review diversification subject to taxes, restrictions and client objectives.
- Confirm feasibility and document the advisor's decision before implementation.
### [MEDIUM] Review monthly income and spending
- Action ID: `ACT-ANOM-HIGH-BURN`
- Estimated amount: N/A
- Sources: ANOM-HIGH-BURN
- Rationale: Reported income leaves little or no monthly surplus.
- Expected purpose: Addresses the documented risk signal; outcome depends on advisor review.
- Review recurring expenses and identify an achievable monthly savings amount.
- Confirm feasibility and document the advisor's decision before implementation.

## Human review
- Status: APPROVED
- Reviewer: Lead Wealth Advisor (Auto-Policy)
- Timestamp: 2026-10-15T19:29:57.103945+00:00
- Reason: Explicit --auto-approve demo policy; no human review performed.

## Meeting agenda (generated before review)
- Fund the emergency reserve shortfall
- Review single-stock diversification
- Coordinate portfolio rebalancing
- Review single-stock diversification
- Review monthly income and spending

## Historical context and findings
- Allocation differs from target by +19.0 percentage points.
- TSLA represents 52.4% of portfolio value.
- PLTR represents 23.4% of portfolio value.
- Available cash covers 0.3 months of reported expenses.
- Reported income leaves little or no monthly surplus.

## Limitations
Assignment demonstration using simulated data and configurable heuristics. Proposals require advisor judgment. Overlapping cash, diversification and rebalance amounts are alternatives to coordinate, not additive orders. No trades are executed.
