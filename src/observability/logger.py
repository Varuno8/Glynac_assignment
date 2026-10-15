"""Correlated structured events with allowlisted metadata; no raw client payloads."""

import json
from pathlib import Path

from rich.console import Console

from src.config import OUTPUT_DIR
from src.models.common import utc_now

console = Console()


class AgentLogger:
    def __init__(self, log_file: Path | None = None, verbose=True, context=None):
        self.verbose = verbose
        self.log_file = Path(log_file) if log_file is not None else OUTPUT_DIR / "agent_execution.jsonl"
        self.context = dict(context or {})

    def bind(self, **context):
        return AgentLogger(self.log_file, self.verbose, {**self.context, **context})

    def log_event(self, level, agent, message, metadata=None):
        allowed = {"tool", "success", "duration_ms", "fallback_reason", "outcome", "stage", "error_type"}
        safe = {k: v for k, v in (metadata or {}).items() if k in allowed}
        record = {
            "timestamp": utc_now(),
            "level": level.upper(),
            "agent": agent,
            "session_id": self.context.get("session_id"),
            "client_id": self.context.get("client_id"),
            "stage": self.context.get("stage"),
            "outcome": safe.get("outcome", "EVENT"),
            "message": message,
            "metadata": safe,
        }
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        with self.log_file.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, allow_nan=False) + "\n")
        if self.verbose:
            console.print(f"[{level.upper()}] {agent}: {message}", markup=False)

    def info(self, agent, message, **kwargs):
        self.log_event("INFO", agent, message, kwargs)

    def warning(self, agent, message, **kwargs):
        self.log_event("WARNING", agent, message, kwargs)

    def error(self, agent, message, **kwargs):
        self.log_event("ERROR", agent, message, kwargs)

    def tool_call(self, agent, tool_name, args):
        self.log_event("TOOL", agent, f"Invoking {tool_name}", {"tool": tool_name})

    def tool_result(self, agent, tool_name, success, duration_ms):
        self.log_event(
            "INFO" if success else "ERROR",
            agent,
            f"Tool {tool_name} {'succeeded' if success else 'failed'}",
            {
                "tool": tool_name,
                "success": success,
                "duration_ms": duration_ms,
                "outcome": "SUCCESS" if success else "FAILED",
            },
        )
