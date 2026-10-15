"""Typed public workflow outcomes, serialized to dictionaries at the CLI boundary."""

from typing import Any, Literal

from pydantic import Field

from src.models.advisory import AdvisoryPlan
from src.models.analysis import AnalysisReport
from src.models.common import ValidatedModel


class WorkflowResult(ValidatedModel):
    status: Literal["COMPLETED", "PENDING_REVIEW", "REJECTED", "FAILED"]
    session_id: str
    client_id: str | None = None
    stage: str | None = None
    error: str | None = None
    health_score: int | None = None
    anomalies_detected: int = 0
    actions_count: int = 0
    hitl_status: str | None = None
    output_json: str | None = None
    output_markdown: str | None = None
    analysis_report: AnalysisReport | None = None
    advisory_plan: AdvisoryPlan | None = None
    trace: dict[str, Any] = Field(default_factory=dict)
