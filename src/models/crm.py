"""CRM and client profile data models."""

from enum import Enum
from typing import List, Optional

from pydantic import Field, model_validator

from src.models.common import ClientId, ValidatedModel


class RiskTolerance(str, Enum):
    CONSERVATIVE = "CONSERVATIVE"
    MODERATE_CONSERVATIVE = "MODERATE_CONSERVATIVE"
    MODERATE = "MODERATE"
    MODERATE_AGGRESSIVE = "MODERATE_AGGRESSIVE"
    AGGRESSIVE = "AGGRESSIVE"


class TargetAllocation(ValidatedModel):
    US_EQUITY: float = Field(ge=0, le=100)
    INTL_EQUITY: float = Field(ge=0, le=100)
    FIXED_INCOME: float = Field(ge=0, le=100)
    CASH: float = Field(ge=0, le=100)
    REAL_ESTATE: Optional[float] = Field(default=0.0, ge=0, le=100)
    CRYPTO: Optional[float] = Field(default=0.0, ge=0, le=100)
    COMMODITIES: float = Field(default=0.0, ge=0, le=100)

    @model_validator(mode="after")
    def allocation_total(self):
        if (
            any(v is None for v in self.model_dump().values())
            or abs(sum(self.model_dump().values()) - 100) > 0.01
        ):
            raise ValueError("Target allocation must total 100%")
        return self


class RiskProfile(ValidatedModel):
    risk_tolerance: RiskTolerance
    risk_score: int = Field(ge=0, le=100)
    target_allocation: TargetAllocation
    max_drawdown_tolerance_pct: float = Field(ge=0, le=100)


class InvestmentGoal(ValidatedModel):
    goal: str
    target_amount: float = Field(gt=0)
    time_horizon_years: int = Field(gt=0)


class KYCStatus(str, Enum):
    VERIFIED = "VERIFIED"
    VERIFIED_NEEDS_REFRESH = "VERIFIED_NEEDS_REFRESH"
    PENDING_DOCUMENTS = "PENDING_DOCUMENTS"
    EXPIRED = "EXPIRED"


class CRMClientProfile(ValidatedModel):
    client_id: ClientId
    name: str
    email: str
    phone: str
    kyc_status: KYCStatus
    risk_profile: RiskProfile
    investment_goals: List[InvestmentGoal] = Field(default_factory=list)
    assigned_advisor: str
    last_review_date: Optional[str] = None
    advisor_notes: str = ""
    communication_preference: str = "EMAIL"
