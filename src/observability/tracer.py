"""Execution tracer tracking pipeline spans and performance metrics."""

import time
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Span(BaseModel):
    span_id: str
    name: str
    agent: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    status: str = "RUNNING"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExecutionTracer:
    """Collects and aggregates timing and execution traces across agent workflows."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.spans: List[Span] = []
        self._active_spans: Dict[str, Span] = {}

    def start_span(self, name: str, agent: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        span_id = f"span_{len(self.spans) + 1}_{name}"
        span = Span(
            span_id=span_id, name=name, agent=agent, start_time=time.perf_counter(), metadata=metadata or {}
        )
        self._active_spans[span_id] = span
        self.spans.append(span)
        return span_id

    def end_span(
        self, span_id: str, status: str = "SUCCESS", metadata_update: Optional[Dict[str, Any]] = None
    ) -> None:
        if span_id in self._active_spans:
            span = self._active_spans.pop(span_id)
            span.end_time = time.perf_counter()
            span.duration_ms = round((span.end_time - span.start_time) * 1000.0, 2)
            span.status = status
            if metadata_update:
                span.metadata.update(metadata_update)

    def get_summary(self) -> Dict[str, Any]:
        total_time_ms = sum(s.duration_ms or 0.0 for s in self.spans)
        return {
            "session_id": self.session_id,
            "total_spans": len(self.spans),
            "total_execution_time_ms": round(total_time_ms, 2),
            "spans": [s.model_dump() for s in self.spans],
        }
