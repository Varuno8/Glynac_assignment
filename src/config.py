"""Application configuration and constants."""

from pathlib import Path

from pydantic import Field

from src.models.common import ValidatedModel

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SAMPLE_CLIENTS_DIR = DATA_DIR / "sample_clients"
CRM_DB_PATH = DATA_DIR / "crm_database.json"
STORAGE_DIR = BASE_DIR / "storage"
OUTPUT_DIR = BASE_DIR / "output"


# Analysis Thresholds
class AnalysisThresholds(ValidatedModel):
    # Anomaly detection: z-score cutoff for transaction spending spikes
    zscore_spike_threshold: float = Field(
        default=2.5, gt=0, description="Z-score threshold for spending anomaly"
    )
    # Concentration risk: single position max % of total liquid net worth
    max_single_position_pct: float = Field(
        default=15.0, gt=0, le=100, description="Max acceptable allocation to a single ticker"
    )
    # Cash drag: cash allocation > target by this percentage point difference
    cash_drag_excess_pct: float = Field(
        default=15.0, ge=0, le=100, description="Excess cash over target allocation triggering alert"
    )
    # Asset drift: deviation from target equity allocation
    equity_drift_tolerance_pct: float = Field(
        default=10.0, ge=0, le=100, description="Max allowed equity drift vs target"
    )
    # Minimum emergency fund in months of living expenses
    min_emergency_fund_months: float = Field(
        default=3.0, gt=0, description="Minimum recommended months of emergency cash"
    )
    # High-risk anomaly threshold requiring Human-in-the-Loop review
    hitl_rebalance_amount_threshold: float = Field(
        default=50000.0, ge=0, description="Turnover threshold requiring human approval"
    )


DEFAULT_THRESHOLDS = AnalysisThresholds()
