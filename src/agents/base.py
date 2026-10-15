"""Base agent class with dependency injection and error management."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from pydantic import BaseModel

from src.memory.short_term import SessionBlackboard
from src.observability.logger import AgentLogger
from src.tools.base import ToolRegistry


class AgentResponse(BaseModel):
    agent_name: str
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0


class BaseAgent(ABC):
    """Abstract base agent providing common capabilities across specialized agents."""

    name: str = "base_agent"
    role: str = "Generic Agent"
    description: str = "Base agent"

    def __init__(self, tools: ToolRegistry, logger: AgentLogger, blackboard: SessionBlackboard):
        self.tools = tools
        self.logger = logger
        self.blackboard = blackboard

    @abstractmethod
    def run(self, **kwargs) -> AgentResponse:
        """Core execution logic to be implemented by specialized agents."""
        pass

    def log(self, message: str, level: str = "INFO", **kwargs) -> None:
        self.logger.log_event(level, self.name, message, kwargs)
