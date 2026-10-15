"""Data models for structured advisory recommendations and Human-in-the-Loop checkpoints."""

from enum import Enum
from typing import List, Optional

from pydantic import Field

from src.models.analysis import AnalysisReport
from src.models.common import ClientId, ValidatedModel


class ActionPriority(str, Enum):
    IMMEDIATE = "IMMEDIATE"  # Within 24-48 hours
    HIGH = "HIGH"  # Next 1-2 weeks
    MEDIUM = "MEDIUM"  # Next monthly / quarterly review
    LOW = "LOW"  # Informational / monitoring


class AdvisoryActionItem(ValidatedModel):
    action_id: str
    priority: ActionPriority
    category: str  # e.g., "RISK_MITIGATION", "TAX_HARVESTING", "REBALANCING", "CASH_OPTIMIZATION"
    title: str
    rationale: str
    impact: str
    estimated_dollar_amount: Optional[float] = Field(default=None, ge=0)
    action_steps: List[str]
    source_anomaly_ids: List[str] = Field(default_factory=list)


class HITLReviewStatus(str, Enum):
    NOT_REQUIRED = "NOT_REQUIRED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    MODIFIED = "MODIFIED"
    REJECTED = "REJECTED"


class HITLDecision(ValidatedModel):
    status: HITLReviewStatus
    reviewer_name: Optional[str] = None
    timestamp: Optional[str] = None
    override_reason: Optional[str] = None
    modified_actions: Optional[List[AdvisoryActionItem]] = None


class AdvisoryPlan(ValidatedModel):
    client_id: ClientId
    client_name: str
    created_at: str
    executive_summary: str
    key_findings: List[str]
    action_items: List[AdvisoryActionItem]
    meeting_agenda_topics: List[str]
    hitl_decision: HITLDecision
    compliance_notes: str
    original_action_items: List[AdvisoryActionItem] = Field(default_factory=list)
    narrative_provider: str = "mock"
    fallback_reason: Optional[str] = None
    narrative_explanations: List["ActionExplanation"] = Field(default_factory=list)


class AdvisoryContext(ValidatedModel):
    client_id: ClientId
    analysis: AnalysisReport
    actions: List[AdvisoryActionItem]
    history_summary: str
    crm_degraded: bool


class ActionExplanation(ValidatedModel):
    action_id: str
    explanation: str


class AdvisoryNarrative(ValidatedModel):
    executive_summary: str
    action_explanations: List[ActionExplanation]
    meeting_agenda_topics: List[str]
