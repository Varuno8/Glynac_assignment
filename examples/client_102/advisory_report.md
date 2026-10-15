# Advisory Review Report
Client: Sarah Connor (client_102)
Generated: 2026-10-15T19:29:57.092154+00:00
**Workflow outcome: COMPLETED | Review: APPROVED**

## Executive summary
Assessment for client_102: 2 current risk signals and 2 proposed review actions. First recorded assessment; no historical observations.

## Data quality and provenance
- Market data: simulated fixture (not live market data); as of 2026-10-15
- Narrative provider: mock

## Financial snapshot
- Portfolio assets: $2,098,000.00
- Available emergency cash: $28,000.00
- Emergency runway: 5.00 months
- Savings rate: 36.4%
- Illustrative health score: 55/100

| Asset class | Actual % | Target % | Drift (percentage points) |
|---|---:|---:|---:|
| US_EQUITY | 83.87 | 30.00 | +53.87 |
| INTL_EQUITY | 0.00 | 10.00 | -10.00 |
| FIXED_INCOME | 14.80 | 50.00 | -35.20 |
| REAL_ESTATE | 0.00 | 0.00 | +0.00 |
| COMMODITIES | 0.00 | 0.00 | +0.00 |
| CRYPTO | 0.00 | 0.00 | +0.00 |
| CASH | 1.33 | 10.00 | -8.67 |

## Current risk signals
### HIGH: Portfolio drift in US_EQUITY
Evidence ID: `ANOM-DRIFT`
Allocation differs from target by +53.9 percentage points.
Evidence: asset_class=US_EQUITY; actual_pct=83.87; target_pct=30.00; drift_pct=53.87; rebalance_amount=1,130,100.00

### CRITICAL: Transaction requires verification
Evidence ID: `ANOM-TX-tx_102_03`
LUXURY_JEWELRY: $18,500.00 on 2026-09-14.
Evidence: tx_id=tx_102_03; amount=18,500.00; date=2026-09-14; flagged_by_bank=True; category=LUXURY_JEWELRY


## Reviewed proposals
Amounts can overlap across proposals and must not be added together as an execution plan.
### [IMMEDIATE] Verify unusual transaction
- Action ID: `ACT-ANOM-TX-tx_102_03`
- Estimated amount: N/A
- Sources: ANOM-TX-tx_102_03
- Rationale: LUXURY_JEWELRY: $18,500.00 on 2026-09-14.
- Expected purpose: Addresses the documented risk signal; outcome depends on advisor review.
- Confirm transaction purpose and authenticity with the client.
- Confirm feasibility and document the advisor's decision before implementation.
### [HIGH] Coordinate portfolio rebalancing
- Action ID: `ACT-ANOM-DRIFT`
- Estimated amount: $1,130,100.00
- Sources: ANOM-DRIFT
- Rationale: Allocation differs from target by +53.9 percentage points.
- Expected purpose: Addresses the documented risk signal; outcome depends on advisor review.
- Review a coordinated rebalance against the agreed allocation, liquidity needs and taxes.
- Confirm feasibility and document the advisor's decision before implementation.

## Human review
- Status: APPROVED
- Reviewer: Lead Wealth Advisor (Auto-Policy)
- Timestamp: 2026-10-15T19:29:57.092682+00:00
- Reason: Explicit --auto-approve demo policy; no human review performed.

## Meeting agenda (generated before review)
- Verify unusual transaction
- Coordinate portfolio rebalancing

## Historical context and findings
- Allocation differs from target by +53.9 percentage points.
- LUXURY_JEWELRY: $18,500.00 on 2026-09-14.

## Limitations
Assignment demonstration using simulated data and configurable heuristics. Proposals require advisor judgment. Overlapping cash, diversification and rebalance amounts are alternatives to coordinate, not additive orders. No trades are executed.
