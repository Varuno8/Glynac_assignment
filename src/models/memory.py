"""Data models for short-term and long-term memory subsystems."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ShortTermMemoryItem(BaseModel):
    step_name: str
    agent_name: str
    timestamp: str
    data: Dict[str, Any] = Field(default_factory=dict)
    summary: str


class HistoricalInsight(BaseModel):
    session_id: str
    date: str
    overall_health_score: int
    anomalies_detected_count: int
    top_anomaly_types: List[str]
    actions_recommended: List[str]
    hitl_status: str
    advisor_override_notes: Optional[str] = None


class ClientLongTermMemory(BaseModel):
    client_id: str
    last_updated: str
    total_sessions_run: int = 0
    historical_sessions: List[HistoricalInsight] = Field(default_factory=list)
    persistent_notes: List[str] = Field(default_factory=list)
    recurring_anomalies: Dict[str, int] = Field(
        default_factory=dict, description="Counts of repeated anomaly triggers"
    )
