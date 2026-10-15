"""Data models for financial analysis, anomaly detection, and portfolio metrics."""

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from src.models.common import ClientId


class AnomalyType(str, Enum):
    UNUSUAL_TRANSACTION_SPIKE = "UNUSUAL_TRANSACTION_SPIKE"
    HIGH_VALUE_WIRE_TRANSFER = "HIGH_VALUE_WIRE_TRANSFER"
    CASH_DRAG = "CASH_DRAG"
    ASSET_ALLOCATION_DRIFT = "ASSET_ALLOCATION_DRIFT"
    CONCENTRATION_RISK = "CONCENTRATION_RISK"
    EMERGENCY_RESERVE_DEFICIT = "EMERGENCY_RESERVE_DEFICIT"
    HIGH_BURN_RATE = "HIGH_BURN_RATE"


class AnomalySeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class DetectedAnomaly(BaseModel):
    anomaly_id: str
    anomaly_type: AnomalyType
    severity: AnomalySeverity
    title: str
    description: str
    evidence: Dict[str, str | float | int | bool] = Field(default_factory=dict)
    recommended_action: str


class AssetAllocationSummary(BaseModel):
    actual_allocation_pct: Dict[str, float]
    target_allocation_pct: Dict[str, float]
    drift_pct: Dict[str, float]
    max_drift_asset_class: str
    max_drift_value_pct: float


class FinancialHealthMetrics(BaseModel):
    total_liquid_net_worth: float
    total_cash: float
    cash_percentage: float
    monthly_burn_rate: float
    emergency_fund_months: Optional[float] = None
    monthly_savings_rate_pct: Optional[float] = None
    top_concentrated_position: Optional[str] = None
    top_concentration_pct: Optional[float] = None
    overall_health_score: int = Field(ge=0, le=100, description="0 to 100 overall financial health score")


class AnalysisReport(BaseModel):
    client_id: ClientId
    timestamp: str
    metrics: FinancialHealthMetrics
    allocation: AssetAllocationSummary
    anomalies: List[DetectedAnomaly] = Field(default_factory=list)
    risk_summary: str
    requires_human_review: bool = False
    warnings: List[str] = Field(default_factory=list)
    benchmark_source: str = "unavailable"
    benchmark_as_of: Optional[str] = None
